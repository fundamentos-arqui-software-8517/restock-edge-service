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
        record.created_at = datetime.now(timezone.utc)

        with patch("tracking.interfaces.rest_services.weight_record_service") as mock_svc, \
                patch("iam.interfaces.services.authenticate_request", return_value=None):
            mock_svc.create_weight_record.return_value = record
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
        """IT-ES-02d: Missing humidity field → 400 Bad Request."""
        with patch("iam.interfaces.services.authenticate_request", return_value=None):
            response = client.post(
                "/api/v1/tracking/environment-records",
                data=json.dumps({"device_id": "device-1", "temperature": 25.0}),
                content_type="application/json",
            )

        assert response.status_code == 400
