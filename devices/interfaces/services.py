"""
Interface layer for the Devices bounded context.

Exposes a Flask Blueprint (``devices_api``) that translates incoming HTTP
requests into calls to the application service and maps the results back to
JSON responses.  This layer owns no domain logic; it is responsible for I/O
concerns such as request parsing, authentication delegation, and HTTP status
code selection.
"""
from flask import Blueprint, jsonify, request

from devices.application.services import DeviceStatusApplicationService
from devices.application.services import DeviceThresholdApplicationService
from devices.domain.services import DeviceStatusSemanticError
from iam.application.services import AuthApplicationService
from iam.interfaces.services import authenticate_request

# This module defines the Flask Blueprint for device-related API endpoints and initializes
devices_api = Blueprint("devices_api", __name__)

# Module-level singleton; it contains no request-specific mutable state.
device_threshold_service = DeviceThresholdApplicationService()
device_status_service = DeviceStatusApplicationService()
auth_application_service = AuthApplicationService()


@devices_api.route("/api/v1/devices/status", methods=["POST"])
def register_device_status():
    """
    Fallback endpoint to register a device health status report.

    MQTT is the real source of device health telemetry. This endpoint exists
    for Postman/Swagger/manual testing and accepts the same event-style JSON
    published by embedded before delegating to DeviceStatusApplicationService.
    """
    auth_result = authenticate_request()
    if auth_result:
        return auth_result

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    try:
        result = device_status_service.register_status(data, source="HTTP")
        report = result["report"]

        return jsonify({
            "device_id": report.device_id,
            "health_status": result["health_status"],
            "critical": result["critical"],
            "event_registered": result["event_registered"],
            "metric": result["metric"],
            "reason": result["reason"],
        }), 201
    except KeyError:
        return jsonify({"error": "Missing required fields"}), 400
    except DeviceStatusSemanticError as error:
        return jsonify({"error": str(error)}), 422
    except LookupError as error:
        return jsonify({"error": str(error)}), 404
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

@devices_api.route("/api/v1/devices/<device_id>/thresholds", methods=["POST"])
def create_threshold_for_device(device_id: str):
    """
    Endpoint to create a new device threshold.

    :param device_id: The id of the device.

    :return: JSON response with a success message and HTTP status code.
    :except: KeyError if required fields are missing or ValueError if invalid data is provided.
    """

    data = request.json

    try:
        assigned_batch_id = data["assigned_batch_id"]
        custom_supply_unit_measurement = data.get("custom_supply_unit_measurement")
        custom_supply_weight = data.get("custom_supply_weight")
        anomaly_threshold = data.get("anomaly_threshold")
        minimum_humidity_percentage = data["minimum_humidity_percentage"]
        maximum_humidity_percentage = data["maximum_humidity_percentage"]
        minimum_temperature_in_celsius = data["minimum_temperature_in_celsius"]
        maximum_temperature_in_celsius = data["maximum_temperature_in_celsius"]

        record = device_threshold_service.create_device_threshold(
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
        auth_application_service.mark_device_configured(device_id)

        return jsonify({
            "success": "Threshold registered successfully in edge service for device: " + record.device_id + ""
        }), 201

    except KeyError:
        return jsonify({"error": "Missing required fields"}), 400
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

@devices_api.route("/api/v1/devices/<device_id>/thresholds", methods=["PUT"])
def update_threshold_for_device(device_id: str):
    """
    Endpoint to update an existing device threshold or to assign a new batch to a device.

    :param device_id: The id of the device.
    :return: JSON response with a success message and HTTP status code.
    """

    data = request.json

    try:
        assigned_batch_id = data["assigned_batch_id"]
        custom_supply_unit_measurement = data.get("custom_supply_unit_measurement")
        custom_supply_weight = data.get("custom_supply_weight")
        anomaly_threshold = data.get("anomaly_threshold")
        minimum_humidity_percentage = data["minimum_humidity_percentage"]
        maximum_humidity_percentage = data["maximum_humidity_percentage"]
        minimum_temperature_in_celsius = data["minimum_temperature_in_celsius"]
        maximum_temperature_in_celsius = data["maximum_temperature_in_celsius"]

        record = device_threshold_service.update_device_threshold(
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
        auth_application_service.mark_device_calibrated(device_id)

        return jsonify({
            "success": "Threshold updated successfully in edge service for device: " + record.device_id + ""
        }), 200

    except KeyError:
        return jsonify({"error": "Missing required fields"}), 400
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
