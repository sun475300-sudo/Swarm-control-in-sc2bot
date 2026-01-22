# -*- coding: utf-8 -*-
"""
Grid-based Spatial Partition for Dense Unit Distributions

Provides O(N) spatial queries for densely distributed units.
More efficient than K-D Tree when units are clustered.

Features:
- Fast grid-based lookups
- Efficient for dense clusters
- Dynamic grid sizing
"""

from typing import Dict, List, Optional, Set, Tuple, Any
import math


class SpatialGrid:
    """
    Grid-based spatial partitioning for efficient proximity queries.

    Time Complexity:
    - Insert: O(1)
    - Query neighbors: O(k) where k is units in nearby cells
    - Range query: O(cells_checked * units_per_cell)
    """

    def __init__(self, cell_size: float = 5.0, map_size: Tuple[float, float] = (200.0, 200.0)):
        """
        Initialize spatial grid.

        Args:
            cell_size: Size of each grid cell (should match typical query radius)
            map_size: (width, height) of the map
        """
        self.cell_size = cell_size
        self.map_width = map_size[0]
        self.map_height = map_size[1]

        # Calculate grid dimensions
        self.grid_width = int(math.ceil(self.map_width / cell_size))
        self.grid_height = int(math.ceil(self.map_height / cell_size))

        # Grid storage: cell_key -> list of (position, data)
        self.grid: Dict[Tuple[int, int], List[Tuple[Tuple[float, float], Any]]] = {}

        # Reverse lookup: data -> cell_key
        self.data_to_cell: Dict[Any, Tuple[int, int]] = {}

        self.size = 0

    def clear(self) -> None:
        """Clear all entries from the grid."""
        self.grid.clear()
        self.data_to_cell.clear()
        self.size = 0

    def _get_cell(self, x: float, y: float) -> Tuple[int, int]:
        """Get grid cell coordinates for a position."""
        cell_x = int(x / self.cell_size)
        cell_y = int(y / self.cell_size)
        # Clamp to grid bounds
        cell_x = max(0, min(cell_x, self.grid_width - 1))
        cell_y = max(0, min(cell_y, self.grid_height - 1))
        return (cell_x, cell_y)

    def insert(self, position: Tuple[float, float], data: Any) -> None:
        """
        Insert a point into the grid.

        Args:
            position: (x, y) coordinates
            data: Associated data (e.g., unit)
        """
        cell = self._get_cell(position[0], position[1])

        if cell not in self.grid:
            self.grid[cell] = []

        self.grid[cell].append((position, data))
        self.data_to_cell[id(data)] = cell
        self.size += 1

    def remove(self, data: Any) -> bool:
        """
        Remove a point from the grid by its data.

        Args:
            data: Data to remove

        Returns:
            True if removed, False if not found
        """
        data_id = id(data)
        if data_id not in self.data_to_cell:
            return False

        cell = self.data_to_cell[data_id]
        if cell in self.grid:
            self.grid[cell] = [(p, d) for p, d in self.grid[cell] if id(d) != data_id]
            if not self.grid[cell]:
                del self.grid[cell]

        del self.data_to_cell[data_id]
        self.size -= 1
        return True

    def update(self, position: Tuple[float, float], data: Any) -> None:
        """
        Update position of existing data or insert if new.

        Args:
            position: New (x, y) coordinates
            data: Associated data
        """
        self.remove(data)
        self.insert(position, data)

    def query_radius(
        self, center: Tuple[float, float], radius: float, exclude_data: Any = None
    ) -> List[Tuple[Tuple[float, float], Any, float]]:
        """
        Find all points within radius of center.

        Args:
            center: (x, y) center point
            radius: Search radius
            exclude_data: Data to exclude from results

        Returns:
            List of ((x, y), data, distance) tuples
        """
        results = []

        # Calculate cells to check
        cells_to_check = int(math.ceil(radius / self.cell_size)) + 1
        center_cell = self._get_cell(center[0], center[1])

        # Check all cells within radius
        for dx in range(-cells_to_check, cells_to_check + 1):
            for dy in range(-cells_to_check, cells_to_check + 1):
                cell = (center_cell[0] + dx, center_cell[1] + dy)

                if cell not in self.grid:
                    continue

                for position, data in self.grid[cell]:
                    if data == exclude_data:
                        continue

                    dist = self._distance(center, position)
                    if dist <= radius:
                        results.append((position, data, dist))

        return results

    def nearest_neighbor(
        self, query: Tuple[float, float], exclude_data: Any = None
    ) -> Optional[Tuple[Tuple[float, float], Any, float]]:
        """
        Find nearest neighbor to query point.

        Args:
            query: (x, y) query point
            exclude_data: Data to exclude

        Returns:
            ((x, y), data, distance) or None
        """
        # Start with nearby cells and expand if needed
        for radius_multiplier in range(1, max(self.grid_width, self.grid_height) + 1):
            search_radius = self.cell_size * radius_multiplier
            results = self.query_radius(query, search_radius, exclude_data)

            if results:
                # Return closest
                results.sort(key=lambda r: r[2])
                return results[0]

        return None

    def k_nearest_neighbors(
        self, query: Tuple[float, float], k: int, exclude_data: Any = None
    ) -> List[Tuple[Tuple[float, float], Any, float]]:
        """
        Find k nearest neighbors.

        Args:
            query: (x, y) query point
            k: Number of neighbors
            exclude_data: Data to exclude

        Returns:
            List of ((x, y), data, distance) tuples, sorted by distance
        """
        # Expand search radius until we have enough results
        for radius_multiplier in range(1, max(self.grid_width, self.grid_height) + 1):
            search_radius = self.cell_size * radius_multiplier
            results = self.query_radius(query, search_radius, exclude_data)

            if len(results) >= k:
                results.sort(key=lambda r: r[2])
                return results[:k]

        # Return all if we don't have k
        results.sort(key=lambda r: r[2])
        return results

    def get_cell_contents(self, cell: Tuple[int, int]) -> List[Tuple[Tuple[float, float], Any]]:
        """Get all entries in a specific cell."""
        return self.grid.get(cell, [])

    def get_neighbors_in_cell(
        self, position: Tuple[float, float]
    ) -> List[Tuple[Tuple[float, float], Any]]:
        """Get all entries in the same cell as position."""
        cell = self._get_cell(position[0], position[1])
        return self.get_cell_contents(cell)

    @staticmethod
    def _distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance."""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        return math.sqrt(dx * dx + dy * dy)

    def __len__(self) -> int:
        return self.size

    def __bool__(self) -> bool:
        return self.size > 0


class DynamicSpatialPartition:
    """
    Adaptive spatial partition that switches between grid and brute force
    based on unit density.
    """

    def __init__(self, cell_size: float = 5.0, density_threshold: int = 10):
        """
        Initialize adaptive spatial partition.

        Args:
            cell_size: Grid cell size
            density_threshold: Minimum units to use grid (below this, use brute force)
        """
        self.cell_size = cell_size
        self.density_threshold = density_threshold
        self.grid: Optional[SpatialGrid] = None
        self.points: List[Tuple[Tuple[float, float], Any]] = []

    def build(
        self, points: List[Tuple[Tuple[float, float], Any]], map_size: Tuple[float, float] = (200.0, 200.0)
    ) -> None:
        """
        Build spatial structure from points.

        Args:
            points: List of ((x, y), data) tuples
            map_size: Map dimensions
        """
        self.points = points

        if len(points) >= self.density_threshold:
            # Use grid for dense distributions
            self.grid = SpatialGrid(self.cell_size, map_size)
            for position, data in points:
                self.grid.insert(position, data)
        else:
            self.grid = None

    def query_radius(
        self, center: Tuple[float, float], radius: float, exclude_data: Any = None
    ) -> List[Tuple[Tuple[float, float], Any, float]]:
        """Find all points within radius."""
        if self.grid:
            return self.grid.query_radius(center, radius, exclude_data)

        # Brute force for small point sets
        results = []
        for position, data in self.points:
            if data == exclude_data:
                continue
            dist = SpatialGrid._distance(center, position)
            if dist <= radius:
                results.append((position, data, dist))
        return results

    def nearest_neighbor(
        self, query: Tuple[float, float], exclude_data: Any = None
    ) -> Optional[Tuple[Tuple[float, float], Any, float]]:
        """Find nearest neighbor."""
        if self.grid:
            return self.grid.nearest_neighbor(query, exclude_data)

        # Brute force
        best = None
        best_dist = float("inf")
        for position, data in self.points:
            if data == exclude_data:
                continue
            dist = SpatialGrid._distance(query, position)
            if dist < best_dist:
                best = (position, data, dist)
                best_dist = dist
        return best


def build_unit_grid(units, cell_size: float = 5.0) -> SpatialGrid:
    """
    Build a spatial grid from SC2 units.

    Args:
        units: SC2 Units object or list of units
        cell_size: Grid cell size

    Returns:
        SpatialGrid with unit positions
    """
    # Estimate map size from unit positions
    max_x = max_y = 200.0
    for unit in units:
        pos = unit.position
        max_x = max(max_x, pos.x + 10)
        max_y = max(max_y, pos.y + 10)

    grid = SpatialGrid(cell_size, (max_x, max_y))

    for unit in units:
        pos = unit.position
        grid.insert((pos.x, pos.y), unit)

    return grid
