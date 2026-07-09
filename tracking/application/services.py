"""Application services for the Tracking bounded context.

Application services sit between the interface layer and the domain layer. They
orchestrate use-cases by coordinating domain services, domain entities and
repositories without containing domain logic themselves.
"""
import json
import logging
import os
from urllib import error, request

from dotenv import load_dotenv

from devices.domain.entities import DeviceThreshold
from devices.infrastructure.repositories import DeviceThresholdRepository
from tracking.domain.entities import WeightRecord
from tracking.domain.entities import EnvironmentRecord
from tracking.domain.services import WeightRecordService
from tracking.domain.services import EnvironmentRecordService
from tracking.infrastructure.repositories import WeightRecordRepository
from tracking.infrastructure.repositories import EnvironmentRecordRepository
from tracking.infrastructure.clients import telemetry_sync_client
from iam.infrastructure.repositories import DeviceRepository

# Load environment variables from .env file
load_dotenv()


class WeightRecordApplicationService:
    """Application service that orchestrates the creation of a weight record use-case.

    Responsibilities:

    1. Cross-context validation – delegates to the IAM
       :class:`~iam.infrastructure.repositories.DeviceRepository` to verify
       that the requesting device is registered and the supplied API key is
       valid.
    2. Domain logic – delegates to
       :class:`~tracking.domain.services.WeightRecordService` to validate raw
       sensor values and construct a
       :class:`~tracking.domain.entities.WeightRecord` entity.
    3. Persistence – delegates to
       :class:`~tracking.infrastructure.repositories.WeightRecordRepository` to
       persist the entity and return the saved aggregate with its assigned
       identity.
    """

    def __init__(self):
        """Initialize the service with its required collaborators."""
        self.weight_record_repository = WeightRecordRepository()
        self.weight_record_service = WeightRecordService()
        self.device_threshold_repository = DeviceThresholdRepository()
        self.device_repository = DeviceRepository()
        self.environment_record_repository = EnvironmentRecordRepository()

    @staticmethod
    def _send_anomaly_to_cloud(
        device_id: str,
        registered_value: float,
        timestamp_iso: str | None = None,
    ) -> None:
        """Sends a physical anomaly report to the cloud backend API.

        Scenario 1: If the physical anomaly threshold is breached, post to api/v1/anomalies.
        Scenario 3: Safely catches HTTPError, URLError, TimeoutError without crashing.
        """
        base_url = os.getenv("CLOUD_API_BASE_URL")
        anomalies_url = os.getenv("CLOUD_ANOMALIES_URL")
        token = os.getenv("CLOUD_API_TOKEN")

        if not anomalies_url and base_url:
            anomalies_url = f"{base_url.rstrip('/')}/api/v1/anomalies"

        if not anomalies_url:
            logging.info("Cloud anomaly reporting skipped: CLOUD_ANOMALIES_URL is not configured")
            return

        from datetime import datetime, timezone
        payload = {
            "deviceId": device_id,
            "registeredValue": registered_value,
            "timestamp": timestamp_iso or datetime.now(timezone.utc).isoformat()
        }
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        body = json.dumps(payload).encode("utf-8")
        cloud_request = request.Request(
            anomalies_url,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(cloud_request, timeout=5) as response:
                logging.info(
                    "Physical anomaly reported to cloud with status %s",
                    response.status,
                )
        except (error.HTTPError, error.URLError, TimeoutError) as ex:
            logging.exception("Error reporting physical anomaly to cloud: %s", ex)
        except Exception as ex:
            logging.exception("Unexpected error reporting physical anomaly: %s", ex)

    def create_weight_record(
        self,
        device_id: str,
        weight: float,
        created_at: str | None,
    ) -> tuple:
        """Execute the creation and processing of a weight record use-case.

        Args:
            device_id (str): Identifier of the device submitting the reading.
            weight (float): Weight measurement expressed in grams.
            created_at (str | None): ISO 8601 timestamp of the reading. Passed
                to the domain service; accepts ``None`` to default to the
                current UTC time.

        Returns:
            WeightRecord: Persisted domain entity populated with its assigned ``id``.

        Raises:
            ValueError: If no device matches the ``device_id``
        """
        if not self.device_repository.find_by_id(device_id):
            raise ValueError("Device not found")

        # Retrieves the custom supply weight for the device
        try:
            device_threshold = self.device_threshold_repository.get_by_device_id(device_id)
            custom_supply_weight = device_threshold.custom_supply_weight if device_threshold else 100.0
        except Exception:
            device_threshold = None
            custom_supply_weight = 100.0

        if custom_supply_weight is None or custom_supply_weight <= 0:
            custom_supply_weight = 100.0

        # Calculates the physical stock based on the raw weight and custom supply weight
        physical_stock = float(self.weight_record_service.calculate_physical_stock(weight, custom_supply_weight))

        # Creates a new weight record using the calculated physical stock
        record = self.weight_record_service.create_record(device_id, weight, physical_stock, created_at)

        # Persists the record and computes updated averages
        saved_record = self.weight_record_repository.save(record)

        # Evaluates the physical anomaly threshold
        anomaly_threshold = getattr(device_threshold, "anomaly_threshold", None)
        is_anomaly = self.weight_record_service.is_physical_anomaly(
            weight,
            custom_supply_weight,
            anomaly_threshold
        )

        logging.info(
            "Evaluating anomaly for device %s: weight=%s, custom_supply_weight=%s, anomaly_threshold=%s -> is_anomaly=%s",
            device_id, weight, custom_supply_weight, anomaly_threshold, is_anomaly
        )

        if is_anomaly:
            # Scenario 1: Anomaly detected, send POST to api/v1/anomalies
            created_at_iso = saved_record.created_at.isoformat() if hasattr(saved_record, "created_at") and saved_record.created_at else None
            self._send_anomaly_to_cloud(device_id, weight, created_at_iso)
        else:
            # Scenario 2: Variation within normal tolerance, discard cloud call
            logging.info("Weight variation within normal tolerance for device %s. Cloud anomaly report skipped.", device_id)

        # Retrieves recent records from the configured interval and computes the average
        recent_records = self.weight_record_repository.find_by_device_in_interval(device_id)
        averages = self.weight_record_service.calculate_averages(recent_records)

        # Retrieve the last registered environment record when available.
        environment_record_repository = getattr(self, "environment_record_repository", None)
        environment_record = (
            environment_record_repository.find_last_record_by_device(device_id)
            if environment_record_repository
            else None
        )
        logging.info(
            "Last environment record for device %s: temperature=%s, humidity=%s, timestamp=%s",
            device_id, environment_record.temperature if environment_record else None, environment_record.humidity if environment_record else None, environment_record.created_at.isoformat() if environment_record else None
        )

        # Sync data with the cloud API. Best-effort: never fails the local telemetry use-case.
        try:
            telemetry_sync_client.sync(device_threshold, record, environment_record)
        except Exception as ex:
            logging.exception("Unexpected error syncing weight telemetry to cloud: %s", ex)

        # Returns the saved record and updated averages
        return saved_record, averages


class EnvironmentRecordApplicationService:
    """Application service that orchestrates the creation of an environment record
    use-case.

    Responsibilities:

    1. Cross-context validation – delegates to the IAM
       :class:`~iam.infrastructure.repositories.DeviceRepository` to verify
       that the requesting device is registered and the supplied API key is
       valid.
    2. Domain logic – delegates to
       :class:`~tracking.domain.services.EnvironmentRecordService` to validate
       raw sensor values and construct an
       :class:`~tracking.domain.entities.EnvironmentRecord` entity.
    3. Persistence – delegates to
       :class:`~tracking.infrastructure.repositories.EnvironmentRecordRepository`
       to persist the entity and return the saved aggregate with its assigned
       identity.
    4. Aggregation – retrieves recent records from the configured interval and
       computes the average temperature and humidity through the domain
       service.
    """

    def __init__(self):
        """Initialize the service with its required collaborators."""
        self.environment_record_repository = EnvironmentRecordRepository()
        self.environment_record_service = EnvironmentRecordService()
        self.device_threshold_repository = DeviceThresholdRepository()
        self.device_repository = DeviceRepository()
        self.weight_record_repository = WeightRecordRepository()

    DEFAULT_MIN_TEMPERATURE_CELSIUS = 0.1
    DEFAULT_MAX_TEMPERATURE_CELSIUS = 90.1
    DEFAULT_MIN_HUMIDITY_PERCENTAGE = 0.1
    DEFAULT_MAX_HUMIDITY_PERCENTAGE = 90.1

    @staticmethod
    def _threshold_or_default(value: float | None, default: float) -> float:
        return default if value is None else float(value)

    def _get_thresholds_for_device(self, device_id: str) -> dict:
        try:
            threshold: DeviceThreshold = self.device_threshold_repository.get_by_device_id(device_id)
            return {
                "min_temperature": self._threshold_or_default(
                    threshold.minimum_temperature_in_celsius,
                    self.DEFAULT_MIN_TEMPERATURE_CELSIUS,
                ),
                "max_temperature": self._threshold_or_default(
                    threshold.maximum_temperature_in_celsius,
                    self.DEFAULT_MAX_TEMPERATURE_CELSIUS,
                ),
                "min_humidity": self._threshold_or_default(
                    threshold.minimum_humidity_percentage,
                    self.DEFAULT_MIN_HUMIDITY_PERCENTAGE,
                ),
                "max_humidity": self._threshold_or_default(
                    threshold.maximum_humidity_percentage,
                    self.DEFAULT_MAX_HUMIDITY_PERCENTAGE,
                ),
                "assigned_batch_id": threshold.assigned_batch_id,
            }
        except Exception:
            return {
                "min_temperature": self.DEFAULT_MIN_TEMPERATURE_CELSIUS,
                "max_temperature": self.DEFAULT_MAX_TEMPERATURE_CELSIUS,
                "min_humidity": self.DEFAULT_MIN_HUMIDITY_PERCENTAGE,
                "max_humidity": self.DEFAULT_MAX_HUMIDITY_PERCENTAGE,
                "assigned_batch_id": None,
            }

    @staticmethod
    def _is_outside_range(value: float, minimum: float, maximum: float) -> bool:
        return value < minimum or value > maximum

    @staticmethod
    def _send_environment_telemetry_to_cloud(
        threshold: DeviceThreshold | None,
        weight_record: WeightRecord | None,
        environment_record: EnvironmentRecord,
    ) -> None:
        try:
            telemetry_sync_client.sync(threshold, weight_record, environment_record)
        except Exception as ex:
            logging.exception("Unexpected error syncing environment telemetry to cloud: %s", ex)

    def create_environment_record(
        self,
        device_id: str,
        temperature: float,
        humidity: float,
        created_at: str | None,
    ) -> tuple:
        """Execute the creation and processing of an environment record use-case.

        Validates that the device identified by ``device_id`` is registered and
        that the supplied ``api_key`` matches the stored credential before
        delegating record creation to the domain service, persisting the
        result, and computing updated averages.

        Args:
            device_id (str): Identifier of the device submitting the reading.
            temperature (float): Temperature measurement expressed in degrees
                Celsius.
            humidity (float): Relative humidity measurement expressed as a
                percentage.
            created_at (str | None): ISO 8601 timestamp of the reading. Passed
                to the domain service; accepts ``None`` to default to the
                current UTC time.

        Returns:
            tuple[EnvironmentRecord, dict]: A two-element tuple containing the
            persisted domain entity and a dictionary with
            ``average_temperature`` and ``average_humidity`` keys.

        Raises:
            ValueError: If no device matches the ``device_id`` / ``api_key``
            combination, or if the domain service rejects the sensor values.
        """
        if not self.device_repository.find_by_id(device_id):
            raise ValueError("Device not found")

        thresholds = self._get_thresholds_for_device(device_id)

        try:
            threshold: DeviceThreshold | None = self.device_threshold_repository.get_by_device_id(device_id)
        except Exception:
            threshold = None

        temperature_is_anomaly = self._is_outside_range(
            float(temperature),
            thresholds["min_temperature"],
            thresholds["max_temperature"],
        )
        humidity_is_anomaly = self._is_outside_range(
            float(humidity),
            thresholds["min_humidity"],
            thresholds["max_humidity"],
        )

        record = self.environment_record_service.create_record(
            device_id,
            temperature,
            humidity,
            created_at,
            temperature_is_anomaly,
            humidity_is_anomaly,
        )
        saved_record = self.environment_record_repository.save(record)

        recent_records = self.environment_record_repository.find_by_device_in_interval(
            device_id
        )
        averages = self.environment_record_service.calculate_averages(recent_records)

        # Fetch the last weight record when available.
        weight_record_repository = getattr(self, "weight_record_repository", None)
        last_weight_record = (
            weight_record_repository.find_last_record_by_device(device_id)
            if weight_record_repository
            else None
        )

        # Sync data with the cloud API after local persistence. Cloud sync must
        # not block the MQTT response expected by the embedded device.
        self._send_environment_telemetry_to_cloud(threshold, last_weight_record, record)

        return saved_record, averages
