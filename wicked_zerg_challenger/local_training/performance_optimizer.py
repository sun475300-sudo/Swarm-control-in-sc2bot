# -*- coding: utf-8 -*-
"""
Performance Optimizer - Unified optimization for combat and movement.

Integrates:
- PID control for smooth movement
- Spatial optimization (K-D Tree / Grid)
- Distance caching for reduced calculations
- Frame-rate optimization

Features:
- Automatic algorithm selection based on unit density
- Cached distance calculations
- Optimized unit iteration
"""

from typing import Any, Dict, List, Optional, Tuple
import time
import math


class DistanceCache:
    """
    Cache for expensive distance calculations.

    Reduces redundant distance_to calls during a single frame.
    """

    def __init__(self, cache_duration: float = 0.1):
        """
        Initialize distance cache.

        Args:
            cache_duration: How long to keep cached values (seconds)
        """
        self.cache_duration = cache_duration
        self.cache: Dict[Tuple[int, int], Tuple[float, float]] = {}
        self.last_clear = time.time()

    def get_distance(self, unit1, unit2) -> float:
        """
        Get cached distance or calculate and cache.

        Args:
            unit1: First unit
            unit2: Second unit

        Returns:
            Distance between units
        """
        # Clear old cache periodically
        now = time.time()
        if now - self.last_clear > self.cache_duration:
            self.cache.clear()
            self.last_clear = now

        # Create cache key (order-independent)
        key = (min(unit1.tag, unit2.tag), max(unit1.tag, unit2.tag))

        if key in self.cache:
            return self.cache[key][0]

        # Calculate distance
        dist = unit1.distance_to(unit2)
        self.cache[key] = (dist, now)
        return dist

    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        self.last_clear = time.time()


class PerformanceOptimizer:
    """
    Central performance optimization controller.

    Manages:
    - Spatial data structures
    - Distance caching
    - PID controllers for units
    - Frame budget allocation
    """

    def __init__(self, bot):
        """
        Initialize performance optimizer.

        Args:
            bot: Main bot instance
        """
        self.bot = bot

        # Distance cache
        self.distance_cache = DistanceCache()

        # Spatial structures (lazy loaded)
        self._kd_tree = None
        self._spatial_grid = None

        # PID controllers for units
        self._unit_pids: Dict[int, Any] = {}

        # Frame timing
        self.last_frame_time = time.time()
        self.frame_times: List[float] = []
        self.max_frame_history = 100

        # Configuration
        self.use_kd_tree = True  # vs spatial grid
        self.kd_tree_threshold = 50  # Use K-D tree when > 50 units

        # Import utilities
        try:
            from utils.kd_tree import KDTree, build_unit_kdtree
            from utils.spatial_partition import SpatialGrid, build_unit_grid
            from utils.pid_controller import UnitMovementController

            self.KDTree = KDTree
            self.build_unit_kdtree = build_unit_kdtree
            self.SpatialGrid = SpatialGrid
            self.build_unit_grid = build_unit_grid
            self.UnitMovementController = UnitMovementController
            self._spatial_available = True
        except ImportError:
            self._spatial_available = False

    def start_frame(self) -> None:
        """Call at the start of each frame."""
        self.last_frame_time = time.time()
        self.distance_cache.clear()

    def end_frame(self) -> None:
        """Call at the end of each frame."""
        frame_time = time.time() - self.last_frame_time
        self.frame_times.append(frame_time)
        if len(self.frame_times) > self.max_frame_history:
            self.frame_times.pop(0)

    def get_average_frame_time(self) -> float:
        """Get average frame time in seconds."""
        if not self.frame_times:
            return 0.0
        return sum(self.frame_times) / len(self.frame_times)

    def build_spatial_index(self, units) -> None:
        """
        Build spatial index for units.

        Args:
            units: Units to index
        """
        if not self._spatial_available:
            return

        unit_count = len(units) if hasattr(units, "__len__") else units.amount

        if unit_count > self.kd_tree_threshold and self.use_kd_tree:
            self._kd_tree = self.build_unit_kdtree(units)
            self._spatial_grid = None
        else:
            self._spatial_grid = self.build_unit_grid(units)
            self._kd_tree = None

    def find_units_in_radius(
        self, position: Tuple[float, float], radius: float, units=None
    ) -> List[Tuple[Any, float]]:
        """
        Find units within radius of position.

        Args:
            position: (x, y) center
            radius: Search radius
            units: Units to search (uses spatial index if available)

        Returns:
            List of (unit, distance) tuples
        """
        if self._kd_tree:
            results = self._kd_tree.range_query(position, radius)
            return [(r[1], r[2]) for r in results]
        elif self._spatial_grid:
            results = self._spatial_grid.query_radius(position, radius)
            return [(r[1], r[2]) for r in results]
        elif units:
            # Fallback to brute force
            results = []
            for unit in units:
                pos = unit.position
                dist = math.sqrt(
                    (pos.x - position[0]) ** 2 + (pos.y - position[1]) ** 2
                )
                if dist <= radius:
                    results.append((unit, dist))
            return results
        return []

    def find_nearest_unit(
        self, position: Tuple[float, float], units=None, exclude_unit=None
    ) -> Optional[Tuple[Any, float]]:
        """
        Find nearest unit to position.

        Args:
            position: (x, y) query point
            units: Units to search
            exclude_unit: Unit to exclude from search

        Returns:
            (unit, distance) or None
        """
        if self._kd_tree:
            result = self._kd_tree.nearest_neighbor(position, exclude_unit)
            if result:
                return (result[1], result[2])
        elif self._spatial_grid:
            result = self._spatial_grid.nearest_neighbor(position, exclude_unit)
            if result:
                return (result[1], result[2])
        elif units:
            # Brute force
            best = None
            best_dist = float("inf")
            for unit in units:
                if unit == exclude_unit:
                    continue
                pos = unit.position
                dist = math.sqrt(
                    (pos.x - position[0]) ** 2 + (pos.y - position[1]) ** 2
                )
                if dist < best_dist:
                    best = unit
                    best_dist = dist
            if best:
                return (best, best_dist)
        return None

    def get_unit_controller(self, unit_tag: int) -> Any:
        """
        Get or create PID controller for unit.

        Args:
            unit_tag: Unit tag

        Returns:
            UnitMovementController
        """
        if not self._spatial_available:
            return None

        if unit_tag not in self._unit_pids:
            self._unit_pids[unit_tag] = self.UnitMovementController()
        return self._unit_pids[unit_tag]

    def calculate_optimal_movement(
        self, unit, target_position: Tuple[float, float], dt: float = 0.1
    ) -> Tuple[float, float]:
        """
        Calculate optimal velocity for unit movement.

        Args:
            unit: Unit to move
            target_position: Target (x, y)
            dt: Time step

        Returns:
            (vx, vy) optimal velocity
        """
        controller = self.get_unit_controller(unit.tag)
        if controller is None:
            # Fallback: direct movement
            dx = target_position[0] - unit.position.x
            dy = target_position[1] - unit.position.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                return (dx / dist * 5.0, dy / dist * 5.0)
            return (0.0, 0.0)

        current = (unit.position.x, unit.position.y)
        return controller.calculate_velocity(current, target_position, dt)

    def cleanup_dead_units(self, alive_tags: set) -> None:
        """
        Remove controllers for dead units.

        Args:
            alive_tags: Set of alive unit tags
        """
        dead_tags = [tag for tag in self._unit_pids if tag not in alive_tags]
        for tag in dead_tags:
            del self._unit_pids[tag]

    def get_cached_distance(self, unit1, unit2) -> float:
        """
        Get distance with caching.

        Args:
            unit1: First unit
            unit2: Second unit

        Returns:
            Distance
        """
        return self.distance_cache.get_distance(unit1, unit2)

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        return {
            "avg_frame_time_ms": self.get_average_frame_time() * 1000,
            "cache_size": len(self.distance_cache.cache),
            "pid_controllers": len(self._unit_pids),
            "spatial_index": "kd_tree" if self._kd_tree else ("grid" if self._spatial_grid else "none"),
            "spatial_available": self._spatial_available,
        }
