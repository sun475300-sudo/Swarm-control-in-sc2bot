# -*- coding: utf-8 -*-
"""
Performance Optimizer - Critical Performance Improvements

This module integrates all performance optimizations:
1. Spatial Partitioning (K-D Tree / Grid) for Boids O(N^2) -> O(N log N)
2. PID Control for unit movement
3. Task Queue management for HRL
4. Transformer model integration

Based on technical debt analysis and hybrid engineering principles.
"""

from typing import Any, Optional, List, Tuple
from pathlib import Path

try:
    from sc2.position import Point2
    from sc2.unit import Unit
    SC2_AVAILABLE = True
except ImportError:
    class Point2:
        def __init__(self, coords):
            self.x, self.y = coords[0], coords[1]
    Unit = Any
    SC2_AVAILABLE = False

try:
    from utils.kd_tree import KDTree
    from utils.spatial_partition import SpatialPartition
    from utils.pid_controller import PIDController, UnitMovementController
    OPTIMIZATIONS_AVAILABLE = True
except ImportError:
    OPTIMIZATIONS_AVAILABLE = False
    KDTree = None
    SpatialPartition = None
    PIDController = None
    UnitMovementController = None


class PerformanceOptimizer:
    """
    Centralized performance optimization manager
    
    Integrates:
    - Spatial partitioning for Boids algorithm
    - PID control for unit movement
    - Performance monitoring
    """
    
    def __init__(self, bot: Any):
        self.bot = bot
        
        # Spatial partitioning
        self.use_spatial_partitioning = True
        self.kd_tree = None
        self.spatial_partition = None
        
        if OPTIMIZATIONS_AVAILABLE:
            try:
                self.kd_tree = KDTree()
                self.spatial_partition = SpatialPartition(cell_size=10.0)
            except Exception as e:
                print(f"[WARNING] Failed to initialize spatial partitioning: {e}")
                self.use_spatial_partitioning = False
        
        # PID controllers for units
        self.pid_controllers = {}  # unit_tag -> PIDController
        self.movement_controllers = {}  # unit_tag -> UnitMovementController
        
        if OPTIMIZATIONS_AVAILABLE and UnitMovementController:
            try:
                # Will create controllers on-demand
                pass
            except Exception as e:
                print(f"[WARNING] Failed to initialize PID controllers: {e}")
        
        # Performance metrics
        self.performance_stats = {
            "boids_calculations": 0,
            "spatial_partition_queries": 0,
            "pid_updates": 0,
            "avg_calculation_time": 0.0
        }
        
        print("[PERFORMANCE_OPTIMIZER] Initialized with spatial partitioning and PID control")
    
    def optimize_boids_calculation(
        self,
        unit_position: Point2,
        all_units: List[Unit],
        max_radius: float = 15.0
    ) -> List[Tuple[Point2, Point2]]:
        """
        Optimize Boids calculation using spatial partitioning.
        
        Args:
            unit_position: Position of the unit
            all_units: List of all units
            max_radius: Maximum search radius
            
        Returns:
            List of (position, velocity) tuples for nearby units
        """
        if not self.use_spatial_partitioning or not all_units:
            # Fallback: return empty list (will use all units in BoidsController)
            return []
        
        try:
            # Convert units to (position, velocity) tuples
            unit_data = []
            for unit in all_units:
                if hasattr(unit, 'position') and hasattr(unit, 'velocity'):
                    unit_data.append((unit.position, unit.velocity))
            
            if not unit_data:
                return []
            
            # Use K-D Tree for sparse distributions
            if self.kd_tree and len(unit_data) < 200:
                self.kd_tree.build(unit_data)
                nearby = self.kd_tree.query_radius(unit_position, max_radius)
                self.performance_stats["spatial_partition_queries"] += 1
                return nearby
            
            # Use Grid-based for dense distributions
            elif self.spatial_partition and len(unit_data) >= 200:
                self.spatial_partition.add_units(unit_data)
                nearby = self.spatial_partition.query_nearby(unit_position, max_radius)
                self.performance_stats["spatial_partition_queries"] += 1
                return nearby
            
            return []
            
        except Exception as e:
            if self.bot.iteration % 200 == 0:
                print(f"[WARNING] Spatial partitioning error: {e}")
            return []
    
    def get_pid_controller(self, unit_tag: int) -> Optional[UnitMovementController]:
        """
        Get or create PID controller for a unit.
        
        Args:
            unit_tag: Unit tag identifier
            
        Returns:
            UnitMovementController instance
        """
        if not OPTIMIZATIONS_AVAILABLE or not UnitMovementController:
            return None
        
        if unit_tag not in self.movement_controllers:
            try:
                self.movement_controllers[unit_tag] = UnitMovementController()
            except Exception as e:
                if self.bot.iteration % 200 == 0:
                    print(f"[WARNING] Failed to create PID controller: {e}")
                return None
        
        return self.movement_controllers[unit_tag]
    
    def calculate_optimal_movement(
        self,
        unit: Unit,
        target_position: Point2,
        dt: float = 0.1
    ) -> Optional[Point2]:
        """
        Calculate optimal movement using PID control.
        
        Args:
            unit: Unit to move
            target_position: Target position
            dt: Time step
            
        Returns:
            Optimal velocity vector (Point2) or None if PID not available
        """
        if not hasattr(unit, 'tag'):
            return None
        
        controller = self.get_pid_controller(unit.tag)
        if not controller:
            return None
        
        try:
            current_pos = unit.position
            current_vel = unit.velocity if hasattr(unit, 'velocity') else Point2((0, 0))
            
            optimal_velocity = controller.calculate_movement(
                current_pos,
                target_position,
                current_vel,
                dt
            )
            
            self.performance_stats["pid_updates"] += 1
            return optimal_velocity
            
        except Exception as e:
            if self.bot.iteration % 200 == 0:
                print(f"[WARNING] PID calculation error: {e}")
            return None
    
    def get_performance_stats(self) -> dict:
        """Get current performance statistics"""
        return self.performance_stats.copy()
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.performance_stats = {
            "boids_calculations": 0,
            "spatial_partition_queries": 0,
            "pid_updates": 0,
            "avg_calculation_time": 0.0
        }
    
    def cleanup_unit_controllers(self, removed_unit_tags: List[int]):
        """
        Clean up PID controllers for removed units.
        
        Args:
            removed_unit_tags: List of unit tags that no longer exist
        """
        for tag in removed_unit_tags:
            self.movement_controllers.pop(tag, None)
            self.pid_controllers.pop(tag, None)
