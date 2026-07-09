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
                 anomaly_threshold: float | None = None,
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
        self.anomaly_threshold = anomaly_threshold


class DeviceStatusReport:
    """
    Status report entity for device health telemetry.

    Attributes:
        id (int | None): The unique id of the status report, if applicable
        device_id (str): The unique id of the device
        branch_id (str | None): The branch associated with the device
        health_status (str): The evaluated health status of the device
        critical (bool): Whether the report contains a critical condition
        source (str): Input channel that produced the report, such as HTTP or MQTT
        created_at (datetime): Timestamp when the status was captured or registered
    """
    def __init__(
            self,
            device_id: str,
            health_status: str,
            critical: bool,
            source: str,
            created_at,
            id: int | None = None,
            branch_id: str | None = None,
            cpu_usage_percentage: float | None = None,
            free_heap_bytes: float | None = None,
            internal_temperature_celsius: float | None = None,
            voltage: float | None = None,
            uptime_ms: float | None = None,
            system_status: str | None = None,
            alert_type: str | None = None,
            metric: str | None = None,
            value: float | None = None,
            threshold: float | None = None,
            message: str | None = None,
    ):
        self.id = id
        self.device_id = device_id
        self.branch_id = branch_id
        self.cpu_usage_percentage = cpu_usage_percentage
        self.free_heap_bytes = free_heap_bytes
        self.internal_temperature_celsius = internal_temperature_celsius
        self.voltage = voltage
        self.uptime_ms = uptime_ms
        self.system_status = system_status
        self.alert_type = alert_type
        self.metric = metric
        self.value = value
        self.threshold = threshold
        self.message = message
        self.health_status = health_status
        self.critical = critical
        self.source = source
        self.created_at = created_at


class DeviceHealthEvent:
    """
    Health event entity raised when a status report requires attention.

    Attributes:
        id (int | None): The unique id of the health event, if applicable
        device_id (str): The unique id of the device
        event_type (str): Type of event registered, such as ERROR or INFO
        health_status (str): Health status that caused the event
        reason (str): Human-readable reason for the event
        source (str): Input channel that produced the event, such as HTTP or MQTT
        created_at (datetime): Timestamp when the event was captured or registered
    """
    def __init__(
            self,
            device_id: str,
            event_type: str,
            health_status: str,
            reason: str,
            source: str,
            created_at,
            id: int | None = None,
            branch_id: str | None = None,
            metric: str | None = None,
            value: float | None = None,
            threshold: float | None = None,
            message: str | None = None,
    ):
        self.id = id
        self.device_id = device_id
        self.branch_id = branch_id
        self.event_type = event_type
        self.health_status = health_status
        self.metric = metric
        self.value = value
        self.threshold = threshold
        self.reason = reason
        self.message = message
        self.source = source
        self.created_at = created_at
