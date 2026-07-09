"""Integration tests for the Tracking REST interface (Flask Blueprint).

Uses Flask's built-in test client to send real HTTP requests against the
registered routes while mocking the application-service layer so that no
database or external HTTP calls are made.

Related User Stories:
  US-ES-01 – Register weight telemetry reading from device
  US-ES-02 – Register environment telemetry reading from device
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from tracking.domain.entities import WeightRecord, EnvironmentRecord
from devices.domain.services import DeviceStatusSemanticError


@pytest.fixture
def app():
    """Create a minimal Flask app with the tracking blueprint registered."""
    from flask import Flask
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True

    # Patch service constructors before blueprint registration
    with patch("tracking.application.services.WeightRecordRepository"), \
         patch("tracking.application.services.EnvironmentRecordRepository"), \
         patch("tracking.application.services.DeviceThresholdRepository"), \
         patch("tracking.application.services.WeightRecordService"), \
         patch("tracking.application.services.EnvironmentRecordService"), \
         patch("tracking.application.services.DeviceRepository"), \
         patch("iam.interfaces.services.authenticate_request", return_value=None):
        from tracking.interfaces.rest_services import tracking_api
        flask_app.register_blueprint(tracking_api)

    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def devices_app():
    """Create a minimal Flask app with the devices blueprint registered."""
    from flask import Flask
    from devices.interfaces.services import devices_api

    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    flask_app.register_blueprint(devices_api)
    return flask_app


@pytest.fixture
def devices_client(devices_app):
    return devices_app.test_client()


# ---------------------------------------------------------------------------
# POST /api/v1/tracking/weight-records
# ---------------------------------------------------------------------------

class TestWeightRecordEndpoint:
    """IT-ES-01 – POST /api/v1/tracking/weight-records"""

    def test_returns_201_on_success(self, client):
        """IT-ES-01a: Valid payload returns 201 Created."""
        record = MagicMock()
        record.id = 1
        record.device_id = "device-1"
        record.weight = 500.0
        record.physical_stock = 5.0
        record.created_at = datetime.now(timezone.utc)

        with patch("tracking.interfaces.rest_services.weight_record_service") as mock_svc, \
                patch("iam.interfaces.services.authenticate_request", return_value=None):
            mock_svc.create_weight_record.return_value = (
                record, {"average_physical_stock": 5.0}
            )
            response = client.post(
                "/api/v1/tracking/weight-records",
                data=json.dumps({"device_id": "device-1", "weight": 500.0}),
                content_type="application/json",
            )

        assert response.status_code == 201

    def test_returns_400_when_device_not_found(self, client):
        """IT-ES-01b: Unknown device_id → 400 Bad Request."""
        with patch("tracking.interfaces.rest_services.weight_record_service") as mock_svc, \
             patch("iam.interfaces.services.authenticate_request", return_value=None):
            mock_svc.create_weight_record.side_effect = ValueError("Device not found")
            response = client.post(
                "/api/v1/tracking/weight-records",
                data=json.dumps({"device_id": "unknown", "weight": 500.0}),
                content_type="application/json",
            )

        assert response.status_code == 400
        body = response.get_json()
        assert "error" in body

    def test_returns_400_when_field_missing(self, client):
        """IT-ES-01c: Missing weight field → 400 Bad Request."""
        with patch("iam.interfaces.services.authenticate_request", return_value=None):
            response = client.post(
                "/api/v1/tracking/weight-records",
                data=json.dumps({"device_id": "device-1"}),
                content_type="application/json",
            )

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/v1/tracking/environment-records
# ---------------------------------------------------------------------------

class TestEnvironmentRecordEndpoint:
    """IT-ES-02 – POST /api/v1/tracking/environment-records"""

    def _make_env_record(self, temp_anomaly=False, hum_anomaly=False):
        record = EnvironmentRecord(
            "device-1", 25.0, 60.0, datetime.now(timezone.utc),
            temperature_is_anomaly=temp_anomaly,
            humidity_is_anomaly=hum_anomaly,
        )
        record.id = 42
        return record

    def test_returns_200_on_success(self, client):
        """IT-ES-02a: Valid payload returns 200 OK."""
        record = self._make_env_record()

        with patch("tracking.interfaces.rest_services.environment_record_service") as mock_svc, \
             patch("iam.interfaces.services.authenticate_request", return_value=None):
            mock_svc.create_environment_record.return_value = (
                record, {"average_temperature": 25.0, "average_humidity": 60.0}
            )
            response = client.post(
                "/api/v1/tracking/environment-records",
                data=json.dumps({"device_id": "device-1", "temperature": 25.0, "humidity": 60.0}),
                content_type="application/json",
            )

        assert response.status_code == 200
        body = response.get_json()
        assert body["temperature"] == 25.0
        assert body["humidity"] == 60.0
        assert body["average_temperature"] == 25.0

    def test_anomaly_flags_are_present_in_response(self, client):
        """IT-ES-02b: Response body includes anomaly flag fields."""
        record = self._make_env_record(temp_anomaly=True)

        with patch("tracking.interfaces.rest_services.environment_record_service") as mock_svc, \
             patch("iam.interfaces.services.authenticate_request", return_value=None):
            mock_svc.create_environment_record.return_value = (
                record, {"average_temperature": 50.0, "average_humidity": 60.0}
            )
            response = client.post(
                "/api/v1/tracking/environment-records",
                data=json.dumps({"device_id": "device-1", "temperature": 50.0, "humidity": 60.0}),
                content_type="application/json",
            )

        body = response.get_json()
        assert "temperature_is_anomaly" in body
        assert body["temperature_is_anomaly"] is True

    def test_returns_400_when_device_not_found(self, client):
        """IT-ES-02c: Unknown device → 400 Bad Request."""
        with patch("tracking.interfaces.rest_services.environment_record_service") as mock_svc, \
             patch("iam.interfaces.services.authenticate_request", return_value=None):
            mock_svc.create_environment_record.side_effect = ValueError("Device not found")
            response = client.post(
                "/api/v1/tracking/environment-records",
                data=json.dumps({"device_id": "unknown", "temperature": 25.0, "humidity": 60.0}),
                content_type="application/json",
            )

        assert response.status_code == 400

    def test_returns_400_when_humidity_missing(self, client):
        """IT-ES-02d: Missing humidity field -> 400 Bad Request."""
        with patch("iam.interfaces.services.authenticate_request", return_value=None):
            response = client.post(
                "/api/v1/tracking/environment-records",
                data=json.dumps({"device_id": "device-1", "temperature": 25.0}),
                content_type="application/json",
            )

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/v1/devices/status
# ---------------------------------------------------------------------------

class TestDeviceStatusEndpoint:
    """TS-45 - POST /api/v1/devices/status"""

    def _status_result(
            self,
            health_status="INFO",
            critical=False,
            event_registered=True,
            metric="reset_reason",
            reason="Device boot/reset reason reported",
    ):
        report = MagicMock()
        report.device_id = "device-1"
        return {
            "report": report,
            "health_status": health_status,
            "critical": critical,
            "event_registered": event_registered,
            "metric": metric,
            "reason": reason,
        }

    def test_returns_201_for_boot_reset_status(self, devices_client):
        """Valid BOOT_RESET_REASON health report returns 201 Created."""
        with patch("devices.interfaces.services.authenticate_request", return_value=None), \
                patch("devices.interfaces.services.device_status_service") as mock_svc:
            mock_svc.register_status.return_value = self._status_result()
            response = devices_client.post(
                "/api/v1/devices/status",
                data=json.dumps({
                    "device_id": "device-1",
                    "branch_id": "branch-001",
                    "alert_type": "BOOT_RESET_REASON",
                    "metric": "reset_reason",
                    "value": "POWER_ON",
                    "threshold": "",
                    "message": "Device booted after power-on reset.",
                    "timestamp_ms": 123456,
                }),
                content_type="application/json",
            )

        body = response.get_json()
        assert response.status_code == 201
        assert body["health_status"] == "INFO"
        assert body["critical"] is False
        assert body["event_registered"] is True

    def test_returns_201_for_critical_cpu_status(self, devices_client):
        """Valid critical CPU report returns 201 Created, not 422."""
        with patch("devices.interfaces.services.authenticate_request", return_value=None), \
                patch("devices.interfaces.services.device_status_service") as mock_svc:
            mock_svc.register_status.return_value = self._status_result(
                health_status="CRITICAL",
                critical=True,
                event_registered=True,
                metric="cpu",
                reason="CPU usage threshold breached",
            )
            response = devices_client.post(
                "/api/v1/devices/status",
                data=json.dumps({
                    "device_id": "device-1",
                    "branch_id": "branch-001",
                    "alert_type": "HEALTH_ANOMALY",
                    "metric": "cpu",
                    "value": "90.1",
                    "threshold": "85.0",
                    "message": "High CPU usage threshold breached.",
                    "timestamp_ms": 123456,
                }),
                content_type="application/json",
            )

        body = response.get_json()
        assert response.status_code == 201
        assert body["health_status"] == "CRITICAL"
        assert body["critical"] is True
        assert body["event_registered"] is True
        assert body["metric"] == "cpu"

    def test_returns_201_for_embedded_health_anomaly(self, devices_client):
        """Valid embedded HEALTH_ANOMALY payload returns 201 Created."""
        with patch("devices.interfaces.services.authenticate_request", return_value=None), \
                patch("devices.interfaces.services.device_status_service") as mock_svc:
            mock_svc.register_status.return_value = self._status_result(
                health_status="CRITICAL",
                critical=True,
                event_registered=True,
                metric="cpu",
                reason="Health anomaly reported by device",
            )
            response = devices_client.post(
                "/api/v1/devices/status",
                data=json.dumps({
                    "device_id": "device-1",
                    "branch_id": "branch-001",
                    "alert_type": "HEALTH_ANOMALY",
                    "metric": "cpu",
                    "value": "90.1",
                    "threshold": "85.0",
                    "message": "High CPU usage threshold breached.",
                    "timestamp_ms": 123456,
                }),
                content_type="application/json",
            )

        body = response.get_json()
        assert response.status_code == 201
        assert body["health_status"] == "CRITICAL"
        assert body["critical"] is True
        assert body["event_registered"] is True

    def test_returns_422_for_semantically_invalid_payload(self, devices_client):
        """Semantically invalid payload returns 422 Unprocessable Entity."""
        with patch("devices.interfaces.services.authenticate_request", return_value=None), \
                patch("devices.interfaces.services.device_status_service") as mock_svc:
            mock_svc.register_status.side_effect = DeviceStatusSemanticError(
                "Unsupported alert_type: UNKNOWN"
            )
            response = devices_client.post(
                "/api/v1/devices/status",
                data=json.dumps({
                    "device_id": "device-1",
                    "branch_id": "branch-001",
                    "alert_type": "UNKNOWN",
                    "metric": "cpu",
                    "value": "90.1",
                    "threshold": "85.0",
                    "message": "Unsupported alert.",
                    "timestamp_ms": 123456,
                }),
                content_type="application/json",
            )

        body = response.get_json()
        assert response.status_code == 422
        assert "error" in body

    def _returns_400_when_humidity_missing_duplicate(self, client):
        """IT-ES-02d: Missing humidity field → 400 Bad Request."""
        with patch("iam.interfaces.services.authenticate_request", return_value=None):
            response = client.post(
                "/api/v1/tracking/environment-records",
                data=json.dumps({"device_id": "device-1", "temperature": 25.0}),
                content_type="application/json",
            )

        assert response.status_code == 400
