class DeviceThreshold:
    """
    Threshold entity for a device, representing the acceptable ranges for humidity and temperature, as well as custom supply unit measurement.

    Attributes:
        threshold_id (int | None): The unique id of the threshold record, if applicable
        device_id (str): The unique id of the device
        assigned_batch_id (str): The id of the batch assigned to the device
        custom_supply_weight (float | None): The weight of the custom supply, if applicable
        custom_supply_unit_measurement (str | None): The unit of measurement for the custom supply
        minimum_humidity_percentage (float): The minimum acceptable humidity percentage for the device
        maximum_humidity_percentage (float): The maximum acceptable humidity percentage for the device
        minimum_temperature_in_celsius (float): The minimum acceptable temperature in Celsius for the device
        maximum_temperature_in_celsius (float): The maximum acceptable temperature in Celsius for the device
    """
    def __init__(self,
                 threshold_id: int | None,
                 device_id: str,
                 assigned_batch_id: str,
                 custom_supply_weight: float | None,
                 custom_supply_unit_measurement: str | None,
                 minimum_humidity_percentage: float,
                 maximum_humidity_percentage: float,
                 minimum_temperature_in_celsius: float,
                 maximum_temperature_in_celsius: float,
                 ):
        self.threshold_id = threshold_id
        self.device_id = device_id
        self.assigned_batch_id = assigned_batch_id
        self.custom_supply_weight = custom_supply_weight
        self.custom_supply_unit_measurement = custom_supply_unit_measurement
        self.minimum_humidity_percentage = minimum_humidity_percentage
        self.maximum_humidity_percentage = maximum_humidity_percentage
        self.minimum_temperature_in_celsius = minimum_temperature_in_celsius
        self.maximum_temperature_in_celsius = maximum_temperature_in_celsius
