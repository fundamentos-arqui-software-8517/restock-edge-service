"""Regression tests for Tracking telemetry received through MQTT."""
import json
from unittest.mock import patch


class FakeMqttMessage:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")


def test_weight_mqtt_payload_is_processed_and_published_to_same_response_topic():
    payload = {
        "raw_weight": 500.0,
        "created_at": "2026-05-25T12:00:00-05:00",
    }
    response_payload = {
        "id": 1,
        "device_id": "device-1",
        "raw_weight": 500.0,
        "physical_stock": 5.0,
        "created_at": "2026-05-25T17:00:00+00:00",
        "average_physical_stock": 5.0,
        "display_mode": "UNITS",
    }

    with patch("tracking.interfaces.mqtt_services.telemetry_processor") as processor, \
         patch("tracking.interfaces.mqtt_services.publish_telemetry_response") as publish:
        processor.process_mqtt_weight_record.return_value = response_payload

        from tracking.interfaces.mqtt_services import on_tracking_telemetry_message
        on_tracking_telemetry_message(
            FakeMqttMessage(payload),
            ["stores", "device-1", "telemetry", "weight"],
        )

    processor.process_mqtt_weight_record.assert_called_once_with("device-1", payload)
    publish.assert_called_once_with("device-1", "weight", response_payload)


def test_environment_mqtt_payload_is_processed_and_published_to_same_response_topic():
    payload = {
        "temperature": 25.0,
        "humidity": 60.0,
        "created_at": "2026-05-25T12:00:00-05:00",
    }
    response_payload = {
        "id": 42,
        "device_id": "device-1",
        "temperature": 25.0,
        "humidity": 60.0,
        "temperature_is_anomaly": False,
        "humidity_is_anomaly": False,
        "created_at": "2026-05-25T17:00:00+00:00",
        "average_temperature": 25.0,
        "average_humidity": 60.0,
        "display_mode": "TEMPERATURE",
    }

    with patch("tracking.interfaces.mqtt_services.telemetry_processor") as processor, \
         patch("tracking.interfaces.mqtt_services.publish_telemetry_response") as publish:
        processor.process_mqtt_environment_record.return_value = response_payload

        from tracking.interfaces.mqtt_services import on_tracking_telemetry_message
        on_tracking_telemetry_message(
            FakeMqttMessage(payload),
            ["stores", "device-1", "telemetry", "environment"],
        )

    processor.process_mqtt_environment_record.assert_called_once_with("device-1", payload)
    publish.assert_called_once_with("device-1", "environment", response_payload)


def test_invalid_mqtt_payload_keeps_existing_no_publish_behavior():
    payload = {
        "raw_weight": 500.0,
    }

    with patch("tracking.interfaces.mqtt_services.telemetry_processor") as processor, \
         patch("tracking.interfaces.mqtt_services.publish_telemetry_response") as publish:
        from tracking.interfaces.mqtt_services import on_tracking_telemetry_message
        on_tracking_telemetry_message(
            FakeMqttMessage(payload),
            ["stores", "device-1", "telemetry", "weight"],
        )

    processor.process_mqtt_weight_record.assert_not_called()
    publish.assert_not_called()


def test_mqtt_response_topic_and_qos_are_unchanged():
    response_payload = {
        "id": 1,
        "device_id": "device-1",
        "raw_weight": 500.0,
        "physical_stock": 5.0,
        "created_at": "2026-05-25T17:00:00+00:00",
        "average_physical_stock": 5.0,
        "display_mode": "UNITS",
    }

    with patch("shared.infrastructure.mqtt_client.mqtt_service") as mqtt_service:
        from tracking.interfaces.mqtt_services import publish_telemetry_response
        publish_telemetry_response("device-1", "weight", response_payload)

    mqtt_service.publish.assert_called_once_with(
        "stores/device-1/response/weight",
        response_payload,
        qos=1,
    )
