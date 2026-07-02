"""Repository implementation for the Tracking bounded context.

Provides the persistence adapter that maps between the: class:`~tracking.domain.entities.WeightRecord` domain entity and
the: class:`~tracking.infrastructure.models.WeightRecord` Peewee ORM model.

Following the Repository pattern, callers in the application layer interact
only with domain entities and are shielded from ORM and database details.
"""
from datetime import datetime, timedelta, timezone

from tracking.domain.entities import EnvironmentRecord
from tracking.domain.entities import WeightRecord
from tracking.infrastructure.models import EnvironmentRecordModel
from tracking.infrastructure.models import WeightRecord as WeightRecordModel


class WeightRecordRepository:
    """Repository that persists and reconstructs WeightRecord entities.

    Acts as an in-process collection of domain entities backed by the local
    SQLite database.  Mapping between the ORM model and the domain entity is handled
    entirely within this class, keeping the domain layer free of infrastructure
    concerns.
    """

    DEFAULT_INTERVAL_MINUTES = 60

    @staticmethod
    def save(weight_record: WeightRecord) -> WeightRecord:
        """Persist a transient WeightRecord entity.

        Inserts a new row into the ``weight_records`` table using Peewee's
        ``create`` helper and returns a new domain entity instance populated
        with the database-assigned ``id``.

        Args:
            weight_record (WeightRecord): Transient entity to persist. Its
                ``id`` attribute is expected to be ``None`` at this point.

        Returns:
            WeightRecord: Copy of the input entity enriched with the assigned
            database ``id``.
        """
        record = WeightRecordModel.create(
            device_id=weight_record.device_id,
            raw_weight=weight_record.raw_weight,
            physical_stock=weight_record.physical_stock,
        )

        return WeightRecord(
            weight_record.device_id,
            weight_record.raw_weight,
            weight_record.physical_stock,
            record.created_at,
            record.id,
        )

    @classmethod
    def find_by_device_in_interval(
            cls, device_id: str, interval_minutes: int = None
    ) -> list:
        """Retrieve weight records for a device within a time interval.

        Queries the ``weight_records`` table for all rows belonging to
        the given ``device_id`` whose ``created_at`` timestamp falls within
        the last ``interval_minutes`` minutes relative to the current UTC
        time.

        Args:
            device_id (str): Identifier of the device to query.
            interval_minutes (int, optional): Size of the look-back window in
                minutes. Defaults to
                :attr:`DEFAULT_INTERVAL_MINUTES` (60).

        Returns:
            list[WeightRecord]: Domain entities reconstructed from
            matching database rows, ordered by ``created_at`` ascending.
        """
        if interval_minutes is None:
            interval_minutes = cls.DEFAULT_INTERVAL_MINUTES

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=interval_minutes)
        query = (
            WeightRecordModel
            .select()
            .where(
                (WeightRecordModel.device_id == device_id)
                & (WeightRecordModel.created_at >= cutoff)
            )
            .order_by(WeightRecordModel.created_at.asc())
        )
        records = []
        for record in query:
            dt = record.created_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            records.append(
                WeightRecord(
                    record.device_id,
                    record.raw_weight,
                    record.physical_stock,
                    dt,
                    record.id,
                )
            )
        return records


class EnvironmentRecordRepository:
    """Repository that persists and reconstructs EnvironmentRecord entities.

    Acts as an in-process collection of domain entities backed by the local
    SQLite database.  Mapping between ORM model and the domain entity is handled
    entirely within this class, keeping the domain layer free of infrastructure
    concerns.
    """

    DEFAULT_INTERVAL_MINUTES = 60

    @staticmethod
    def save(environment_record: EnvironmentRecord) -> EnvironmentRecord:
        """Persists a transient EnvironmentRecord entity.

        Inserts a new row into the ``environment_records`` table using Peewee's
        ``create`` helper and returns a new domain entity instance populated
        with the database-assigned ``id``.

        Args:
            environment_record (EnvironmentRecord): Transient entity to
                persist. Its ``id`` attribute is expected to be ``None`` at
                this point.

        Returns:
            EnvironmentRecord: Copy of the input entity enriched with the
            assigned database ``id``.
        """
        record = EnvironmentRecordModel.create(
            device_id=environment_record.device_id,
            temperature=environment_record.temperature,
            humidity=environment_record.humidity,
            temperature_is_anomaly=environment_record.temperature_is_anomaly,
            humidity_is_anomaly=environment_record.humidity_is_anomaly,
            created_at=environment_record.created_at,
        )
        return EnvironmentRecord(
            environment_record.device_id,
            environment_record.temperature,
            environment_record.humidity,
            environment_record.created_at,
            record.id,
            record.temperature_is_anomaly,
            record.humidity_is_anomaly,
        )

    @classmethod
    def find_by_device_in_interval(
        cls, device_id: str, interval_minutes: int = None
    ) -> list:
        """Retrieve environment records for a device within a time interval.

        Queries the ``environment_records`` table for all rows belonging to
        the given ``device_id`` whose ``created_at`` timestamp falls within
        the last ``interval_minutes`` minutes relative to the current UTC
        time.

        Args:
            device_id (str): Identifier of the device to query.
            interval_minutes (int, optional): Size of the look-back window in
                minutes. Defaults to
                :attr:`DEFAULT_INTERVAL_MINUTES` (60).

        Returns:
            list[EnvironmentRecord]: Domain entities reconstructed from
            matching database rows, ordered by ``created_at`` ascending.
        """
        if interval_minutes is None:
            interval_minutes = cls.DEFAULT_INTERVAL_MINUTES

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=interval_minutes)
        query = (
            EnvironmentRecordModel
            .select()
            .where(
                (EnvironmentRecordModel.device_id == device_id)
                & (EnvironmentRecordModel.created_at >= cutoff)
            )
            .order_by(EnvironmentRecordModel.created_at.asc())
        )
        records = []
        for record in query:
            dt = record.created_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            records.append(
                EnvironmentRecord(
                    record.device_id,
                    record.temperature,
                    record.humidity,
                    dt,
                    record.id,
                    record.temperature_is_anomaly,
                    record.humidity_is_anomaly,
                )
            )
        return records
