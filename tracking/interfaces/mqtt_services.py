import json
import logging

from tracking.application.telemetry_processor import TelemetryProcessor

# Module-level singleton; it contains no request-specific mutable state.
telemetry_processor = TelemetryProcessor()


def validate_telemetry_payload(payload, telemetry_type: str):
    """
    Validate the payload of the telemetry message.

    :param payload: The payload of the telemetry message.
    :param telemetry_type: The type of telemetry message.

    :raise ValueError: If the payload is invalid.
    """

    # Validates the telemetry type
    if telemetry_type not in ["weight", "environment", "health"]:
        raise ValueError("Invalid telemetry type")

    # Assigns the required fields based on the telemetry type
    required_fields = []
    match telemetry_type:
        case "weight":
            required_fields = [
                "raw_weight",
                "created_at"
            ]

        case "environment":
            required_fields = [
                "temperature",
                "humidity",
                "created_at"
            ]

        case "health":
            pass

    # Validates that all required fields are present in the payload
    for field in required_fields:
        if field not in payload:
            logging.error("Required field is missing in %s telemetry: %s", telemetry_type, field)
            raise ValueError(f"Required field is missing in {telemetry_type} telemetry: {field}")


def publish_telemetry_response(device_id, telemetry_type, response):
    """
    Function that publishes the response to the response topic.

    :param device_id: The device ID.
    :param telemetry_type: The type of telemetry message.
    :param response: The response to be published, which will be converted to JSON before publishing.

    :raise ValueError: If there is an error while publishing the response.
    """

    # Deferred import of the mqtt_service singleton to avoid circular imports
    from shared.infrastructure.mqtt_client import mqtt_service

    try:
        # Construct the response topic based on the device ID and telemetry type
        response_topic = f"stores/{device_id}/response/{telemetry_type}"

        # Calls the publish method of the MQTT service to publish the response to the response topic
        mqtt_service.publish(response_topic, response, qos=1)

        logging.info("Response send to response topic %s", response_topic)
    except Exception as ex:
        logging.exception("Error while publishing response: %s", ex)
        raise ValueError(f"Error while publishing response: {ex}")


def create_weight_record(device_id, payload):
    """
    Handles the weight telemetry message and orchestrates the process of converting and persisting the telemetry data.

    :param device_id: The ID of the device that sent the telemetry message.
    :param payload: The payload of the telemetry message.
    """

    response = telemetry_processor.process_mqtt_weight_record(device_id, payload)

    # Publishes the response to the response topic
    publish_telemetry_response(device_id, "weight", response)


def create_environment_record(device_id, payload):
    """
    Handles the environment telemetry message and orchestrates the process of converting and persisting the telemetry data.

    :param device_id: The ID of the device that sent the telemetry message.
    :param payload: The payload of the telemetry message.
    """

    response = telemetry_processor.process_mqtt_environment_record(device_id, payload)

    # Publishes the response to the response topic
    publish_telemetry_response(device_id, "environment", response)


def on_tracking_telemetry_message(msg, topic_parts):
    """
    Validates the type of telemetry message and calls the appropriate handler.

    :param msg: The MQTT message.
    :param topic_parts: The topic parts, divided from the original topic string.

    :raise ValueError: If the telemetry type is unknown.
    """

    try:
        # Gets the device ID and telemetry type from the topic parts
        device_id = topic_parts[1]
        telemetry_type = topic_parts[3]

        # Decode the payload from the message
        payload = json.loads(msg.payload.decode("utf-8"))

        # Validates the payload of the telemetry message based on the telemetry type
        validate_telemetry_payload(payload, telemetry_type)

        # Sets up the mapping of telemetry types to their respective handlers
        handlers = {
            "weight": create_weight_record,
            "environment": create_environment_record,
            "health": "",

        }

        # Assigns the appropriate handler based on the telemetry type
        handler = handlers.get(telemetry_type)

        if handler is None:
            logging.warning("Telemetry type unknown or not implemented: %s", telemetry_type)
            return

        handler(device_id, payload)
    except Exception as ex:
        logging.exception("Error while processing MQTT message: %s", ex)
