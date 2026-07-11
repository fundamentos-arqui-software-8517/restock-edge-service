import logging
import os
import requests

from dotenv import load_dotenv

from devices.domain.entities import DeviceThreshold
from tracking.domain.entities import WeightRecord, EnvironmentRecord

# Load environment variables from .env file
load_dotenv()


class TelemetrySyncClient:
    """ A client for syncing telemetry data to a cloud API."""

    def __init__(self):
        """ Initialize the TelemetrySyncClient with the cloud API base URL and telemetry API URL from environment variables. """
        self.api_base_url = os.getenv('CLOUD_API_BASE_URL')
        self.telemetry_api_url = os.getenv('CLOUD_TELEMETRY_URL')
        self.api_token = os.getenv('CLOUD_API_TOKEN')

    def sync(
            self,
            threshold: DeviceThreshold,
            weight_telemetry: WeightRecord,
            environment_telemetry: EnvironmentRecord
    ) -> None:
        """ Sync telemetry data to the cloud API.

        :param threshold: The device threshold entity.
        :param environment_telemetry: The environment telemetry record to be synced.
        :param weight_telemetry: The weight telemetry record to be synced.
        :exception ValueError: If the telemetry data is invalid.
        :exception requests.RequestException: If there is an error during the HTTP request.
        """

        try:
            payload: dict = self._to_payload(threshold, weight_telemetry, environment_telemetry)
        except (ValueError, TypeError, AttributeError) as e:
            logging.error("Invalid telemetry sync payload: %s", e)
            return
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        try:
            response = requests.post(self.telemetry_api_url, json=payload, headers=headers)
        except requests.RequestException as e:
            logging.error("Error syncing telemetry: %s", e)
            return

        if response.status_code == 200:
            logging.info("Telemetry synced successfully for device %s", payload["deviceId"])
            return

        logging.warning(
            "Failed to sync telemetry for device %s. Status code: %s, Response: %s",
            payload["deviceId"],
            response.status_code,
            response.text
        )

        return

    @staticmethod
    def _to_payload(
            threshold: DeviceThreshold,
            weight_telemetry: WeightRecord,
            environment_telemetry: EnvironmentRecord
    ) -> dict:
        """Convert a TelemetryRecord to a payload for the telemetry API."""

        try:
            payload_physical_stock = float(weight_telemetry.physical_stock)
            if payload_physical_stock < 0:
                raise ValueError("Physical stock must be a positive number")

            payload_temperature_in_celsius = float(environment_telemetry.temperature)
            if payload_temperature_in_celsius < -273.15 or payload_temperature_in_celsius > 100:
                raise ValueError("Temperature must be a valid temperature in Celsius")

            payload_humidity_percentage = float(environment_telemetry.humidity)
            if payload_humidity_percentage < 0 or payload_humidity_percentage > 100:
                raise ValueError("Humidity must be a valid percentage")

            payload_assigned_batch_id = str(threshold.assigned_batch_id)

            payload_device_id = str(threshold.device_id)

            payload_timestamp = weight_telemetry.created_at.isoformat(timespec='milliseconds')
            if not payload_timestamp:
                raise ValueError("Timestamp is required")

        except (ValueError, TypeError, AttributeError):
            raise ValueError("Invalid data format")

        payload = {
            "physicalStock": payload_physical_stock,
            "temperatureInCelsius": payload_temperature_in_celsius,
            "humidityPercentage": payload_humidity_percentage,
            "assignedBatchId": payload_assigned_batch_id,
            "deviceId": payload_device_id,
            "timestamp": payload_timestamp,
        }

        return payload

# Singleton instance of the TelemetrySyncClient
telemetry_sync_client = TelemetrySyncClient()
