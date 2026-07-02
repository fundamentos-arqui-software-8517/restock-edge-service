from devices.domain.entities import DeviceThreshold
from devices.infrastructure.models import DeviceThresholdModel


class DeviceThresholdRepository:
    """
    Repository for DeviceThreshold entities.
    This repository is responsible for storing DeviceThreshold entities.
    """

    @staticmethod
    def save(device_threshold: DeviceThreshold) -> DeviceThreshold:
        """
        Persists a DeviceThreshold entity to the database.

        :param device_threshold: The DeviceThreshold entity to persist
        :return: A DeviceThreshold entity corresponding to the given device_threshold.
        """

        record = DeviceThresholdModel.create(
            device_id = device_threshold.device_id,
            assigned_batch_id = device_threshold.assigned_batch_id,
            custom_supply_weight = device_threshold.custom_supply_weight,
            custom_supply_unit_measurement = device_threshold.custom_supply_unit_measurement,
            minimum_humidity_percentage = device_threshold.minimum_humidity_percentage,
            maximum_humidity_percentage = device_threshold.maximum_humidity_percentage,
            minimum_temperature_in_celsius = device_threshold.minimum_temperature_in_celsius,
            maximum_temperature_in_celsius = device_threshold.maximum_temperature_in_celsius,
        )

        return DeviceThreshold(
            threshold_id = record.threshold_id,
            device_id = record.device_id,
            assigned_batch_id = record.assigned_batch_id,
            custom_supply_weight = record.custom_supply_weight,
            custom_supply_unit_measurement = record.custom_supply_unit_measurement,
            minimum_humidity_percentage = record.minimum_humidity_percentage,
            maximum_humidity_percentage = record.maximum_humidity_percentage,
            minimum_temperature_in_celsius = record.minimum_temperature_in_celsius,
            maximum_temperature_in_celsius = record.maximum_temperature_in_celsius,
        )

    @staticmethod
    def update(device_threshold: DeviceThreshold) -> DeviceThreshold:
        """
        Updates a DeviceThreshold entity in the database.
        It can be used to update the configuration of the threshold and to assign the threshold to a new batch for the device.

        :param device_threshold: The DeviceThreshold entity to update
        :return: A DeviceThreshold entity corresponding to the given device_threshold.
        """

        DeviceThresholdModel.update(
            assigned_batch_id = device_threshold.assigned_batch_id,
            custom_supply_unit_measurement = device_threshold.custom_supply_unit_measurement,
            minimum_humidity_percentage = device_threshold.minimum_humidity_percentage,
            maximum_humidity_percentage = device_threshold.maximum_humidity_percentage,
            minimum_temperature_in_celsius = device_threshold.minimum_temperature_in_celsius,
            maximum_temperature_in_celsius = device_threshold.maximum_temperature_in_celsius,
        ).where(DeviceThresholdModel.device_id == device_threshold.device_id).execute()
        record = DeviceThresholdModel.get(device_id=device_threshold.device_id)

        return DeviceThreshold(
            threshold_id = record.threshold_id,
            device_id = record.device_id,
            assigned_batch_id = record.assigned_batch_id,
            custom_supply_weight = record.custom_supply_weight,
            custom_supply_unit_measurement = record.custom_supply_unit_measurement,
            minimum_humidity_percentage = record.minimum_humidity_percentage,
            maximum_humidity_percentage = record.maximum_humidity_percentage,
            minimum_temperature_in_celsius = record.minimum_temperature_in_celsius,
            maximum_temperature_in_celsius = record.maximum_temperature_in_celsius,
        )

    @staticmethod
    def calibrate_custom_supply_weight(device_id: str, custom_supply_weight: float) -> DeviceThreshold:
        """
        Updates the custom_supply_weight of a DeviceThreshold entity in the database.

        :param device_id: The device id of the device to update
        :param custom_supply_weight: The new custom supply weight to set for the device
        :return: A DeviceThreshold entity corresponding to the given device_id with the updated custom_supply_weight.
        """

        DeviceThresholdModel.update(
            custom_supply_weight = custom_supply_weight,
        ).where(DeviceThresholdModel.device_id == device_id).execute()

        record = DeviceThresholdModel.get(device_id=device_id)

        return DeviceThreshold(
            threshold_id = record.threshold_id,
            device_id = record.device_id,
            assigned_batch_id = record.assigned_batch_id,
            custom_supply_weight = record.custom_supply_weight,
            custom_supply_unit_measurement = record.custom_supply_unit_measurement,
            minimum_humidity_percentage = record.minimum_humidity_percentage,
            maximum_humidity_percentage = record.maximum_humidity_percentage,
            minimum_temperature_in_celsius = record.minimum_temperature_in_celsius,
            maximum_temperature_in_celsius = record.maximum_temperature_in_celsius,
        )

    @staticmethod
    def get_by_device_id(device_id: str) -> DeviceThreshold:
        """
        Retrieves a DeviceThreshold entity from the database by device_id.

        :param device_id: The device id of the device to retrieve
        :return: A DeviceThreshold entity corresponding to the given device_id.
        """

        record = DeviceThresholdModel.get(device_id=device_id)

        return DeviceThreshold(
            threshold_id = record.threshold_id,
            device_id = record.device_id,
            assigned_batch_id = record.assigned_batch_id,
            custom_supply_weight = record.custom_supply_weight,
            custom_supply_unit_measurement = record.custom_supply_unit_measurement,
            minimum_humidity_percentage = record.minimum_humidity_percentage,
            maximum_humidity_percentage = record.maximum_humidity_percentage,
            minimum_temperature_in_celsius = record.minimum_temperature_in_celsius,
            maximum_temperature_in_celsius = record.maximum_temperature_in_celsius,
        )
