"""Application services for the IAM bounded context.

Application services orchestrate use-cases by coordinating domain objects and
repositories.  They contain no domain logic themselves; all business rules live
in the domain layer.
"""
from typing import Optional

from iam.domain.entities import Device
from iam.domain.services import AuthService, DeviceStatus
from iam.infrastructure.repositories import DeviceRepository


class AuthApplicationService:
    """Application service that orchestrates device-authentication use-cases.

    Coordinates the :class:`~iam.infrastructure.repositories.DeviceRepository`
    for reading device credentials and the
    :class:`~iam.domain.services.AuthService` for applying the authentication
    business rule.
    """

    def __init__(self):
        """Initialize the service with its required collaborators."""
        self.device_repository = DeviceRepository()
        self.auth_service = AuthService()

    def authenticate(self, device_id: str, api_key: str) -> bool:
        """Authenticate a device by its ID and cloud-generated token.

        Looks up the device in the repository using the supplied credentials.
        The domain service then evaluates whether the result constitutes a
        successful authentication.

        Args:
            device_id (str): MAC-address identifier of the device.
            api_key (str): Secret token paired with the device, typically
                provided in the ``X-API-Key`` request header.

        Returns:
            bool: ``True`` if a device with the given ``device_id`` and
            ``api_key`` exists in the repository; otherwise ``False``.
        """
        device: Optional[Device] = self.device_repository.find_by_id_and_api_key(
            device_id, api_key
        )
        return self.auth_service.authenticate(device)

    def device_exists(self, device_id: str) -> bool:
        """Check whether a device exists by its MAC-address device id."""
        return self.device_repository.find_by_id(device_id) is not None

    def get_or_create_test_device(self) -> Device:
        """Retrieve the default test device, creating it if it does not exist.

        Intended for development and local testing only.  Delegates to the
        repository to perform an idempotent ``get_or_create`` operation against
        the ``devices`` table.

        Returns:
            Device: Domain entity for the pre-configured test device.
        """
        return self.device_repository.get_or_create_test_device()

    def register_device(self, device_token: str, device_id: str) -> tuple[Device, bool]:
        """Register a new device with its MAC-address id and cloud token.

        ``device_id`` stores the MAC address supplied by the device;
        ``device_token`` is supplied by cloud.

        Idempotent: if a device with the given device id already exists, it is
        returned unchanged.

        Args:
            device_token (str): Cloud-generated token assigned to the device.
            device_id (str): MAC address used as the public device id.

        Returns:
            tuple[Device, bool]: The device entity, and ``True`` if it was
            newly created or ``False`` if it already existed.
        """
        return self.device_repository.create_or_get(device_token, device_id)

    def mark_device_configured(self, device_id: str) -> Device:
        """Move a device to CONFIGURED after batch and thresholds are assigned."""
        device = self.device_repository.update_status(device_id, DeviceStatus.CONFIGURED)
        if device is None:
            raise ValueError("Device not found")
        return device

    def mark_device_calibrated(self, device_id: str) -> Device:
        """Move a device to CALIBRATED so embedded communication is allowed."""
        device = self.device_repository.update_status(device_id, DeviceStatus.CALIBRATED)
        if device is None:
            raise ValueError("Device not found")
        return device
