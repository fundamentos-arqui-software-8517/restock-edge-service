from devices.domain.entities import DeviceHealthEvent
from devices.domain.entities import DeviceStatusReport
from devices.domain.entities import DeviceThreshold
from devices.infrastructure.models import DeviceHealthEventModel
from devices.infrastructure.models import DeviceStatusReportModel
from devices.infrastructure.models import DeviceThresholdModel


class DeviceThresholdRepository:
    """
    Repository for DeviceThreshold entities.
    This repository is responsible for storing DeviceThreshold entities.
    """

    @staticmethod
    def save(device_threshold: DeviceThreshold) -> DeviceThreshold:
        """
        Persists a DeviceThreshold entity to the database. Performs upsert if record exists.
        """
        existing = DeviceThresholdModel.select().where(DeviceThresholdModel.device_id == device_threshold.device_id).first()
        if existing:
            return DeviceThresholdRepository.update(device_threshold)

        anomaly_thresh = getattr(device_threshold, "anomaly_threshold", None)
        record = DeviceThresholdModel.create(
            device_id=device_threshold.device_id,
            assigned_batch_id=device_threshold.assigned_batch_id,
            custom_supply_weight=device_threshold.custom_supply_weight,
            custom_supply_unit_measurement=device_threshold.custom_supply_unit_measurement,
            minimum_humidity_percentage=device_threshold.minimum_humidity_percentage,
            maximum_humidity_percentage=device_threshold.maximum_humidity_percentage,
            minimum_temperature_in_celsius=device_threshold.minimum_temperature_in_celsius,
            maximum_temperature_in_celsius=device_threshold.maximum_temperature_in_celsius,
            anomaly_threshold=anomaly_thresh,
        )

        return DeviceThresholdRepository._to_entity(record)

    @staticmethod
    def update(device_threshold: DeviceThreshold) -> DeviceThreshold:
        """
        Updates a DeviceThreshold entity in the database.
        """
        anomaly_thresh = getattr(device_threshold, "anomaly_threshold", None)
        update_data = {
            "assigned_batch_id": device_threshold.assigned_batch_id,
            "custom_supply_weight": device_threshold.custom_supply_weight,
            "custom_supply_unit_measurement": device_threshold.custom_supply_unit_measurement,
            "minimum_humidity_percentage": device_threshold.minimum_humidity_percentage,
            "maximum_humidity_percentage": device_threshold.maximum_humidity_percentage,
            "minimum_temperature_in_celsius": device_threshold.minimum_temperature_in_celsius,
            "maximum_temperature_in_celsius": device_threshold.maximum_temperature_in_celsius,
        }
        if anomaly_thresh is not None:
            update_data["anomaly_threshold"] = anomaly_thresh

        DeviceThresholdModel.update(update_data).where(DeviceThresholdModel.device_id == device_threshold.device_id).execute()
        record = DeviceThresholdModel.get(device_id=device_threshold.device_id)

        return DeviceThresholdRepository._to_entity(record)

    @staticmethod
    def calibrate_custom_supply_weight(device_id: str, custom_supply_weight: float) -> DeviceThreshold:
        """
        Updates the custom_supply_weight of a DeviceThreshold entity in the database.
        """
        DeviceThresholdModel.update(
            custom_supply_weight=custom_supply_weight,
        ).where(DeviceThresholdModel.device_id == device_id).execute()

        record = DeviceThresholdModel.get(device_id=device_id)

        return DeviceThresholdRepository._to_entity(record)

    @staticmethod
    def get_by_device_id(device_id: str) -> DeviceThreshold:
        """
        Retrieves a DeviceThreshold entity from the database by device_id.
        """
        record = DeviceThresholdModel.get(device_id=device_id)
        return DeviceThresholdRepository._to_entity(record)

    @staticmethod
    def _to_entity(record: DeviceThresholdModel) -> DeviceThreshold:
        """Map a DeviceThresholdModel to a domain entity."""
        return DeviceThreshold(
            threshold_id=record.threshold_id,
            device_id=record.device_id,
            assigned_batch_id=record.assigned_batch_id,
            custom_supply_weight=record.custom_supply_weight,
            custom_supply_unit_measurement=record.custom_supply_unit_measurement,
            minimum_humidity_percentage=record.minimum_humidity_percentage,
            maximum_humidity_percentage=record.maximum_humidity_percentage,
            minimum_temperature_in_celsius=record.minimum_temperature_in_celsius,
            maximum_temperature_in_celsius=record.maximum_temperature_in_celsius,
            anomaly_threshold=getattr(record, "anomaly_threshold", None),
        )


class DeviceStatusReportRepository:
    """
    Repository for DeviceStatusReport entities.

    This repository is responsible for storing normalized device health status
    reports independently from IAM lifecycle status.
    """

    @staticmethod
    def save(device_status_report: DeviceStatusReport) -> DeviceStatusReport:
        """Persist a DeviceStatusReport entity to the database."""
        record = DeviceStatusReportModel.create(
            device_id=device_status_report.device_id,
            branch_id=device_status_report.branch_id,
            cpu_usage_percentage=device_status_report.cpu_usage_percentage,
            free_heap_bytes=device_status_report.free_heap_bytes,
            internal_temperature_celsius=device_status_report.internal_temperature_celsius,
            voltage=device_status_report.voltage,
            uptime_ms=device_status_report.uptime_ms,
            system_status=device_status_report.system_status,
            alert_type=device_status_report.alert_type,
            metric=device_status_report.metric,
            value=device_status_report.value,
            threshold=device_status_report.threshold,
            message=device_status_report.message,
            health_status=device_status_report.health_status,
            critical=device_status_report.critical,
            source=device_status_report.source,
            created_at=device_status_report.created_at,
        )
        return DeviceStatusReportRepository._to_entity(record)

    @staticmethod
    def _to_entity(record: DeviceStatusReportModel) -> DeviceStatusReport:
        """Map a DeviceStatusReportModel to a domain entity."""
        return DeviceStatusReport(
            id=record.id,
            device_id=record.device_id,
            branch_id=record.branch_id,
            cpu_usage_percentage=record.cpu_usage_percentage,
            free_heap_bytes=record.free_heap_bytes,
            internal_temperature_celsius=record.internal_temperature_celsius,
            voltage=record.voltage,
            uptime_ms=record.uptime_ms,
            system_status=record.system_status,
            alert_type=record.alert_type,
            metric=record.metric,
            value=record.value,
            threshold=record.threshold,
            message=record.message,
            health_status=record.health_status,
            critical=record.critical,
            source=record.source,
            created_at=record.created_at,
        )


class DeviceHealthEventRepository:
    """
    Repository for DeviceHealthEvent entities.

    This repository stores critical and informational events derived from
    device health reports.
    """

    @staticmethod
    def save(device_health_event: DeviceHealthEvent) -> DeviceHealthEvent:
        """Persist a DeviceHealthEvent entity to the database."""
        record = DeviceHealthEventModel.create(
            device_id=device_health_event.device_id,
            branch_id=device_health_event.branch_id,
            event_type=device_health_event.event_type,
            health_status=device_health_event.health_status,
            metric=device_health_event.metric,
            value=device_health_event.value,
            threshold=device_health_event.threshold,
            reason=device_health_event.reason,
            message=device_health_event.message,
            source=device_health_event.source,
            created_at=device_health_event.created_at,
        )
        return DeviceHealthEventRepository._to_entity(record)

    @staticmethod
    def _to_entity(record: DeviceHealthEventModel) -> DeviceHealthEvent:
        """Map a DeviceHealthEventModel to a domain entity."""
        return DeviceHealthEvent(
            id=record.id,
            device_id=record.device_id,
            branch_id=record.branch_id,
            event_type=record.event_type,
            health_status=record.health_status,
            metric=record.metric,
            value=record.value,
            threshold=record.threshold,
            reason=record.reason,
            message=record.message,
            source=record.source,
            created_at=record.created_at,
        )
