import json
import logging
import os
from urllib import error, request

from devices.domain.entities import DeviceStatusReport
from devices.domain.entities import DeviceThreshold
from devices.domain.services import DeviceStatusService
from devices.domain.services import DeviceThresholdService
from devices.infrastructure.repositories import DeviceHealthEventRepository
from devices.infrastructure.repositories import DeviceStatusReportRepository
from devices.infrastructure.repositories import DeviceThresholdRepository
from iam.infrastructure.repositories import DeviceRepository


class DeviceThresholdApplicationService:
    """
    Application service that orchestrates the registering of a device threshold use-case.

    Attributes:
        device_threshold_repository: (DeviceThresholdRepository) The device threshold repository.
        device_threshold_service: (DeviceThresholdService) The device threshold service.
    """

    def __init__(self):
        """ Initialize the device threshold application service. """
        self.device_threshold_repository = DeviceThresholdRepository()
        self.device_threshold_service = DeviceThresholdService()
        self.device_repository = DeviceRepository()

    def create_device_threshold(
        self,
        device_id: str,
        assigned_batch_id: str,
        custom_supply_unit_measurement: str | None,
        minimum_humidity_percentage: float,
        maximum_humidity_percentage: float,
        minimum_temperature_in_celsius: float,
        maximum_temperature_in_celsius: float,
        custom_supply_weight: float | None = 100.0,
        anomaly_threshold: float | None = None,
    ) -> DeviceThreshold:
        record = self.device_threshold_service.create_threshold_for_device(
            device_id=device_id,
            assigned_batch_id=assigned_batch_id,
            custom_supply_unit_measurement=custom_supply_unit_measurement,
            minimum_humidity_percentage=minimum_humidity_percentage,
            maximum_humidity_percentage=maximum_humidity_percentage,
            minimum_temperature_in_celsius=minimum_temperature_in_celsius,
            maximum_temperature_in_celsius=maximum_temperature_in_celsius,
            custom_supply_weight=custom_supply_weight,
            anomaly_threshold=anomaly_threshold,
        )

        return self.device_threshold_repository.save(record)

    def calibrate_custom_supply_weight(
            self,
            device_id: str,
            custom_supply_weight: float,
    ) -> DeviceThreshold:
        return self.device_threshold_repository.calibrate_custom_supply_weight(
            device_id,
            custom_supply_weight
        )

    def update_device_threshold(
            self,
            device_id: str,
            assigned_batch_id: str,
            custom_supply_unit_measurement: str | None,
            minimum_humidity_percentage: float,
            maximum_humidity_percentage: float,
            minimum_temperature_in_celsius: float,
            maximum_temperature_in_celsius: float,
            custom_supply_weight: float | None = None,
            anomaly_threshold: float | None = None,
    ) -> DeviceThreshold:
        try:
            record = self.device_threshold_repository.get_by_device_id(device_id)
            threshold_id = record.threshold_id
            if custom_supply_weight is None:
                custom_supply_weight = record.custom_supply_weight
            if anomaly_threshold is None:
                anomaly_threshold = getattr(record, "anomaly_threshold", None)
        except Exception:
            threshold_id = 0

        updated_threshold = self.device_threshold_service.create_threshold_for_device(
            threshold_id=threshold_id,
            device_id=device_id,
            assigned_batch_id=assigned_batch_id,
            custom_supply_weight=custom_supply_weight,
            custom_supply_unit_measurement=custom_supply_unit_measurement,
            minimum_humidity_percentage=minimum_humidity_percentage,
            maximum_humidity_percentage=maximum_humidity_percentage,
            minimum_temperature_in_celsius=minimum_temperature_in_celsius,
            maximum_temperature_in_celsius=maximum_temperature_in_celsius,
            anomaly_threshold=anomaly_threshold,
        )

        return self.device_threshold_repository.update(updated_threshold)


class DeviceStatusApplicationService:
    """
    Application service that orchestrates device health status registration.

    MQTT is the real source of embedded health telemetry. HTTP delegates to the
    same service only as a fallback/testing path, preserving one use-case for
    evaluation, persistence and cloud reporting.
    """

    def __init__(self):
        """Initialize the device status application service."""
        self.device_status_service = DeviceStatusService()
        self.device_status_report_repository = DeviceStatusReportRepository()
        self.device_health_event_repository = DeviceHealthEventRepository()
        self.device_repository = DeviceRepository()

    def register_status(self, payload: dict, source: str = "HTTP") -> dict:
        """
        Register an embedded-style device health status report.

        :param payload: Raw HealthTelemetryPackage received from MQTT or simulated through HTTP.
        :param source: Input source, usually MQTT or HTTP.
        :return: Result dictionary containing persisted report, optional event and response metadata.
        :raise ValueError: If the payload is invalid or the device is not registered.
        """
        report, event, evaluation = self.device_status_service.create_status_report(
            payload,
            source=source,
        )

        if not self.device_repository.find_by_id(report.device_id):
            raise LookupError("Device not found")

        saved_report = self.device_status_report_repository.save(report)
        saved_event = None
        if event:
            saved_event = self.device_health_event_repository.save(event)

        if saved_event and saved_report.critical:
            self._send_device_event_to_cloud(saved_report, saved_event)

        return {
            "report": saved_report,
            "event": saved_event,
            "health_status": saved_report.health_status,
            "critical": saved_report.critical,
            "metric": evaluation.get("metric"),
            "reason": evaluation.get("reason"),
            "event_registered": saved_event is not None,
            "message": "Device status registered successfully",
        }

    def _send_device_event_to_cloud(self, report: DeviceStatusReport, event) -> None:
        """
        Send a critical device health event to the configured cloud endpoint.

        The call is best-effort: missing configuration or network errors are
        logged and never fail the local status registration flow.
        """
        events_url = os.getenv("CLOUD_DEVICE_EVENTS_URL")

        if not events_url:
            logging.info("Cloud device event sync skipped: CLOUD_DEVICE_EVENTS_URL is not configured")
            return

        payload = {
            "deviceId": report.device_id,
            "branchId": report.branch_id,
            "healthStatus": report.health_status,
            "eventType": event.event_type,
            "metric": event.metric,
            "value": event.value,
            "threshold": event.threshold,
            "reason": event.reason,
            "message": event.message,
            "source": event.source,
            "createdAt": event.created_at.isoformat(),
        }
        headers = {"Content-Type": "application/json"}

        body = json.dumps(payload).encode("utf-8")
        cloud_request = request.Request(
            events_url,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(cloud_request, timeout=5) as response:
                logging.info(
                    "Device health event synced to cloud with status %s",
                    response.status,
                )
        except (error.HTTPError, error.URLError, TimeoutError) as ex:
            logging.exception("Error syncing device health event to cloud: %s", ex)
        except Exception as ex:
            logging.exception("Unexpected error syncing device health event: %s", ex)
