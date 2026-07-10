"""Internal telemetry facade for the Tracking bounded context."""
import logging

from iam.application.services import AuthApplicationService
from tracking.application.services import (
    EnvironmentRecordApplicationService,
    WeightRecordApplicationService,
)


class TelemetryProcessor:
    """Facade that routes Tracking telemetry to the existing application services.

    The processor does not own persistence, validation rules, anomaly detection
    or cloud synchronization. Those responsibilities remain in the application
    and domain services already used by the REST and MQTT adapters.
    """

    def __init__(
        self,
        weight_record_service: WeightRecordApplicationService | None = None,
        environment_record_service: EnvironmentRecordApplicationService | None = None,
        device_service: AuthApplicationService | None = None,
    ):
        self.weight_record_service = weight_record_service or WeightRecordApplicationService()
        self.environment_record_service = (
            environment_record_service or EnvironmentRecordApplicationService()
        )
        self.device_service = device_service or AuthApplicationService()

    def process_rest_weight_record(self, device_id, weight, created_at):
        """Process a REST weight telemetry request using the existing use case."""
        return self.weight_record_service.create_weight_record(
            device_id,
            weight,
            created_at,
        )

    def process_rest_environment_record(self, device_id, temperature, humidity, created_at):
        """Process a REST environment telemetry request using the existing use case."""
        return self.environment_record_service.create_environment_record(
            device_id,
            temperature,
            humidity,
            created_at,
        )

    def process_mqtt_weight_record(self, device_id, payload):
        """Process an Embedded MQTT weight payload and return its response body."""
        raw_weight = float(payload["raw_weight"])
        created_at = str(payload["created_at"])

        logging.info(
            "Weight received at %s for device %s with value %s",
            created_at,
            device_id,
            raw_weight,
        )

        record, averages = self.weight_record_service.create_weight_record(
            device_id=device_id,
            weight=raw_weight,
            created_at=created_at,
        )
        device = self.device_service.get_by_id(device_id)

        return {
            "id": record.weight_record_id,
            "device_id": record.device_id,
            "raw_weight": record.raw_weight,
            "physical_stock": record.physical_stock,
            "created_at": record.created_at.isoformat(),
            "average_physical_stock": averages["average_physical_stock"],
            "display_mode": device.display_mode,
        }

    def process_mqtt_environment_record(self, device_id, payload):
        """Process an Embedded MQTT environment payload and return its response body."""
        temperature = float(payload["temperature"])
        humidity = float(payload["humidity"])
        created_at = str(payload["created_at"])

        logging.info(
            "Environment telemetry received at %s for device %s with temperature %s and humidity %s",
            created_at,
            device_id,
            temperature,
            humidity,
        )

        record, averages = self.environment_record_service.create_environment_record(
            device_id=device_id,
            temperature=temperature,
            humidity=humidity,
            created_at=created_at,
        )
        device = self.device_service.get_by_id(device_id)

        return {
            "id": record.id,
            "device_id": record.device_id,
            "temperature": record.temperature,
            "humidity": record.humidity,
            "temperature_is_anomaly": record.temperature_is_anomaly,
            "humidity_is_anomaly": record.humidity_is_anomaly,
            "created_at": record.created_at.isoformat(),
            "average_temperature": averages["average_temperature"],
            "average_humidity": averages["average_humidity"],
            "display_mode": device.display_mode,
        }
