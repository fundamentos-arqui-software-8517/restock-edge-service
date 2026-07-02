from peewee import Model, AutoField, CharField, FloatField

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

    class Meta:
        """ Peewee metadata that binds the model to the shared database. """

        database = db
        db_table = 'device_thresholds'
