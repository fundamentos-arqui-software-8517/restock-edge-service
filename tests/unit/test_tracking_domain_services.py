"""Unit tests for tracking domain services (WeightRecordService and EnvironmentRecordService).

These tests validate the business invariants enforced by the domain layer without
any dependency on infrastructure (database, HTTP, etc.).
"""
import pytest
from datetime import datetime, timezone

from tracking.domain.services import WeightRecordService, EnvironmentRecordService
from tracking.domain.entities import WeightRecord, EnvironmentRecord


# ---------------------------------------------------------------------------
# WeightRecordService – Unit Tests
# ---------------------------------------------------------------------------

class TestWeightRecordServiceCalculatePhysicalStock:
    """UT-ES-01 – WeightRecordService.calculate_physical_stock"""

    def test_exact_multiple_returns_integer_stock(self):
        """When raw_weight is an exact multiple of custom_supply_weight the nearest
        integer stock is returned (within absolute tolerance)."""
        result = WeightRecordService.calculate_physical_stock(500.0, 250.0)
        assert result == 2

    def test_weight_within_relative_tolerance_snaps_to_nearest(self):
        """A residual weight within relative tolerance should snap to the nearest unit."""
        # 3 items × 100 g = 300 g; add 1 g residual → still within 5 % of 100 g = 5 g
        result = WeightRecordService.calculate_physical_stock(301.0, 100.0)
        assert result == 3

    def test_weight_outside_tolerance_returns_float_stock(self):
        """Large fractional physical stock: 250g / 100g = 2.5. However, the algorithm's
        permitted_weight_difference = 100 * min(10, max(3, 5)) = 500 g which is larger
        than the residual of 50 g, so it snaps to nearest integer 2."""
        result = WeightRecordService.calculate_physical_stock(250.0, 100.0)
        # Actual behavior: residual (50g) < permitted_weight_diff (500g) → snaps to 2
        assert result == 2

    def test_zero_raw_weight_raises_value_error(self):
        """A raw weight of 0 g leads to a physical stock ≤ 0 which is invalid."""
        with pytest.raises(ValueError):
            WeightRecordService.calculate_physical_stock(0.0, 100.0)

    def test_negative_weight_raises_value_error(self):
        with pytest.raises(ValueError):
            WeightRecordService.calculate_physical_stock(-10.0, 100.0)

    def test_weight_exceeds_maximum_raises_value_error(self):
        with pytest.raises(ValueError):
            WeightRecordService.calculate_physical_stock(99999.0, 100.0)

    def test_non_numeric_weight_raises_value_error(self):
        with pytest.raises(ValueError):
            WeightRecordService.calculate_physical_stock("heavy", 100.0)


class TestWeightRecordServiceCreateRecord:
    """UT-ES-02 – WeightRecordService.create_record"""

    def test_creates_record_with_valid_inputs(self):
        record = WeightRecordService.create_record("device-1", 500.0, 2, None)
        assert isinstance(record, WeightRecord)
        assert record.device_id == "device-1"
        assert record.raw_weight == 500.0
        assert record.physical_stock == 2
        assert record.created_at is not None

    def test_created_at_none_defaults_to_utc_now(self):
        before = datetime.now(timezone.utc)
        record = WeightRecordService.create_record("device-1", 100.0, 1, None)
        after = datetime.now(timezone.utc)
        assert before <= record.created_at <= after

    def test_created_at_iso_string_is_parsed_to_utc(self):
        record = WeightRecordService.create_record(
            "device-1", 100.0, 1, "2026-06-01T12:00:00-05:00"
        )
        assert record.created_at.tzinfo == timezone.utc
        assert record.created_at.hour == 17  # 12:00 -05:00 → 17:00 UTC

    def test_invalid_weight_raises_value_error(self):
        with pytest.raises(ValueError):
            WeightRecordService.create_record("device-1", -1.0, 0, None)


class TestWeightRecordServiceCalculateAverages:
    """UT-ES-03 – WeightRecordService.calculate_averages"""

    def test_returns_zero_for_empty_list(self):
        result = WeightRecordService.calculate_averages([])
        assert result == {"average_physical_stock": 0.0}

    def test_computes_average_correctly(self):
        records = [
            WeightRecord("d", 100.0, 2, datetime.now(timezone.utc)),
            WeightRecord("d", 200.0, 4, datetime.now(timezone.utc)),
        ]
        result = WeightRecordService.calculate_averages(records)
        assert result["average_physical_stock"] == 3.0


# ---------------------------------------------------------------------------
# EnvironmentRecordService – Unit Tests
# ---------------------------------------------------------------------------

class TestEnvironmentRecordServiceCreateRecord:
    """UT-ES-04 – EnvironmentRecordService.create_record"""

    def test_creates_record_with_valid_inputs(self):
        record = EnvironmentRecordService.create_record("dev-1", 25.0, 60.0, None)
        assert isinstance(record, EnvironmentRecord)
        assert record.device_id == "dev-1"
        assert record.temperature == 25.0
        assert record.humidity == 60.0

    def test_temperature_below_minimum_raises_value_error(self):
        with pytest.raises(ValueError):
            EnvironmentRecordService.create_record("dev-1", -50.0, 60.0, None)

    def test_temperature_above_maximum_raises_value_error(self):
        with pytest.raises(ValueError):
            EnvironmentRecordService.create_record("dev-1", 100.0, 60.0, None)

    def test_humidity_below_minimum_raises_value_error(self):
        with pytest.raises(ValueError):
            EnvironmentRecordService.create_record("dev-1", 25.0, -5.0, None)

    def test_humidity_above_maximum_raises_value_error(self):
        with pytest.raises(ValueError):
            EnvironmentRecordService.create_record("dev-1", 25.0, 110.0, None)

    def test_anomaly_flags_are_stored(self):
        record = EnvironmentRecordService.create_record(
            "dev-1", 25.0, 60.0, None,
            temperature_is_anomaly=True,
            humidity_is_anomaly=False,
        )
        assert record.temperature_is_anomaly is True
        assert record.humidity_is_anomaly is False

    def test_created_at_iso_string_is_parsed(self):
        record = EnvironmentRecordService.create_record(
            "dev-1", 25.0, 60.0, "2026-06-01T12:00:00Z"
        )
        assert record.created_at.tzinfo == timezone.utc


class TestEnvironmentRecordServiceCalculateAverages:
    """UT-ES-05 – EnvironmentRecordService.calculate_averages"""

    def test_returns_zeros_for_empty_list(self):
        result = EnvironmentRecordService.calculate_averages([])
        assert result == {"average_temperature": 0.0, "average_humidity": 0.0}

    def test_computes_averages_correctly(self):
        records = [
            EnvironmentRecord("d", 20.0, 50.0, datetime.now(timezone.utc)),
            EnvironmentRecord("d", 30.0, 70.0, datetime.now(timezone.utc)),
        ]
        result = EnvironmentRecordService.calculate_averages(records)
        assert result["average_temperature"] == 25.0
        assert result["average_humidity"] == 60.0
