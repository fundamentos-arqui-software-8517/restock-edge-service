"""Domain services for the IAM bounded context.

Domain services express business behavior that does not fit naturally inside a
single entity.  ``AuthService`` encapsulates the authentication invariant for
Restock IoT devices: a device is considered authenticated when the device
registry returns a matching MAC-address ``device_id`` and ``device_token`` pair
in ``CALIBRATED`` status.
"""
from typing import Optional

from iam.domain.entities import Device, DeviceStatus


class AuthService:
    """Domain service that determines whether a device is authenticated.

    The authentication rule is deliberately simple for this base version: a
    ``Device`` object retrieved from the repository is considered valid.  If no
    device is found, the repository returns ``None`` and authentication fails.
    """

    @staticmethod
    def authenticate(device: Optional[Device]) -> bool:
        """Determine whether the given device is authenticated.

        Args:
            device (Optional[Device]): Device entity returned by the repository,
                or ``None`` when no matching credentials were found.

        Returns:
            bool: ``True`` if ``device`` is not ``None``; otherwise ``False``.
        """
        return device is not None and device.status == DeviceStatus.CALIBRATED
