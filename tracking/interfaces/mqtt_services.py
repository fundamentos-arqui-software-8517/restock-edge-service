import json
import logging

from tracking.application.services import WeightRecordApplicationService, EnvironmentRecordApplicationService

# Module-level singleton; it contains no request-specific mutable state.
weight_record_service = WeightRecordApplicationService()

# Module-level singleton for environment record operations.
environment_record_service = EnvironmentRecordApplicationService()


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
        response_topic = f"store/{device_id}/response/{telemetry_type}"

        # Calls the publish method of the MQTT service to publish the response to the response topic
        mqtt_service.publish(response_topic, response, qos=1)

        logging.info("Response send to response topic %s",response_topic)
    except Exception as ex:
        logging.exception("Error while publishing response: %s", ex)
        raise ValueError(f"Error while publishing response: {ex}")


def create_weight_record(device_id, payload):
    """
    Handles the weight telemetry message and orchestrates the process of converting and persisting the telemetry data.

    :param device_id: The ID of the device that sent the telemetry message.
    :param payload: The payload of the telemetry message.
    """

    raw_weight = float(payload["raw_weight"])
    created_at = str(payload["created_at"])

    logging.info("Weight received at %s for device %s with value %s",
                 created_at,
                 device_id,
                 raw_weight
    )

    # Creates a new weight record using the application service
    record, averages = weight_record_service.create_weight_record(
        device_id=device_id,
        weight=raw_weight,
        created_at=created_at
    )

    # Builds the response to be sent back to the device in a response topic
    response = {
        "id": record.weight_record_id,
        "device_id": record.device_id,
        "raw_weight": record.raw_weight,
        "physical_stock": record.physical_stock,
        "created_at": record.created_at.isoformat(),
        "average_physical_stock": averages["average_physical_stock"],
    }

    # Publishes the response to the response topic
    publish_telemetry_response(device_id, "weight", response)


def create_environment_record(device_id, payload):
    """
    Handles the environment telemetry message and orchestrates the process of converting and persisting the telemetry data.

    :param device_id: The ID of the device that sent the telemetry message.
    :param payload: The payload of the telemetry message.
    """

    temperature = float(payload["temperature"])
    humidity = float(payload["humidity"])
    created_at = str(payload["created_at"])

    logging.info("Environment telemetry received at %s for device %s with temperature %s and humidity %s",
                 created_at,
                 device_id,
                 temperature,
                 humidity
    )

    # Creates a new environment record using the application service
    record, averages = environment_record_service.create_environment_record(
        device_id=device_id,
        temperature=temperature,
        humidity=humidity,
        created_at=created_at
    )

    # Builds the response to be sent back to the device in a response topic
    response = {
        "id": record.id,
        "device_id": record.device_id,
        "temperature": record.temperature,
        "humidity": record.humidity,
        "temperature_is_anomaly": record.temperature_is_anomaly,
        "humidity_is_anomaly": record.humidity_is_anomaly,
        "created_at": record.created_at.isoformat(),
        "average_temperature": averages["average_temperature"],
        "average_humidity": averages["average_humidity"],
    }

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
        logging.exception("Error while processing MQTT message: %s",ex)
