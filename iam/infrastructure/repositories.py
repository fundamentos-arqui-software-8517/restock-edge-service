"""Repository implementation for the IAM bounded context.

Provides the persistence adapter that maps between the
:class:`~iam.domain.entities.Device` domain entity and the
:class:`~iam.infrastructure.models.Device` Peewee ORM model.

Following the Repository pattern, callers in the application layer work only
with domain entities and remain isolated from ORM and database details.
"""
from datetime import datetime, timezone
from typing import Optional

import peewee

from iam.domain.entities import Device
from iam.domain.services import DeviceStatus
from iam.infrastructure.models import Device as DeviceModel


class DeviceRepository:
    """Repository that persists and reconstructs Device entities.

    Implements the collection-like interface expected by application services.
    All ORM-to-entity mapping is contained within this class, ensuring the
    domain layer has no dependency on Peewee.
    """

    @staticmethod
    def find_by_id(device_id: str) -> Optional[Device]:
        """Look up a device by its MAC-address public identifier."""
        try:
            device = DeviceModel.get(DeviceModel.device_id == device_id)
            return Device(
                device.device_id,
                device.device_token,
                device.status,
                device.created_at,
            )
        except peewee.DoesNotExist:
            return None

    @staticmethod
    def find_by_id_and_api_key(device_id: str, api_key: str) -> Optional[Device]:
        """Look up a device by its identifier and token.

        Queries the ``devices`` table for a row matching both ``device_id`` and
        ``device_token``.  Returning ``None`` when no match is found lets the
        domain service apply the authentication rule without catching
        infrastructure exceptions.

        Args:
            device_id (str): Identifier of the device to search for.
            api_key (str): Token that must match the stored credential.

        Returns:
            Optional[Device]: Matching domain entity if the credentials exist;
            otherwise ``None``.
        """
        try:
            device = DeviceModel.get(
                (DeviceModel.device_id == device_id) & (DeviceModel.device_token == api_key)
            )
            return Device(
                device.device_id,
                device.device_token,
                device.status,
                device.created_at,
            )
        except peewee.DoesNotExist:
            return None

    @staticmethod
    def get_or_create_test_device() -> Device:
        """Retrieve the default Restock test device, creating it if absent.

        Performs an idempotent ``get_or_create`` against the ``devices`` table.
        The default credentials are intended for local development and testing
        only.  They must not be reused in production or on real deployed edge
        devices.

        Returns:
            Device: Domain entity for the local development test device.
        """
        device, _ = DeviceModel.get_or_create(
            device_id="00:00:00:00:00:00",
            defaults={
                "device_token": "test-api-key-123",
                "status": DeviceStatus.CALIBRATED,
                "created_at": datetime.now(timezone.utc),
            },
        )
        return Device(
            device.device_id,
            device.device_token,
            device.status,
            device.created_at,
        )

    @staticmethod
    def create_or_get(device_token: str, device_id: str) -> tuple[Device, bool]:
        """Create a device for the given MAC-address id and token.

        ``device_id`` stores the MAC address used by the device API, and
        ``device_token`` is assigned by cloud.

        Args:
            device_token (str): Cloud-generated token paired with the device.
            device_id (str): MAC address used as the public device id.

        Returns:
            tuple[Device, bool]: The domain entity, and ``True`` if it was
            newly created, ``False`` if it already existed.
        """
        device, created = DeviceModel.get_or_create(
            device_id=device_id,
            defaults={
                "device_token": device_token,
                "status": DeviceStatus.REGISTERED,
                "created_at": datetime.now(timezone.utc),
            },
        )
        if device.device_token != device_token:
            device.device_token = device_token
            device.save()
        return Device(
            device.device_id,
            device.device_token,
            device.status,
            device.created_at,
        ), created

    @staticmethod
    def update_status(device_id: str, status: str) -> Optional[Device]:
        """Update the lifecycle status for a registered device."""
        try:
            device = DeviceModel.get(DeviceModel.device_id == device_id)
            device.status = status
            device.save()
            return Device(
                device.device_id,
                device.device_token,
                device.status,
                device.created_at,
            )
        except peewee.DoesNotExist:
            return None
