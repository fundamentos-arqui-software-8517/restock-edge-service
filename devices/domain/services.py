from datetime import datetime, timezone

from dateutil.parser import parse

from devices.domain.entities import DeviceHealthEvent
from devices.domain.entities import DeviceStatusReport
from devices.domain.entities import DeviceThreshold


class DeviceStatusSemanticError(ValueError):
    """
    Error raised when a device health payload is syntactically valid but
    semantically invalid for status registration.
    """


class DeviceThresholdService:
    """
    Domain service responsible for the creation of valid device threshold entities.
    """

    @classmethod
    def create_threshold_for_device(cls,
                         device_id: str,
                         assigned_batch_id: str,
                         custom_supply_unit_measurement: str | None,
                         minimum_humidity_percentage: float,
                         maximum_humidity_percentage: float,
                         minimum_temperature_in_celsius: float,
                         maximum_temperature_in_celsius: float,
                         threshold_id: int = 0,
                         custom_supply_weight: float | None = 100.0,
                         anomaly_threshold: float | None = None,
                         ) -> DeviceThreshold:
        try:
            parsed_custom_supply_unit_measurement = (
                str(custom_supply_unit_measurement)
                if custom_supply_unit_measurement is not None
                else None
            )

            parsed_custom_supply_weight = (
                float(custom_supply_weight)
                if custom_supply_weight is not None
                else None
            )

            parsed_anomaly_threshold = (
                float(anomaly_threshold)
                if anomaly_threshold is not None
                else None
            )

            parsed_assigned_batch_id = str(assigned_batch_id)
            parsed_minimum_humidity_percentage = float(minimum_humidity_percentage)
            parsed_maximum_humidity_percentage = float(maximum_humidity_percentage)
            parsed_minimum_temperature_in_celsius = float(minimum_temperature_in_celsius)
            parsed_maximum_temperature_in_celsius = float(maximum_temperature_in_celsius)
        except (ValueError, TypeError):
            raise ValueError("Invalid data format")

        return DeviceThreshold(
            threshold_id=threshold_id,
            device_id=device_id,
            assigned_batch_id=parsed_assigned_batch_id,
            custom_supply_weight=parsed_custom_supply_weight,
            custom_supply_unit_measurement=parsed_custom_supply_unit_measurement,
            minimum_humidity_percentage=parsed_minimum_humidity_percentage,
            maximum_humidity_percentage=parsed_maximum_humidity_percentage,
            minimum_temperature_in_celsius=parsed_minimum_temperature_in_celsius,
            maximum_temperature_in_celsius=parsed_maximum_temperature_in_celsius,
            anomaly_threshold=parsed_anomaly_threshold,
        )


class DeviceStatusService:
    """
    Domain service responsible for normalizing embedded health telemetry
    packages and creating status report and health event entities.

    MQTT is the real source of this contract. HTTP callers must send the same
    event-style payload to simulate or fallback the embedded message.
    """

    HEALTH_INFO = "INFO"
    HEALTH_CRITICAL = "CRITICAL"

    ALERT_TYPE_HEALTH_ANOMALY = "HEALTH_ANOMALY"
    ALERT_TYPE_BOOT_RESET_REASON = "BOOT_RESET_REASON"
    SUPPORTED_ALERT_TYPES = {
        ALERT_TYPE_HEALTH_ANOMALY,
        ALERT_TYPE_BOOT_RESET_REASON,
    }
    SUPPORTED_METRICS = {
        "heap",
        "cpu",
        "voltage",
        "temperature",
        "reset_reason",
    }
    NUMERIC_METRICS = {
        "heap",
        "cpu",
        "voltage",
        "temperature",
    }

    @classmethod
    def create_status_report(cls, payload: dict, source: str = "HTTP") -> tuple:
        """
        Normalize an embedded HealthTelemetryPackage and create domain entities.

        :param payload: Raw event-style health payload received from HTTP or MQTT.
        :param source: Input channel that produced the payload.
        :return: Tuple with DeviceStatusReport, optional DeviceHealthEvent and result metadata.
        :raise ValueError: If device_id is missing or the payload is not a dict.
        """
        normalized = cls._normalize_payload(payload, source)
        evaluation = cls._evaluate_health(normalized)

        report = DeviceStatusReport(
            device_id=normalized["device_id"],
            branch_id=normalized.get("branch_id"),
            cpu_usage_percentage=normalized.get("cpu_usage_percentage"),
            free_heap_bytes=normalized.get("free_heap_bytes"),
            internal_temperature_celsius=normalized.get("internal_temperature_celsius"),
            voltage=normalized.get("voltage"),
            uptime_ms=normalized.get("uptime_ms"),
            system_status=normalized.get("system_status"),
            alert_type=normalized.get("alert_type"),
            metric=normalized.get("metric"),
            value=normalized.get("value"),
            threshold=normalized.get("threshold"),
            message=normalized.get("message"),
            health_status=evaluation["health_status"],
            critical=evaluation["critical"],
            source=normalized["source"],
            created_at=normalized["created_at"],
        )

        event = None
        if evaluation["event_type"]:
            event = DeviceHealthEvent(
                device_id=normalized["device_id"],
                branch_id=normalized.get("branch_id"),
                event_type=evaluation["event_type"],
                health_status=evaluation["health_status"],
                metric=evaluation.get("metric"),
                value=normalized.get("value"),
                threshold=normalized.get("threshold"),
                reason=evaluation["reason"],
                message=normalized.get("message"),
                source=normalized["source"],
                created_at=normalized["created_at"],
            )

        return report, event, evaluation

    @classmethod
    def _normalize_payload(cls, payload: dict, source: str) -> dict:
        """Convert the embedded HealthTelemetryPackage into the domain shape."""
        if not isinstance(payload, dict):
            raise ValueError("Invalid payload")

        device_id = payload.get("device_id")
        if not device_id:
            raise ValueError("Missing device_id")

        metric = cls._to_optional_str(payload.get("metric"))
        alert_type = cls._to_optional_str(payload.get("alert_type"))
        if alert_type:
            alert_type = alert_type.upper()
        if metric:
            metric = metric.lower()

        if not alert_type:
            raise ValueError("Missing alert_type")
        if not metric:
            raise ValueError("Missing metric")
        if "timestamp_ms" not in payload:
            raise ValueError("Missing timestamp_ms")
        if not cls._to_optional_str(payload.get("message")):
            raise ValueError("Missing message")

        value = cls._parse_metric_value(payload, metric)
        threshold = cls._parse_metric_threshold(payload, metric)
        timestamp_ms = cls._to_optional_float(payload, "timestamp_ms")
        created_at = cls._parse_created_at(payload.get("created_at"))

        normalized = {
            "device_id": str(device_id),
            "branch_id": cls._to_optional_str(payload.get("branch_id")),
            "cpu_usage_percentage": None,
            "free_heap_bytes": None,
            "internal_temperature_celsius": None,
            "voltage": None,
            "uptime_ms": timestamp_ms,
            "system_status": None,
            "alert_type": alert_type,
            "metric": metric,
            "value": value,
            "threshold": threshold,
            "message": cls._to_optional_str(payload.get("message")),
            "source": str(source or "HTTP").upper(),
            "created_at": created_at,
        }

        if metric == "cpu" and normalized["cpu_usage_percentage"] is None:
            normalized["cpu_usage_percentage"] = value
        elif metric == "heap" and normalized["free_heap_bytes"] is None:
            normalized["free_heap_bytes"] = value
        elif metric == "voltage" and normalized["voltage"] is None:
            normalized["voltage"] = value
        elif metric == "temperature" and normalized["internal_temperature_celsius"] is None:
            normalized["internal_temperature_celsius"] = value

        cls._validate_semantics(normalized)
        return normalized

    @classmethod
    def _validate_semantics(cls, payload: dict) -> None:
        """Validate unsupported or impossible event-style payload values."""
        alert_type = payload.get("alert_type")
        if alert_type not in cls.SUPPORTED_ALERT_TYPES:
            raise DeviceStatusSemanticError(f"Unsupported alert_type: {alert_type}")

        metric = payload.get("metric")
        if metric not in cls.SUPPORTED_METRICS:
            raise DeviceStatusSemanticError(f"Unsupported metric: {metric}")

        if alert_type == cls.ALERT_TYPE_HEALTH_ANOMALY and metric == "reset_reason":
            raise DeviceStatusSemanticError("reset_reason is not valid for HEALTH_ANOMALY")

        if alert_type == cls.ALERT_TYPE_BOOT_RESET_REASON and metric != "reset_reason":
            raise DeviceStatusSemanticError("BOOT_RESET_REASON requires metric reset_reason")

        non_negative_fields = [
            "cpu_usage_percentage",
            "free_heap_bytes",
            "voltage",
            "uptime_ms",
            "value",
            "threshold",
        ]
        for field in non_negative_fields:
            value = payload.get(field)
            if value is not None and value < 0:
                raise DeviceStatusSemanticError(f"Invalid negative value for {field}")

    @classmethod
    def _evaluate_health(cls, payload: dict) -> dict:
        """Evaluate the embedded alert type into a device health status."""
        alert_type = payload.get("alert_type")
        metric = payload.get("metric")

        if alert_type == cls.ALERT_TYPE_HEALTH_ANOMALY:
            reason = payload.get("message") or "Health anomaly reported by device"
            return cls._critical_result(metric, reason)

        if alert_type == cls.ALERT_TYPE_BOOT_RESET_REASON:
            reason = payload.get("message") or "Device boot/reset reason reported"
            return {
                "health_status": cls.HEALTH_INFO,
                "critical": False,
                "metric": metric or "reset_reason",
                "reason": reason,
                "event_type": "INFO",
            }

        raise DeviceStatusSemanticError(f"Unsupported alert_type: {alert_type}")

    @classmethod
    def _critical_result(cls, metric: str | None, reason: str) -> dict:
        return {
            "health_status": cls.HEALTH_CRITICAL,
            "critical": True,
            "metric": metric,
            "reason": reason,
            "event_type": "ERROR",
        }

    @staticmethod
    def _to_optional_float(payload: dict, field_name: str) -> float | None:
        value = payload.get(field_name)
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            raise DeviceStatusSemanticError(f"Invalid numeric value for {field_name}")

    @classmethod
    def _parse_metric_value(cls, payload: dict, metric: str | None) -> float | None:
        """Parse value as numeric only for metrics that are numeric on embedded."""
        if metric in cls.NUMERIC_METRICS:
            if "value" not in payload:
                raise ValueError("Missing value")
            return cls._to_optional_float(payload, "value")
        return None

    @classmethod
    def _parse_metric_threshold(cls, payload: dict, metric: str | None) -> float | None:
        """Parse threshold as numeric only for metrics that are numeric on embedded."""
        if metric in cls.NUMERIC_METRICS:
            if "threshold" not in payload:
                raise ValueError("Missing threshold")
            return cls._to_optional_float(payload, "threshold")
        return None

    @staticmethod
    def _to_optional_str(value) -> str | None:
        if value in (None, ""):
            return None
        return str(value)

    @staticmethod
    def _parse_created_at(value):
        if not value:
            return datetime.now(timezone.utc)
        try:
            parsed = parse(str(value))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (ValueError, TypeError):
            return datetime.now(timezone.utc)
