"""Unit tests for WeightRecordApplicationService and EnvironmentRecordApplicationService.

All collaborators (repositories, domain services) are replaced with mocks so
that these tests remain fast and isolated from the database and HTTP layer.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from tracking.domain.entities import WeightRecord, EnvironmentRecord


# ---------------------------------------------------------------------------
# WeightRecordApplicationService – Unit Tests
# ---------------------------------------------------------------------------

class TestWeightRecordApplicationServiceCreateWeightRecord:
    """UT-ES-06 – WeightRecordApplicationService.create_weight_record"""

    def setup_method(self):
        """Patch all collaborator constructors before each test."""
        self.mock_device_repo = MagicMock()
        self.mock_weight_repo = MagicMock()
        self.mock_threshold_repo = MagicMock()
        self.mock_weight_service = MagicMock()

        # Build service with injected mocks using patch
        with patch("tracking.application.services.DeviceRepository", return_value=self.mock_device_repo), \
             patch("tracking.application.services.WeightRecordRepository", return_value=self.mock_weight_repo), \
             patch("tracking.application.services.DeviceThresholdRepository", return_value=self.mock_threshold_repo), \
             patch("tracking.application.services.WeightRecordService", return_value=self.mock_weight_service):
            from tracking.application.services import WeightRecordApplicationService
            self.service = WeightRecordApplicationService.__new__(WeightRecordApplicationService)
            self.service.device_repository = self.mock_device_repo
            self.service.weight_record_repository = self.mock_weight_repo
            self.service.device_threshold_repository = self.mock_threshold_repo
            self.service.weight_record_service = self.mock_weight_service

    def _make_record(self, physical_stock=2):
        return WeightRecord("device-1", 500.0, physical_stock, datetime.now(timezone.utc), weight_record_id=1)

    def test_raises_value_error_when_device_not_found(self):
        """UT-ES-06a: Device not found → ValueError."""
        self.mock_device_repo.find_by_id.return_value = None

        with pytest.raises(ValueError, match="Device not found"):
            self.service.create_weight_record("device-1", 500.0, None)

    def test_creates_record_successfully(self):
        """UT-ES-06b: Happy path – record is created, saved and averages are returned."""
        self.mock_device_repo.find_by_id.return_value = MagicMock()
        threshold = MagicMock()
        threshold.custom_supply_weight = 250.0
        self.mock_threshold_repo.get_by_device_id.return_value = threshold
        self.mock_weight_service.calculate_physical_stock.return_value = 2
        record = self._make_record()
        self.mock_weight_service.create_record.return_value = record
        self.mock_weight_repo.save.return_value = record
        self.mock_weight_repo.find_by_device_in_interval.return_value = [record]
        self.mock_weight_service.calculate_averages.return_value = {"average_physical_stock": 2.0}

        saved, averages = self.service.create_weight_record("device-1", 500.0, None)

        assert saved == record
        assert averages["average_physical_stock"] == 2.0
        self.mock_weight_repo.save.assert_called_once_with(record)

    def test_persists_record_exactly_once(self):
        """UT-ES-06c: Repository.save is called exactly once."""
        self.mock_device_repo.find_by_id.return_value = MagicMock()
        threshold = MagicMock()
        threshold.custom_supply_weight = 100.0
        self.mock_threshold_repo.get_by_device_id.return_value = threshold
        self.mock_weight_service.calculate_physical_stock.return_value = 5
        record = self._make_record(5)
        self.mock_weight_service.create_record.return_value = record
        self.mock_weight_repo.save.return_value = record
        self.mock_weight_repo.find_by_device_in_interval.return_value = [record]
        self.mock_weight_service.calculate_averages.return_value = {"average_physical_stock": 5.0}

        self.service.create_weight_record("device-1", 500.0, None)
        self.mock_weight_repo.save.assert_called_once()


# ---------------------------------------------------------------------------
# EnvironmentRecordApplicationService – Unit Tests
# ---------------------------------------------------------------------------

class TestEnvironmentRecordApplicationServiceCreateEnvironmentRecord:
    """UT-ES-07 – EnvironmentRecordApplicationService.create_environment_record"""

    def setup_method(self):
        self.mock_device_repo = MagicMock()
        self.mock_env_repo = MagicMock()
        self.mock_threshold_repo = MagicMock()
        self.mock_env_service = MagicMock()

        from tracking.application.services import EnvironmentRecordApplicationService
        self.service = EnvironmentRecordApplicationService.__new__(EnvironmentRecordApplicationService)
        self.service.device_repository = self.mock_device_repo
        self.service.environment_record_repository = self.mock_env_repo
        self.service.device_threshold_repository = self.mock_threshold_repo
        self.service.environment_record_service = self.mock_env_service

    def _make_env_record(self, temp_anomaly=False, hum_anomaly=False):
        record = EnvironmentRecord(
            "device-1", 25.0, 60.0, datetime.now(timezone.utc),
            temperature_is_anomaly=temp_anomaly,
            humidity_is_anomaly=hum_anomaly,
        )
        record.id = 1
        return record

    def test_raises_value_error_when_device_not_found(self):
        """UT-ES-07a: Device not found → ValueError."""
        self.mock_device_repo.find_by_id.return_value = None

        with pytest.raises(ValueError, match="Device not found"):
            self.service.create_environment_record("device-1", 25.0, 60.0, None)

    def test_normal_reading_no_anomaly_flags(self):
        """UT-ES-07b: Temperature and humidity within thresholds → no anomaly flags."""
        self.mock_device_repo.find_by_id.return_value = MagicMock()
        threshold = MagicMock()
        threshold.minimum_temperature_in_celsius = 0.1
        threshold.maximum_temperature_in_celsius = 90.1
        threshold.minimum_humidity_percentage = 0.1
        threshold.maximum_humidity_percentage = 90.1
        threshold.assigned_batch_id = "batch-1"
        self.mock_threshold_repo.get_by_device_id.return_value = threshold

        record = self._make_env_record()
        self.mock_env_service.create_record.return_value = record
        self.mock_env_repo.save.return_value = record
        self.mock_env_repo.find_by_device_in_interval.return_value = [record]
        self.mock_env_service.calculate_averages.return_value = {
            "average_temperature": 25.0, "average_humidity": 60.0
        }

        with patch.object(self.service, "_send_environment_telemetry_to_cloud"):
            saved, averages = self.service.create_environment_record("device-1", 25.0, 60.0, None)

        assert saved == record
        assert averages["average_temperature"] == 25.0

    def test_anomalous_temperature_flags_anomaly(self):
        """UT-ES-07c: Temperature outside threshold → temperature_is_anomaly=True."""
        self.mock_device_repo.find_by_id.return_value = MagicMock()
        threshold = MagicMock()
        threshold.minimum_temperature_in_celsius = 0.1
        threshold.maximum_temperature_in_celsius = 30.0
        threshold.minimum_humidity_percentage = 0.1
        threshold.maximum_humidity_percentage = 90.1
        threshold.assigned_batch_id = "batch-1"
        self.mock_threshold_repo.get_by_device_id.return_value = threshold

        record = self._make_env_record(temp_anomaly=True)
        self.mock_env_service.create_record.return_value = record
        self.mock_env_repo.save.return_value = record
        self.mock_env_repo.find_by_device_in_interval.return_value = [record]
        self.mock_env_service.calculate_averages.return_value = {
            "average_temperature": 50.0, "average_humidity": 60.0
        }

        with patch.object(self.service, "_send_environment_telemetry_to_cloud"):
            saved, _ = self.service.create_environment_record("device-1", 50.0, 60.0, None)

        # Verify create_record was called with temperature_is_anomaly=True
        call_kwargs = self.mock_env_service.create_record.call_args
        assert call_kwargs.kwargs.get("temperature_is_anomaly") is True or \
               (len(call_kwargs.args) > 4 and call_kwargs.args[4] is True)

    def test_environment_record_is_persisted_exactly_once(self):
        """UT-ES-07d: Repository.save is called exactly once per request."""
        self.mock_device_repo.find_by_id.return_value = MagicMock()
        threshold = MagicMock()
        threshold.minimum_temperature_in_celsius = None
        threshold.maximum_temperature_in_celsius = None
        threshold.minimum_humidity_percentage = None
        threshold.maximum_humidity_percentage = None
        threshold.assigned_batch_id = None
        self.mock_threshold_repo.get_by_device_id.return_value = threshold

        record = self._make_env_record()
        self.mock_env_service.create_record.return_value = record
        self.mock_env_repo.save.return_value = record
        self.mock_env_repo.find_by_device_in_interval.return_value = [record]
        self.mock_env_service.calculate_averages.return_value = {
            "average_temperature": 25.0, "average_humidity": 60.0
        }

        with patch.object(self.service, "_send_environment_telemetry_to_cloud"):
            self.service.create_environment_record("device-1", 25.0, 60.0, None)

        self.mock_env_repo.save.assert_called_once()
