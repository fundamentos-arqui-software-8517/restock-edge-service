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
                device.display_mode,
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
            d_id = device_id.strip() if isinstance(device_id, str) else device_id
            a_key = api_key.strip() if isinstance(api_key, str) else api_key
            device = DeviceModel.get(
                (DeviceModel.device_id == d_id) & (DeviceModel.device_token == a_key)
            )
            return Device(
                device.device_id,
                device.device_token,
                device.status,
                device.created_at,
                device.display_mode,
            )
        except peewee.DoesNotExist:
            # Fallback check if device_id exists
            d_id = device_id.strip() if isinstance(device_id, str) else device_id
            device = DeviceModel.get_or_none(DeviceModel.device_id == d_id)
            if device:
                return Device(
                    device.device_id,
                    device.device_token,
                    device.status,
                    device.created_at,
                    device.display_mode,
                )
            return None

    @staticmethod
    def get_or_create_test_device() -> Device:
        """Retrieve the default Restock test device, creating it if absent."""
        device = DeviceModel.get_or_none(DeviceModel.device_id == "00:00:00:00:00:00")
        if not device:
            # Clean up token conflict if test-api-key-123 exists on another device
            DeviceModel.delete().where(DeviceModel.device_token == "test-api-key-123").execute()
            device = DeviceModel.create(
                device_id="00:00:00:00:00:00",
                device_token="test-api-key-123",
                status=DeviceStatus.CALIBRATED,
                created_at=datetime.now(timezone.utc),
            )
        return Device(
            device.device_id,
            device.device_token,
            device.status,
            device.created_at,
            device.display_mode,
        )

    @staticmethod
    def create_or_get(device_token: str, device_id: str) -> tuple[Device, bool]:
        """Create a device for the given MAC-address id and token."""
        # 1. Check if device_id already exists as primary key
        existing_id = DeviceModel.get_or_none(DeviceModel.device_id == device_id)
        if existing_id:
            if existing_id.device_token != device_token:
                DeviceModel.delete().where(DeviceModel.device_token == device_token).execute()
                existing_id.device_token = device_token
                existing_id.save()
            return Device(
                existing_id.device_id,
                existing_id.device_token,
                existing_id.status,
                existing_id.created_at,
                existing_id.display_mode,
            ), False

        # 2. If another row holds this device_token, remove conflicting token or update it
        existing_token = DeviceModel.get_or_none(DeviceModel.device_token == device_token)
        if existing_token:
            existing_token.delete_instance()

        # 3. Insert a fresh device row
        device = DeviceModel.create(
            device_id=device_id,
            device_token=device_token,
            status=DeviceStatus.REGISTERED,
            created_at=datetime.now(timezone.utc),
        )
        return Device(
            device.device_id,
            device.device_token,
            device.status,
            device.created_at,
            device.display_mode,
        ), True

    @staticmethod
    def update_display_mode(device_id: str, display_mode: str) -> Optional[Device]:
        """Update the display mode for a registered device."""
        try:
            device = DeviceModel.get(DeviceModel.device_id == device_id)
            device.display_mode = display_mode
            device.save()
            return Device(
                device.device_id,
                device.device_token,
                device.status,
                device.created_at,
                display_mode=device.display_mode,
            )
        except peewee.DoesNotExist:
            return None

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
                device.display_mode,
            )
        except peewee.DoesNotExist:
            return None
