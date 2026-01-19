# -*- coding: utf-8 -*-
"""
Spatial Partitioning for O(N^2) Optimization

This module implements spatial partitioning (grid-based) to optimize
distance calculations in Boids algorithm and other unit coordination tasks.

Instead of checking all units against all units (O(N^2)),
we only check units in nearby grid cells (O(N)).

Performance improvement:
- O(N^2) -> O(N) for large swarms (100+ units)
- Maintains constant frame time even with 200+ units
"""

import math
from typing import List, Dict, Tuple, Set
from collections import defaultdict

try:
    from sc2.position import Point2
    SC2_AVAILABLE = True
except ImportError:
    # Mock for testing
    class Point2:
        def __init__(self, coords):
            self.x, self.y = coords[0], coords[1]
        def distance_to_squared(self, other):
            dx = self.x - other.x
            dy = self.y - other.y
            return dx*dx + dy*dy
    SC2_AVAILABLE = False


class SpatialGrid:
    """
    Grid-based spatial partitioning for efficient neighbor queries.
    
    Divides the map into a grid of cells. Each unit is placed in a cell
    based on its position. Neighbor queries only check units in nearby cells.
    
    Complexity: O(1) insertion, O(K) neighbor query (K = units in nearby cells)
    """
    
    def __init__(self, cell_size: float = 5.0):
        """
        Initialize spatial grid.
        
        Args:
            cell_size: Size of each grid cell (default: 5.0, optimal for Boids)
        """
        self.cell_size = cell_size
        self.grid: Dict[Tuple[int, int], List[Tuple[Point2, Point2]]] = defaultdict(list)
        self._hash_map: Dict[int, Tuple[int, int]] = {}  # unit_id -> (grid_x, grid_y)
    
    def _get_cell_coords(self, position: Point2) -> Tuple[int, int]:
        """Convert position to grid cell coordinates."""
        grid_x = int(position.x / self.cell_size)
        grid_y = int(position.y / self.cell_size)
        return (grid_x, grid_y)
    
    def clear(self):
        """Clear all units from the grid."""
        self.grid.clear()
        self._hash_map.clear()
    
    def add_unit(self, unit_id: int, position: Point2, velocity: Point2 = None):
        """
        Add a unit to the spatial grid.
        
        Args:
            unit_id: Unique identifier for the unit
            position: Unit position (Point2)
            velocity: Unit velocity (Point2, optional)
        """
        cell = self._get_cell_coords(position)
        velocity = velocity or Point2((0.0, 0.0))
        
        # Remove from old cell if exists
        if unit_id in self._hash_map:
            old_cell = self._hash_map[unit_id]
            if old_cell in self.grid:
                self.grid[old_cell] = [
                    (pos, vel) for (pos, vel) in self.grid[old_cell]
                    if id(pos) != unit_id  # Remove by position object identity
                ]
        
        # Add to new cell
        self.grid[cell].append((position, velocity))
        self._hash_map[unit_id] = cell
    
    def get_nearby_units(
        self,
        position: Point2,
        radius: float
    ) -> List[Tuple[Point2, Point2]]:
        """
        Get all units within radius of the given position.
        
        Only checks units in nearby grid cells, dramatically reducing
        computation compared to checking all units.
        
        Args:
            position: Center position
            radius: Search radius
            
        Returns:
            List of (position, velocity) tuples for nearby units
        """
        nearby_units = []
        radius_squared = radius * radius
        
        # Calculate which grid cells to check
        # We need to check cells in a radius around the position
        cells_to_check = self._get_cells_in_radius(position, radius)
        
        # Check each cell
        for cell in cells_to_check:
            if cell in self.grid:
                for unit_pos, unit_vel in self.grid[cell]:
                    # Check if actually within radius (grid cells may contain units outside)
                    if hasattr(unit_pos, 'distance_to_squared'):
                        dist_sq = unit_pos.distance_to_squared(position)
                    else:
                        dx = unit_pos.x - position.x
                        dy = unit_pos.y - position.y
                        dist_sq = dx*dx + dy*dy
                    
                    if dist_sq <= radius_squared and dist_sq > 0:  # Exclude self
                        nearby_units.append((unit_pos, unit_vel))
        
        return nearby_units
    
    def _get_cells_in_radius(self, position: Point2, radius: float) -> Set[Tuple[int, int]]:
        """Get set of grid cells that intersect with the search radius."""
        cells = set()
        
        # Calculate bounding box
        min_x = position.x - radius
        max_x = position.x + radius
        min_y = position.y - radius
        max_y = position.y + radius
        
        # Convert to grid coordinates
        min_grid_x = int(min_x / self.cell_size)
        max_grid_x = int(max_x / self.cell_size)
        min_grid_y = int(min_y / self.cell_size)
        max_grid_y = int(max_y / self.cell_size)
        
        # Add all cells in bounding box
        for grid_x in range(min_grid_x, max_grid_x + 1):
            for grid_y in range(min_grid_y, max_grid_y + 1):
                cells.add((grid_x, grid_y))
        
        return cells
    
    def get_all_units(self) -> List[Tuple[Point2, Point2]]:
        """Get all units in the grid (for debugging/testing)."""
        all_units = []
        for cell_units in self.grid.values():
            all_units.extend(cell_units)
        return all_units


class OptimizedSpatialPartition:
    """
    High-level interface for spatial partitioning optimization.
    
    Usage:
        partition = OptimizedSpatialPartition(cell_size=5.0)
        partition.add_units(units)  # units: List[Tuple[position, velocity]]
        nearby = partition.query_nearby(position, radius=10.0)
    """
    
    def __init__(self, cell_size: float = 5.0):
        """
        Initialize optimized spatial partition.
        
        Args:
            cell_size: Grid cell size (5.0 works well for Boids with radius ~10.0)
        """
        self.grid = SpatialGrid(cell_size)
        self._unit_counter = 0
    
    def add_units(self, units: List[Tuple[Point2, Point2]]):
        """
        Add multiple units to the partition.
        
        Args:
            units: List of (position, velocity) tuples
        """
        self.grid.clear()
        self._unit_counter = 0
        
        for position, velocity in units:
            self.grid.add_unit(self._unit_counter, position, velocity)
            self._unit_counter += 1
    
    def query_nearby(
        self,
        position: Point2,
        radius: float
    ) -> List[Tuple[Point2, Point2]]:
        """
        Query for nearby units efficiently.
        
        Args:
            position: Center position
            radius: Search radius
            
        Returns:
            List of (position, velocity) tuples within radius
        """
        return self.grid.get_nearby_units(position, radius)
    
    def clear(self):
        """Clear all units from the partition."""
        self.grid.clear()
        self._unit_counter = 0
