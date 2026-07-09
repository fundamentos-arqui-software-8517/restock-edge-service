from datetime import datetime, timezone

from peewee import AutoField, BooleanField, CharField, DateTimeField, FloatField, Model, TextField

from shared.infrastructure.database import db


class DeviceThresholdModel(Model):
    """
    ORM mapping for the ``device_thresholds`` table.

    Attributes:
        threshold_id (AutoField): Auto-incrementing integer primary key assigned by the database on insert
        device_id (str): The unique id of the device
        assigned_batch_id (str): The id of the batch assigned to the device
        custom_supply_unit_measurement (str | None): The custom supply unit measurement of the device
        minimum_humidity_percentage (float): The minimum humidity percentage of the device
        maximum_humidity_percentage (float): The maximum humidity percentage of the device
        minimum_temperature_in_celsius (float): The minimum temperature in Celsius of the device
        maximum_temperature_in_celsius (float): The maximum temperature in Celsius of the device
    """

    threshold_id = AutoField(primary_key=True)
    device_id = CharField(unique=True, null=False)
    assigned_batch_id = CharField(null=False)
    custom_supply_weight = FloatField(null=True)
    custom_supply_unit_measurement = CharField(null=True)
    minimum_humidity_percentage = FloatField(null=False)
    maximum_humidity_percentage = FloatField(null=False)
    minimum_temperature_in_celsius = FloatField(null=False)
    maximum_temperature_in_celsius = FloatField(null=False)
    anomaly_threshold = FloatField(null=True)

    class Meta:
        """ Peewee metadata that binds the model to the shared database. """

        database = db
        db_table = 'device_thresholds'


class DeviceStatusReportModel(Model):
    """
    ORM mapping for the ``device_status_reports`` table.

    Stores normalized device health snapshots received through HTTP or MQTT,
    including the evaluated ``health_status`` without reusing IAM lifecycle
    status.
    """

    id = AutoField()
    device_id = CharField(null=False)
    branch_id = CharField(null=True)
    cpu_usage_percentage = FloatField(null=True)
    free_heap_bytes = FloatField(null=True)
    internal_temperature_celsius = FloatField(null=True)
    voltage = FloatField(null=True)
    uptime_ms = FloatField(null=True)
    system_status = CharField(null=True)
    alert_type = CharField(null=True)
    metric = CharField(null=True)
    value = FloatField(null=True)
    threshold = FloatField(null=True)
    message = TextField(null=True)
    health_status = CharField(null=False)
    critical = BooleanField(default=False)
    source = CharField(null=False, default="HTTP")
    created_at = DateTimeField(null=False, default=lambda: datetime.now(timezone.utc))

    class Meta:
        """ Peewee metadata that binds the model to the shared database. """

        database = db
        table_name = "device_status_reports"


class DeviceHealthEventModel(Model):
    """
    ORM mapping for the ``device_health_events`` table.

    Stores critical and informational health events derived from status reports.
    """

    id = AutoField()
    device_id = CharField(null=False)
    branch_id = CharField(null=True)
    event_type = CharField(null=False)
    health_status = CharField(null=False)
    metric = CharField(null=True)
    value = FloatField(null=True)
    threshold = FloatField(null=True)
    reason = TextField(null=False)
    message = TextField(null=True)
    source = CharField(null=False, default="HTTP")
    created_at = DateTimeField(null=False, default=lambda: datetime.now(timezone.utc))

    class Meta:
        """ Peewee metadata that binds the model to the shared database. """

        database = db
        table_name = "device_health_events"
