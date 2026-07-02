"""Shared database infrastructure for the Restock Edge Service.

Provides a single :class:`peewee.SqliteDatabase` instance (``db``) that is
imported by ORM models across all bounded contexts, ensuring every model
operates on the same physical database file.

The :func:`init_db` helper is called once at application start-up to open a
connection and create any missing tables without affecting existing data
(``safe=True``).

Note:
    The ``db`` object itself is not connected until :func:`init_db` is called.
    Peewee's ``SqliteDatabase`` manages the connection lifecycle through its
    own thread-local storage.
"""
import os

from peewee import SqliteDatabase

# Shared SQLite database instance used by all bounded-context ORM models.
DB_PATH = os.getenv("SQLITE_DB_PATH", "restock_edge.db")

db = SqliteDatabase(DB_PATH)

def init_db() -> None:
    """Open the database connection and create all required tables.

    Imports ORM models from the IAM and Tracking bounded contexts at call time
    through deferred imports.  This avoids circular dependencies during module
    loading and keeps table creation centralized in the shared infrastructure.

    This function is idempotent: calling it when the tables already exist is
    safe and has no side effects because ``safe=True`` suppresses create-table
    errors for pre-existing tables.

    Side effects:
        - Opens a connection to ``restock_edge.db`` when needed.
        - Creates the ``devices`` table if absent.
        - Creates the ``weight_records`` table if absent.
        - Creates the ``device_thresholds`` table if absent.
        - Closes the connection after table creation.
    """
    should_close = db.is_closed()
    if should_close:
        db.connect()

    from iam.infrastructure.models import Device
    from tracking.infrastructure.models import WeightRecord
    from tracking.infrastructure.models import EnvironmentRecordModel
    from devices.infrastructure.models import DeviceThresholdModel

    db.create_tables([
        Device,
        WeightRecord,
        EnvironmentRecordModel,
        DeviceThresholdModel
    ], safe=True)

    _ensure_environment_anomaly_columns()

    if should_close and not db.is_closed():
        db.close()


def _ensure_environment_anomaly_columns() -> None:
    """Add anomaly flags to existing local environment records."""
    existing_columns = {
        row[1] for row in db.execute_sql("PRAGMA table_info(environment_records)")
    }
    anomaly_columns = {
        "temperature_is_anomaly": "INTEGER NOT NULL DEFAULT 0",
        "humidity_is_anomaly": "INTEGER NOT NULL DEFAULT 0",
    }

    for column_name, column_definition in anomaly_columns.items():
        if column_name not in existing_columns:
            db.execute_sql(
                f"ALTER TABLE environment_records ADD COLUMN {column_name} {column_definition}"
            )
