# -*- coding: utf-8 -*-
"""
Common Helper Functions - Shared utilities across managers.

This module consolidates duplicate utility functions to reduce code duplication.
"""

from typing import Any, Iterable, Optional, Tuple

try:
    from sc2.position import Point2
except ImportError:
    Point2 = None


class SafeTrainHelper:
    """Helper for safe unit training with async/sync compatibility."""

    @staticmethod
    async def safe_train(unit, unit_type) -> bool:
        """
        Safely train a unit, handling both sync and async train() methods.

        Args:
            unit: The unit (typically larva) to train from
            unit_type: UnitTypeId to train

        Returns:
            True if training was initiated successfully
        """
        try:
            result = unit.train(unit_type)
            if hasattr(result, '__await__'):
                await result
            return True
        except Exception:
            return False


class UnitFilterHelper:
    """Helper for unit filtering and selection."""

    @staticmethod
    def closest_enemy(unit, enemies: Iterable) -> Optional[Any]:
        """
        Find the closest enemy to a given unit.

        Args:
            unit: The reference unit
            enemies: Iterable of enemy units

        Returns:
            Closest enemy unit or None
        """
        closest = None
        closest_dist = None
        for enemy in enemies:
            try:
                dist = unit.distance_to(enemy)
            except Exception:
                continue
            if closest_dist is None or dist < closest_dist:
                closest = enemy
                closest_dist = dist
        return closest

    @staticmethod
    def filter_by_type(units, type_names: list) -> list:
        """
        Filter units by type name.

        Args:
            units: Units to filter
            type_names: List of type names (e.g., ["ZERGLING", "ROACH"])

        Returns:
            Filtered list of units
        """
        if hasattr(units, "filter"):
            return units.filter(lambda u: u.type_id.name in type_names)
        return [u for u in units if getattr(u.type_id, "name", "") in type_names]

    @staticmethod
    def has_units(units) -> bool:
        """Check if units collection has any units."""
        if hasattr(units, "exists"):
            return bool(units.exists)
        return bool(units)

    @staticmethod
    def units_amount(units) -> int:
        """Get the amount/count of units."""
        if hasattr(units, "amount"):
            return int(units.amount)
        return len(units) if units else 0


class PositionHelper:
    """Helper for position calculations."""

    @staticmethod
    def centroid(units) -> Optional[Any]:
        """
        Calculate center of mass for a group of units.

        Args:
            units: Collection of units

        Returns:
            Point2 representing the centroid, or None
        """
        if not units or not Point2:
            return Point2((0, 0)) if Point2 else None

        try:
            unit_list = list(units)
            if not unit_list:
                return Point2((0, 0)) if Point2 else None

            total_x = sum(u.position.x for u in unit_list)
            total_y = sum(u.position.y for u in unit_list)
            count = len(unit_list)
            return Point2((total_x / count, total_y / count))
        except Exception:
            return Point2((0, 0)) if Point2 else None

    @staticmethod
    def get_first_larva(bot) -> Optional[Any]:
        """
        Get the first available larva.

        Args:
            bot: Bot instance

        Returns:
            First larva unit or None
        """
        larva = getattr(bot, "larva", None)
        if not larva:
            return None
        if hasattr(larva, "first"):
            return larva.first
        try:
            return next(iter(larva))
        except (StopIteration, TypeError):
            return None


class LogHelper:
    """Helper for throttled logging."""

    @staticmethod
    def log_with_interval(iteration: int, message: str, interval: int = 200) -> bool:
        """
        Log message only at specified intervals.

        Args:
            iteration: Current game iteration
            message: Message to log
            interval: Logging interval (default 200)

        Returns:
            True if message was logged
        """
        if iteration % interval == 0:
            print(message)
            return True
        return False

    @staticmethod
    def warning_with_interval(iteration: int, context: str, error: Exception, interval: int = 200) -> bool:
        """
        Log warning only at specified intervals.

        Args:
            iteration: Current game iteration
            context: Context description
            error: Exception that occurred
            interval: Logging interval (default 200)

        Returns:
            True if warning was logged
        """
        if iteration % interval == 0:
            print(f"[WARNING] {context}: {error}")
            return True
        return False


# Convenience functions for direct import
safe_train = SafeTrainHelper.safe_train
closest_enemy = UnitFilterHelper.closest_enemy
filter_by_type = UnitFilterHelper.filter_by_type
has_units = UnitFilterHelper.has_units
units_amount = UnitFilterHelper.units_amount
centroid = PositionHelper.centroid
get_first_larva = PositionHelper.get_first_larva
log_with_interval = LogHelper.log_with_interval
warning_with_interval = LogHelper.warning_with_interval
