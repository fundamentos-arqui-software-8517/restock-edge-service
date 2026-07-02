from devices.domain.entities import DeviceThreshold


class DeviceThresholdService:
    """
    Domain service responsible for the creation of valid device threshold entities.
    """

    @classmethod
    def create_threshold_for_device(cls,
                         device_id: str,
                         assigned_batch_id: str,
                         custom_supply_unit_measurement: str | None,
                         minimum_humidity_percentage: float,
                         maximum_humidity_percentage: float,
                         minimum_temperature_in_celsius: float,
                         maximum_temperature_in_celsius: float,
                         threshold_id: int = 0,
                         custom_supply_weight: float = 1.0,
                         ) -> DeviceThreshold:
        """
        Method to create a DeviceThreshold entity with validated data.

        :param threshold_id: The id of the device threshold
        :param device_id: The device id of the device
        :param assigned_batch_id: The assigned batch id of the device
        :param custom_supply_weight: The custom supply weight of the device
        :param custom_supply_unit_measurement: The unit measurement of the device
        :param minimum_humidity_percentage: The minimum humidity percentage of the device
        :param maximum_humidity_percentage: The maximum humidity percentage of the device
        :param minimum_temperature_in_celsius: The minimum temperature in Celsius
        :param maximum_temperature_in_celsius: The maximum temperature in Celsius

        :return: A DeviceThreshold entity
        """
        try:
            parsed_custom_supply_unit_measurement = (
                str(custom_supply_unit_measurement)
                if custom_supply_unit_measurement is not None
                else None
            )

            parsed_custom_supply_weight = (
                float(custom_supply_weight)
                if custom_supply_weight is not None
                else None
            )

            parsed_assigned_batch_id = str(assigned_batch_id)
            parsed_minimum_humidity_percentage = float(minimum_humidity_percentage)
            parsed_maximum_humidity_percentage = float(maximum_humidity_percentage)
            parsed_minimum_temperature_in_celsius = float(minimum_temperature_in_celsius)
            parsed_maximum_temperature_in_celsius = float(maximum_temperature_in_celsius)
        except (ValueError, TypeError):
            raise ValueError("Invalid data format")

        return DeviceThreshold(
            threshold_id=threshold_id,
            device_id=device_id,
            assigned_batch_id=parsed_assigned_batch_id,
            custom_supply_weight=parsed_custom_supply_weight,
            custom_supply_unit_measurement=parsed_custom_supply_unit_measurement,
            minimum_humidity_percentage=parsed_minimum_humidity_percentage,
            maximum_humidity_percentage=parsed_maximum_humidity_percentage,
            minimum_temperature_in_celsius=parsed_minimum_temperature_in_celsius,
            maximum_temperature_in_celsius=parsed_maximum_temperature_in_celsius,
        )
