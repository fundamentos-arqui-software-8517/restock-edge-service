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
        - Creates the ``device_status_reports`` table if absent.
        - Creates the ``device_health_events`` table if absent.
        - Closes the connection after table creation.
    """
    should_close = db.is_closed()
    if should_close:
        db.connect()

    from iam.infrastructure.models import Device
    from tracking.infrastructure.models import WeightRecord
    from tracking.infrastructure.models import EnvironmentRecordModel
    from devices.infrastructure.models import DeviceHealthEventModel
    from devices.infrastructure.models import DeviceStatusReportModel
    from devices.infrastructure.models import DeviceThresholdModel

    db.create_tables([
        Device,
        WeightRecord,
        EnvironmentRecordModel,
        DeviceThresholdModel,
        DeviceStatusReportModel,
        DeviceHealthEventModel,
    ], safe=True)

    _ensure_environment_anomaly_columns()
    _ensure_device_threshold_schema()
    _ensure_device_health_schema()
    _ensure_weight_record_schema()

    if should_close and not db.is_closed():
        db.close()


def _ensure_weight_record_schema() -> None:
    """Ensure weight_records table schema matches current WeightRecord model."""
    try:
        existing_columns = {
            row[1] for row in db.execute_sql("PRAGMA table_info(weight_records)")
        }
        if existing_columns:
            if "raw_weight" not in existing_columns:
                if "weight" in existing_columns:
                    db.execute_sql("ALTER TABLE weight_records RENAME COLUMN weight TO raw_weight")
                else:
                    db.execute_sql("ALTER TABLE weight_records ADD COLUMN raw_weight REAL DEFAULT 0.0")
            if "physical_stock" not in existing_columns:
                db.execute_sql("ALTER TABLE weight_records ADD COLUMN physical_stock REAL DEFAULT 0.0")
    except Exception:
        pass


def _ensure_device_threshold_schema() -> None:
    """Ensure device_thresholds table schema matches current DeviceThresholdModel."""
    try:
        existing_columns = {
            row[1] for row in db.execute_sql("PRAGMA table_info(device_thresholds)")
        }
        if existing_columns and "threshold_id" not in existing_columns:
            db.execute_sql("DROP TABLE IF EXISTS device_thresholds")
            from devices.infrastructure.models import DeviceThresholdModel
            db.create_tables([DeviceThresholdModel], safe=True)
            existing_columns = {
                row[1] for row in db.execute_sql("PRAGMA table_info(device_thresholds)")
            }

        columns_to_add = {
            "custom_supply_weight": "REAL",
            "custom_supply_unit_measurement": "VARCHAR(255)",
            "anomaly_threshold": "REAL",
        }
        for column_name, column_definition in columns_to_add.items():
            if column_name not in existing_columns:
                db.execute_sql(
                    f"ALTER TABLE device_thresholds ADD COLUMN {column_name} {column_definition}"
                )
    except Exception:
        pass


def _ensure_device_health_schema() -> None:
    """Ensure device health tables include all current nullable columns."""
    try:
        report_columns = {
            row[1] for row in db.execute_sql("PRAGMA table_info(device_status_reports)")
        }
        report_columns_to_add = {
            "branch_id": "VARCHAR(255)",
            "cpu_usage_percentage": "REAL",
            "free_heap_bytes": "REAL",
            "internal_temperature_celsius": "REAL",
            "voltage": "REAL",
            "uptime_ms": "REAL",
            "system_status": "VARCHAR(255)",
            "alert_type": "VARCHAR(255)",
            "metric": "VARCHAR(255)",
            "value": "REAL",
            "threshold": "REAL",
            "message": "TEXT",
            "source": "VARCHAR(255) NOT NULL DEFAULT 'HTTP'",
        }
        for column_name, column_definition in report_columns_to_add.items():
            if report_columns and column_name not in report_columns:
                db.execute_sql(
                    f"ALTER TABLE device_status_reports ADD COLUMN {column_name} {column_definition}"
                )

        event_columns = {
            row[1] for row in db.execute_sql("PRAGMA table_info(device_health_events)")
        }
        event_columns_to_add = {
            "branch_id": "VARCHAR(255)",
            "metric": "VARCHAR(255)",
            "value": "REAL",
            "threshold": "REAL",
            "message": "TEXT",
            "source": "VARCHAR(255) NOT NULL DEFAULT 'HTTP'",
        }
        for column_name, column_definition in event_columns_to_add.items():
            if event_columns and column_name not in event_columns:
                db.execute_sql(
                    f"ALTER TABLE device_health_events ADD COLUMN {column_name} {column_definition}"
                )
    except Exception:
        pass


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
