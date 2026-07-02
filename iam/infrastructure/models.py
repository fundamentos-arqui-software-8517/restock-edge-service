"""Peewee ORM model for the IAM bounded context.

Defines the ``devices`` database table used to persist
:class:`~iam.domain.entities.Device` aggregate roots.  This module belongs to
the infrastructure layer; it must not be imported directly by the domain or
application layers.  Access is mediated through the repository.
"""
from peewee import CharField, DateTimeField, Model

from shared.infrastructure.database import db


class Device(Model):
    """ORM mapping for the ``devices`` table.

    Each row represents a registered Restock IoT device and the token assigned
    by cloud.

    Attributes:
        device_id (CharField): Device MAC address used as the primary key.
        device_token (CharField): Secret token paired with the device and
            checked on authenticated API calls.
        status (CharField): Device lifecycle status.
        created_at (DateTimeField): UTC timestamp recording when the device was
            registered in the local edge database.
    """

    device_id = CharField(primary_key=True)
    device_token = CharField(unique=True)
    status = CharField(default="REGISTERED")
    created_at = DateTimeField()

    class Meta:
        """Peewee metadata that binds the model to the shared database."""

        database = db
        table_name = "devices"
