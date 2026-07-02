"""Interface layer for the Tracking bounded context.

Exposes a Flask Blueprint (``tracking_api``) that translates incoming HTTP
requests into calls to the application service and maps the results back to
JSON responses.  This layer owns no domain logic; it is responsible for I/O
concerns such as request parsing, authentication delegation and HTTP status
code selection.
"""
from flask import Blueprint, jsonify, request

from iam.interfaces.services import authenticate_request
from tracking.application.services import WeightRecordApplicationService
from tracking.application.services import EnvironmentRecordApplicationService


tracking_api = Blueprint("tracking_api", __name__)

# Module-level singleton; it contains no request-specific mutable state.
weight_record_service = WeightRecordApplicationService()

# Module-level singleton for environment record operations.
environment_record_service = EnvironmentRecordApplicationService()


@tracking_api.route("/api/v1/tracking/weight-records", methods=["POST"])
def create_weight_record():
    """Create a new weight telemetry record.

    Validates device identity through the ``X-API-Key`` header and the
    ``device_id`` field in the request body before delegating to the
    application service to apply domain rules and persist the record.

    Request headers:
        X-API-Key: API key paired with the device.
        Content-Type: Must be ``application/json``.

    Request body:
        ``device_id`` (str): Identifier of the submitting device.
        ``weight`` (float): Weight reading expressed in grams.
        ``created_at`` (str, optional): ISO 8601 timestamp. Defaults to the
        current UTC time when omitted.

    Responses:
        201 Created: Record saved successfully. Body contains the persisted
        record with its assigned ``id`` and UTC ``created_at``.
        400 Bad Request: A required field is missing or a value is invalid.
        401 Unauthorized: ``device_id`` or ``X-API-Key`` is absent or invalid.

    Returns:
        tuple[flask.Response, int]: JSON response body paired with the
        appropriate HTTP status code.
    """
    auth_result = authenticate_request()
    if auth_result:
        return auth_result

    data = request.json
    try:
        device_id = data["device_id"]
        weight = data["weight"]
        created_at = data.get("created_at")
        record = weight_record_service.create_weight_record(
            device_id,
            weight,
            created_at,
        )
        return jsonify({
            "id": record.id,
            "device_id": record.device_id,
            "weight": record.weight,
            "created_at": record.created_at.isoformat(),
        }), 201
    except KeyError:
        return jsonify({"error": "Missing required fields"}), 400
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@tracking_api.route("/api/v1/tracking/environment-records", methods=["POST"])
def create_environment_record():
    """Create a new environment telemetry record.

    Validates device identity through the ``X-API-Key`` header and the
    ``device_id`` field in the request body before delegating to the
    application service to apply domain rules, persist the record and
    compute updated averages.

    Request headers:
        X-API-Key: API key paired with the device.
        Content-Type: Must be ``application/json``.

    Request body:
        ``device_id`` (str): Identifier of the submitting device.
        ``temperature`` (float): Temperature reading expressed in degrees
        Celsius.
        ``humidity`` (float): Relative humidity reading expressed as a
        percentage.
        ``created_at`` (str, optional): ISO 8601 timestamp. Defaults to the
        current UTC time when omitted.

    Responses:
        200 OK: Record saved successfully. Body contains the persisted
        record with its assigned ``id``, UTC ``created_at`` and computed
        average temperature and humidity values.
        400 Bad Request: A required field is missing or a value is invalid.
        401 Unauthorized: ``device_id`` or ``X-API-Key`` is absent or invalid.

    Returns:
        tuple[flask.Response, int]: JSON response body paired with the
        appropriate HTTP status code.
    """
    auth_result = authenticate_request()
    if auth_result:
        return auth_result

    data = request.json
    try:
        device_id = data["device_id"]
        temperature = data["temperature"]
        humidity = data["humidity"]
        created_at = data.get("created_at")
        record, averages = environment_record_service.create_environment_record(
            device_id,
            temperature,
            humidity,
            created_at,
        )
        return jsonify({
            "id": record.id,
            "device_id": record.device_id,
            "temperature": record.temperature,
            "humidity": record.humidity,
            "temperature_is_anomaly": record.temperature_is_anomaly,
            "humidity_is_anomaly": record.humidity_is_anomaly,
            "created_at": record.created_at.isoformat(),
            "average_temperature": averages["average_temperature"],
            "average_humidity": averages["average_humidity"],
        }), 200
    except KeyError:
        return jsonify({"error": "Missing required fields"}), 400
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
