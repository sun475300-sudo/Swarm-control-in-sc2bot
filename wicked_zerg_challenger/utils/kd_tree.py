# -*- coding: utf-8 -*-
"""
K-D Tree for Spatial Partitioning (Advanced)

K-D Tree provides O(log N) nearest neighbor queries,
better than grid-based partitioning for sparse distributions.

Used for Boids algorithm optimization when units are spread out.
"""

import math
from typing import List, Tuple, Optional, Any
from dataclasses import dataclass

try:
    from sc2.position import Point2
    SC2_AVAILABLE = True
except ImportError:
    class Point2:
        def __init__(self, coords):
            self.x, self.y = coords[0], coords[1]
        def distance_to_squared(self, other):
            dx = self.x - other.x
            dy = self.y - other.y
            return dx*dx + dy*dy
    SC2_AVAILABLE = False


@dataclass
class KDNode:
    """K-D Tree node"""
    point: Point2
    velocity: Point2
    left: Optional['KDNode'] = None
    right: Optional['KDNode'] = None
    axis: int = 0  # 0 = x-axis, 1 = y-axis


class KDTree:
    """
    K-D Tree for efficient spatial queries.
    
    Complexity:
    - Build: O(N log N)
    - Query: O(log N) average, O(N) worst case
    - Better than grid for sparse distributions
    """
    
    def __init__(self, points: List[Tuple[Point2, Point2]] = None):
        """
        Initialize K-D Tree.
        
        Args:
            points: List of (position, velocity) tuples
        """
        self.root = None
        if points:
            self.build(points)
    
    def build(self, points: List[Tuple[Point2, Point2]]):
        """
        Build K-D Tree from points.
        
        Args:
            points: List of (position, velocity) tuples
        """
        if not points:
            return
        
        self.root = self._build_recursive(points, depth=0)
    
    def _build_recursive(
        self,
        points: List[Tuple[Point2, Point2]],
        depth: int
    ) -> Optional[KDNode]:
        """Recursively build K-D Tree."""
        if not points:
            return None
        
        # Alternate between x and y axis
        axis = depth % 2
        
        # Sort by current axis
        sorted_points = sorted(points, key=lambda p: p[0].x if axis == 0 else p[0].y)
        
        # Median point
        median_idx = len(sorted_points) // 2
        median_point, median_velocity = sorted_points[median_idx]
        
        # Create node
        node = KDNode(
            point=median_point,
            velocity=median_velocity,
            axis=axis
        )
        
        # Recursively build left and right subtrees
        node.left = self._build_recursive(
            sorted_points[:median_idx],
            depth + 1
        )
        node.right = self._build_recursive(
            sorted_points[median_idx + 1:],
            depth + 1
        )
        
        return node
    
    def query_radius(
        self,
        center: Point2,
        radius: float
    ) -> List[Tuple[Point2, Point2]]:
        """
        Query all points within radius of center.
        
        Args:
            center: Center position
            radius: Search radius
            
        Returns:
            List of (position, velocity) tuples within radius
        """
        results = []
        radius_squared = radius * radius
        
        if self.root:
            self._query_recursive(
                self.root,
                center,
                radius_squared,
                results,
                depth=0
            )
        
        return results
    
    def _query_recursive(
        self,
        node: KDNode,
        center: Point2,
        radius_squared: float,
        results: List[Tuple[Point2, Point2]],
        depth: int
    ):
        """Recursively query K-D Tree."""
        if node is None:
            return
        
        # Calculate distance
        dx = node.point.x - center.x
        dy = node.point.y - center.y
        dist_squared = dx*dx + dy*dy
        
        # If within radius, add to results
        if dist_squared <= radius_squared and dist_squared > 0:
            results.append((node.point, node.velocity))
        
        # Determine which side to search
        axis = depth % 2
        if axis == 0:  # x-axis
            axis_dist = node.point.x - center.x
        else:  # y-axis
            axis_dist = node.point.y - center.y
        
        # Search closer side first
        if axis_dist > 0:
            self._query_recursive(node.left, center, radius_squared, results, depth + 1)
            # Check if we need to search other side
            if axis_dist * axis_dist <= radius_squared:
                self._query_recursive(node.right, center, radius_squared, results, depth + 1)
        else:
            self._query_recursive(node.right, center, radius_squared, results, depth + 1)
            # Check if we need to search other side
            if axis_dist * axis_dist <= radius_squared:
                self._query_recursive(node.left, center, radius_squared, results, depth + 1)
    
    def clear(self):
        """Clear the tree."""
        self.root = None
