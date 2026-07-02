"""Domain services for the Tracking bounded context.

Domain services encapsulate business logic that does not naturally belong to a
single entity.  ``WeightRecordService`` validates raw sensor input and creates a
well-formed :class:`~tracking.domain.entities.WeightRecord` aggregate,
enforcing the invariants of the Tracking bounded context.
"""
from datetime import datetime, timezone

from dateutil.parser import parse

from tracking.domain.entities import WeightRecord
from tracking.domain.entities import EnvironmentRecord


class WeightRecordService:
    """Domain service responsible for the creation of valid weight records.

    This service enforces the current business invariants for Restock weight
    telemetry:

    - ``weight`` must be a numeric value.
    - ``weight`` must be in the range [0, 20000] grams for the initial smart
      scale prototype.
    - ``created_at``, when supplied, must be a valid ISO 8601 timestamp.
    - ``created_at`` is normalized to UTC before persistence.
    """

    MIN_WEIGHT_GRAMS = 0.0
    MAX_WEIGHT_GRAMS = 20000.0
    ABSOLUTE_TOLERANCE_GRAMS = 3.0
    RELATIVE_TOLERANCE_PERCENTAGE = 0.05
    MAXIMUM_DIFFERENCE_GRAMS = 10.0

    @classmethod
    def calculate_physical_stock(cls, raw_weight: float, custom_supply_weight: float) -> int | float:
        """
        Algorithm to calculate the physical stock based on the raw weight and custom supply weight.

        This uses a combination of absolute and relative tolerances to determine the permitted weight difference.

        :param raw_weight: The raw weight of the product.
        :param custom_supply_weight: The custom supply weight of the product.
        :return: Either the calculated physical stock or the nearest stock if the residual weight is within the permitted weight difference.
        """

        try:
            parsed_raw_weight = float(raw_weight)
            if not (cls.MIN_WEIGHT_GRAMS <= parsed_raw_weight <= cls.MAX_WEIGHT_GRAMS):
                raise ValueError("Invalid weight value")

            parsed_custom_supply_weight = float(custom_supply_weight)
            if not (cls.MIN_WEIGHT_GRAMS <= parsed_custom_supply_weight <= cls.MAX_WEIGHT_GRAMS):
                raise ValueError("Invalid custom supply weight value")
        except (ValueError, TypeError):
            raise ValueError("Invalid data format")

        # Calculate the physical stock based on the raw weight and custom supply weight
        calculated_physical_stock = parsed_raw_weight / parsed_custom_supply_weight

        # If the calculated physical stock is out of range, raise an error
        if calculated_physical_stock <= 0.0:
            raise ValueError(f"Calculated physical stock is out of range: {calculated_physical_stock}")

        # Determine the permitted difference between the maximum difference and the maximum between the absolute and relative tolerances
        permitted_difference = min(
            cls.MAXIMUM_DIFFERENCE_GRAMS,
            max(
                cls.ABSOLUTE_TOLERANCE_GRAMS,
                custom_supply_weight * cls.RELATIVE_TOLERANCE_PERCENTAGE
            )
        )

        # Round the calculated physical stock to the nearest integer and compare it to the raw weight
        nearest_stock = round(calculated_physical_stock)

        # Calculate the expected weight based on the nearest stock and custom supply weight
        expected_weight = nearest_stock * custom_supply_weight

        # Calculate the residual weight between the raw weight and the expected weight
        residual_weight = abs(raw_weight - expected_weight)

        # Calculate the permitted weight difference based on the custom supply weight and the permitted difference
        permitted_weight_difference = custom_supply_weight * permitted_difference

        # Evaluate the residual weight against the permitted weight difference
        if residual_weight <= permitted_weight_difference:

            # If the residual weight is within the permitted weight difference, return the nearest stock
            return nearest_stock

        # If the residual weight exceeds the permitted weight difference, return the original calculated physical stock
        return calculated_physical_stock

    @classmethod
    def create_record(cls, device_id: str, weight: float, physical_stock: float, created_at: str | None) -> WeightRecord:
        """Validate raw sensor data and create a new WeightRecord entity.

        Applies domain invariants before constructing the aggregate:

        * ``weight`` is coerced to ``float`` and validated in the range [0, 20000] grams.
        * ``created_at`` is parsed and converted to UTC; when ``None``, the current UTC timestamp is used.
        * ``physical_stock`` is calculated based on the raw weight and custom supply weight.
        * ``device_id`` is validated.

        :return: New unsaved domain entity with a UTC-normalized ``created_at`` value.
        """
        try:
            parsed_weight = float(weight)
            if not (cls.MIN_WEIGHT_GRAMS <= parsed_weight <= cls.MAX_WEIGHT_GRAMS):
                raise ValueError("Invalid weight value")

            if created_at:
                parsed = parse(created_at)
                if parsed.tzinfo is None:
                    parsed_created_at = parsed.replace(tzinfo=timezone.utc)
                else:
                    parsed_created_at = parsed.astimezone(timezone.utc)
            else:
                parsed_created_at = datetime.now(timezone.utc)
        except (ValueError, TypeError):
            raise ValueError("Invalid data format")

        return WeightRecord(device_id, parsed_weight, physical_stock, parsed_created_at)

    @classmethod
    def calculate_averages(cls, records: list) -> dict:
        """Calculates the average of physical stock.

        Given a list of :class:`~tracking.domain.entities.WeightRecord`
        instances, returns the mean of physical stock values.

        Args:
            records (list[WeightRecord]): Collection of weight records to aggregate.

        Returns:
            dict: Dictionary with ``average_physical_stock`` as a key holding a ``float`` rounded to two
            decimal places.  Returns ``0.0`` if ``record`` is empty.
        """
        if not records:
            return {"average_physical_stock": 0.0}

        total_physical_stock = sum(r.physical_stock for r in records)
        count = len(records)

        return {
            "average_physical_stock": round(total_physical_stock / count, 2),
        }


class EnvironmentRecordService:
    """Domain service responsible for the creation and aggregation of
    environment records.

    This service enforces the current business invariants for Restock
    environment telemetry:

    - ``temperature`` must be a numeric value in the range [-40, 80] °C.
    - ``humidity`` must be a numeric value in the range [0, 100] %.
    - ``created_at``, when supplied, must be a valid ISO 8601 timestamp.
    - ``created_at`` is normalized to UTC before persistence.

    It also provides a helper to compute the arithmetic average of temperature
    and humidity from a collection of records.
    """

    MIN_TEMPERATURE_CELSIUS = -40.0
    MAX_TEMPERATURE_CELSIUS = 80.0
    MIN_HUMIDITY_PERCENTAGE = 0.0
    MAX_HUMIDITY_PERCENTAGE = 100.0

    @classmethod
    def create_record(
            cls,
            device_id: str,
            temperature: float,
            humidity: float,
            created_at: str | None,
            temperature_is_anomaly: bool = False,
            humidity_is_anomaly: bool = False,
    ) -> EnvironmentRecord:
        """Validate raw sensor data and create a new EnvironmentRecord entity.

        Applies domain invariants before constructing the aggregate:

        * ``temperature`` is coerced to ``float`` and validated in the range
          [-40, 80].
        * ``humidity`` is coerced to ``float`` and validated in the range
          [0, 100].
        * ``created_at`` is parsed and converted to UTC; when ``None``, the
          current UTC timestamp is used.

        Args:
            device_id (str): Identifier of the originating device.
            temperature (float): Temperature reading expressed in degrees
                Celsius.
            humidity (float): Relative humidity reading expressed as a
                percentage.
            created_at (str | None): ISO 8601 timestamp of the reading, for
                example ``'2026-05-25T12:00:00-05:00'``; or ``None`` to use
                the current UTC time.

        Returns:
            EnvironmentRecord: New unsaved domain entity with a UTC-normalized
            ``created_at`` value.

        Raises:
            ValueError: If ``temperature`` or ``humidity`` is not convertible
            to ``float``, falls outside the allowed range, or if
            ``created_at`` is not valid ISO 8601.
        """
        try:
            parsed_temperature = float(temperature)
            if not (cls.MIN_TEMPERATURE_CELSIUS <= parsed_temperature <= cls.MAX_TEMPERATURE_CELSIUS):
                raise ValueError("Invalid temperature value")

            parsed_humidity = float(humidity)
            if not (cls.MIN_HUMIDITY_PERCENTAGE <= parsed_humidity <= cls.MAX_HUMIDITY_PERCENTAGE):
                raise ValueError("Invalid humidity value")

            if created_at:
                parsed = parse(created_at)
                if parsed.tzinfo is None:
                    parsed_created_at = parsed.replace(tzinfo=timezone.utc)
                else:
                    parsed_created_at = parsed.astimezone(timezone.utc)
            else:
                parsed_created_at = datetime.now(timezone.utc)
        except (ValueError, TypeError):
            raise ValueError("Invalid data format")

        return EnvironmentRecord(device_id, parsed_temperature,
                                 parsed_humidity, parsed_created_at,
                                 temperature_is_anomaly=temperature_is_anomaly,
                                 humidity_is_anomaly=humidity_is_anomaly)

    @classmethod
    def calculate_averages(cls, records: list) -> dict:
        """Compute the arithmetic average of temperature and humidity.

        Given a list of :class:`~tracking.domain.entities.EnvironmentRecord`
        instances, returns the mean temperature and humidity values.

        Args:
            records (list[EnvironmentRecord]): Collection of environment
                records to aggregate.

        Returns:
            dict: Dictionary with keys ``average_temperature`` and
            ``average_humidity``, each holding a ``float`` rounded to two
            decimal places.  Returns ``0.0`` for both if ``records`` is empty.
        """
        if not records:
            return {"average_temperature": 0.0, "average_humidity": 0.0}

        total_temperature = sum(r.temperature for r in records)
        total_humidity = sum(r.humidity for r in records)
        count = len(records)

        return {
            "average_temperature": round(total_temperature / count, 2),
            "average_humidity": round(total_humidity / count, 2),
        }
