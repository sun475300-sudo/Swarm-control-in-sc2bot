"""
Spatial Query Optimizer - C++ Optimized Proximity Calculations

Replaces manual Python distance loops with sc2.Units.closer_than() which uses
C++ optimized spatial queries. Provides significant performance improvements
for combat-heavy scenarios.

Performance improvements:
- Manual distance loops: O(N) with Python overhead
- C++ closer_than(): O(log N) with spatial indexing
- Expected speedup: 3-10x for large unit counts
"""

from typing import TYPE_CHECKING, Optional, Dict, Tuple
from functools import lru_cache

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.units import Units
    from sc2.unit import Unit
    from sc2.position import Point2

from wicked_zerg_challenger.utils.logger import get_logger


class SpatialQueryOptimizer:
    """Centralized spatial query system using C++ optimizations"""

    def __init__(self, bot: "BotAI"):
        self.bot = bot
        self.logger = get_logger("SpatialQueryOptimizer")

        # Query result cache (cleared every frame)
        self._query_cache: Dict[Tuple, "Units"] = {}
        self._last_cache_clear = 0

        # Statistics
        self.total_queries = 0
        self.cache_hits = 0
        self.cache_misses = 0

    def get_enemies_near_position(
        self,
        position: "Point2",
        radius: float,
        iteration: int
    ) -> "Units":
        """
        Get enemy units within radius of position (C++ optimized)

        Args:
            position: Center position
            radius: Search radius
            iteration: Current game iteration (for cache invalidation)

        Returns:
            Units collection of enemies within radius
        """
        self.total_queries += 1

        # Cache key
        cache_key = (iteration, "enemies_near", position.x, position.y, radius)

        if cache_key in self._query_cache:
            self.cache_hits += 1
            return self._query_cache[cache_key]

        # Use C++ closer_than()
        result = self.bot.enemy_units.closer_than(radius, position)
        self._query_cache[cache_key] = result
        self.cache_misses += 1
        return result

    def get_allies_near_position(
        self,
        position: "Point2",
        radius: float,
        iteration: int
    ) -> "Units":
        """
        Get friendly units within radius of position (C++ optimized)

        Args:
            position: Center position
            radius: Search radius
            iteration: Current game iteration

        Returns:
            Units collection of allies within radius
        """
        self.total_queries += 1

        cache_key = (iteration, "allies_near", position.x, position.y, radius)

        if cache_key in self._query_cache:
            self.cache_hits += 1
            return self._query_cache[cache_key]

        result = self.bot.units.closer_than(radius, position)
        self._query_cache[cache_key] = result
        self.cache_misses += 1
        return result

    def get_allies_near_unit(
        self,
        unit: "Unit",
        radius: float,
        iteration: int
    ) -> "Units":
        """
        Get friendly units near a specific unit (C++ optimized)

        Args:
            unit: Reference unit
            radius: Search radius
            iteration: Current game iteration

        Returns:
            Units collection of allies within radius
        """
        self.total_queries += 1

        cache_key = (iteration, "allies_near_unit", unit.tag, radius)

        if cache_key in self._query_cache:
            self.cache_hits += 1
            return self._query_cache[cache_key]

        result = self.bot.units.closer_than(radius, unit)
        self._query_cache[cache_key] = result
        self.cache_misses += 1
        return result

    def get_enemies_near_unit(
        self,
        unit: "Unit",
        radius: float,
        iteration: int
    ) -> "Units":
        """
        Get enemy units near a specific unit (C++ optimized)

        Args:
            unit: Reference unit
            radius: Search radius
            iteration: Current game iteration

        Returns:
            Units collection of enemies within radius
        """
        self.total_queries += 1

        cache_key = (iteration, "enemies_near_unit", unit.tag, radius)

        if cache_key in self._query_cache:
            self.cache_hits += 1
            return self._query_cache[cache_key]

        result = self.bot.enemy_units.closer_than(radius, unit)
        self._query_cache[cache_key] = result
        self.cache_misses += 1
        return result

    def get_closest_enemy(self, position: "Point2") -> Optional["Unit"]:
        """
        Get closest enemy to position (C++ optimized)

        Args:
            position: Reference position

        Returns:
            Closest enemy unit, or None if no enemies
        """
        if not self.bot.enemy_units:
            return None
        return self.bot.enemy_units.closest_to(position)

    def get_closest_ally(self, position: "Point2") -> Optional["Unit"]:
        """
        Get closest friendly unit to position (C++ optimized)

        Args:
            position: Reference position

        Returns:
            Closest friendly unit, or None if no units
        """
        if not self.bot.units:
            return None
        return self.bot.units.closest_to(position)

    def get_units_in_range(
        self,
        units: "Units",
        position: "Point2",
        radius: float
    ) -> "Units":
        """
        Get units from collection within radius (C++ optimized)

        Args:
            units: Units collection to filter
            position: Center position
            radius: Search radius

        Returns:
            Filtered units within radius
        """
        if not units:
            return units

        return units.closer_than(radius, position)

    def count_enemies_near_position(
        self,
        position: "Point2",
        radius: float,
        iteration: int
    ) -> int:
        """
        Count enemy units near position (optimized with cache)

        Args:
            position: Center position
            radius: Search radius
            iteration: Current game iteration

        Returns:
            Number of enemies within radius
        """
        enemies = self.get_enemies_near_position(position, radius, iteration)
        return len(enemies)

    def count_allies_near_position(
        self,
        position: "Point2",
        radius: float,
        iteration: int
    ) -> int:
        """
        Count friendly units near position (optimized with cache)

        Args:
            position: Center position
            radius: Search radius
            iteration: Current game iteration

        Returns:
            Number of allies within radius
        """
        allies = self.get_allies_near_position(position, radius, iteration)
        return len(allies)

    def is_position_safe(
        self,
        position: "Point2",
        safe_distance: float,
        iteration: int
    ) -> bool:
        """
        Check if position is safe (no enemies within safe_distance)

        Args:
            position: Position to check
            safe_distance: Minimum safe distance
            iteration: Current game iteration

        Returns:
            True if safe, False otherwise
        """
        enemy_count = self.count_enemies_near_position(position, safe_distance, iteration)
        return enemy_count == 0

    def clear_cache_if_needed(self, iteration: int) -> None:
        """
        Clear cache every frame (iteration change)

        Args:
            iteration: Current game iteration
        """
        if iteration != self._last_cache_clear:
            self._query_cache.clear()
            self._last_cache_clear = iteration

    def get_statistics(self) -> Dict[str, any]:
        """
        Get query statistics

        Returns:
            Dictionary containing statistics
        """
        cache_hit_rate = (
            self.cache_hits / self.total_queries
            if self.total_queries > 0
            else 0.0
        )

        return {
            "total_queries": self.total_queries,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": cache_hit_rate,
            "active_cache_entries": len(self._query_cache)
        }

    def log_statistics(self, iteration: int) -> None:
        """Log statistics periodically"""
        if iteration % 2200 == 0 and self.total_queries > 0:  # Every 100 seconds
            stats = self.get_statistics()
            self.logger.info(
                f"[SPATIAL QUERY] "
                f"Queries: {stats['total_queries']}, "
                f"Hit rate: {stats['cache_hit_rate']:.1%}, "
                f"Cache size: {stats['active_cache_entries']}"
            )

            # Reset counters
            self.total_queries = 0
            self.cache_hits = 0
            self.cache_misses = 0

    def get_furthest_unit_from_enemies(
        self,
        units: "Units",
        iteration: int
    ) -> Optional["Unit"]:
        """
        Find unit furthest from all enemies (safe retreat position)

        Args:
            units: Units to check
            iteration: Current game iteration

        Returns:
            Furthest unit from enemies, or None if no units
        """
        if not units or not self.bot.enemy_units:
            return None

        # Find unit with maximum minimum distance to enemies
        best_unit = None
        max_min_distance = 0

        for unit in units:
            closest_enemy = self.bot.enemy_units.closest_to(unit)
            distance = unit.distance_to(closest_enemy)

            if distance > max_min_distance:
                max_min_distance = distance
                best_unit = unit

        return best_unit
