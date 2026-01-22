# -*- coding: utf-8 -*-
"""
K-D Tree Implementation for Spatial Optimization

Provides O(N log N) nearest neighbor search instead of O(N^2) brute force.
Used by BoidsController and CombatManager for efficient unit proximity queries.

Features:
- Fast nearest neighbor search
- Range queries for finding units within radius
- Efficient for sparse unit distributions
"""

from typing import List, Optional, Tuple, Any
import math


class KDTreeNode:
    """K-D Tree node for 2D points."""

    def __init__(
        self,
        point: Tuple[float, float],
        data: Any = None,
        left: Optional["KDTreeNode"] = None,
        right: Optional["KDTreeNode"] = None,
        axis: int = 0,
    ):
        self.point = point
        self.data = data  # Associated unit or object
        self.left = left
        self.right = right
        self.axis = axis  # 0 for x, 1 for y


class KDTree:
    """
    2D K-D Tree for efficient spatial queries.

    Time Complexity:
    - Build: O(N log N)
    - Nearest neighbor: O(log N) average, O(N) worst case
    - Range query: O(sqrt(N) + k) where k is result count
    """

    def __init__(self, points: Optional[List[Tuple[Tuple[float, float], Any]]] = None):
        """
        Initialize K-D Tree.

        Args:
            points: List of ((x, y), data) tuples to build tree from
        """
        self.root: Optional[KDTreeNode] = None
        self.size = 0

        if points:
            self.build(points)

    def build(self, points: List[Tuple[Tuple[float, float], Any]]) -> None:
        """
        Build K-D Tree from list of points.

        Args:
            points: List of ((x, y), data) tuples
        """
        if not points:
            self.root = None
            self.size = 0
            return

        self.size = len(points)
        self.root = self._build_recursive(points, depth=0)

    def _build_recursive(
        self, points: List[Tuple[Tuple[float, float], Any]], depth: int
    ) -> Optional[KDTreeNode]:
        """Recursively build K-D Tree."""
        if not points:
            return None

        axis = depth % 2  # Alternate between x (0) and y (1)

        # Sort by current axis and find median
        points.sort(key=lambda p: p[0][axis])
        median_idx = len(points) // 2

        # Create node with median point
        point, data = points[median_idx]
        node = KDTreeNode(
            point=point,
            data=data,
            axis=axis,
            left=self._build_recursive(points[:median_idx], depth + 1),
            right=self._build_recursive(points[median_idx + 1 :], depth + 1),
        )

        return node

    def nearest_neighbor(
        self, query: Tuple[float, float], exclude_data: Any = None
    ) -> Optional[Tuple[Tuple[float, float], Any, float]]:
        """
        Find nearest neighbor to query point.

        Args:
            query: (x, y) query point
            exclude_data: Data to exclude from results (e.g., the querying unit itself)

        Returns:
            ((x, y), data, distance) or None if tree is empty
        """
        if not self.root:
            return None

        best = [None, float("inf")]  # [node, distance]
        self._nearest_neighbor_recursive(self.root, query, best, exclude_data)

        if best[0] is None:
            return None

        return (best[0].point, best[0].data, best[1])

    def _nearest_neighbor_recursive(
        self,
        node: Optional[KDTreeNode],
        query: Tuple[float, float],
        best: List,
        exclude_data: Any,
    ) -> None:
        """Recursively search for nearest neighbor."""
        if node is None:
            return

        # Calculate distance to current node
        dist = self._distance(query, node.point)

        # Update best if this node is closer (and not excluded)
        if dist < best[1] and node.data != exclude_data:
            best[0] = node
            best[1] = dist

        # Determine which subtree to search first
        axis = node.axis
        diff = query[axis] - node.point[axis]

        # Search closer subtree first
        if diff <= 0:
            first, second = node.left, node.right
        else:
            first, second = node.right, node.left

        self._nearest_neighbor_recursive(first, query, best, exclude_data)

        # Check if we need to search the other subtree
        if abs(diff) < best[1]:
            self._nearest_neighbor_recursive(second, query, best, exclude_data)

    def range_query(
        self, center: Tuple[float, float], radius: float
    ) -> List[Tuple[Tuple[float, float], Any, float]]:
        """
        Find all points within radius of center.

        Args:
            center: (x, y) center point
            radius: Search radius

        Returns:
            List of ((x, y), data, distance) tuples
        """
        results = []
        if self.root:
            self._range_query_recursive(self.root, center, radius, results)
        return results

    def _range_query_recursive(
        self,
        node: Optional[KDTreeNode],
        center: Tuple[float, float],
        radius: float,
        results: List,
    ) -> None:
        """Recursively search for points within radius."""
        if node is None:
            return

        # Check if current node is within radius
        dist = self._distance(center, node.point)
        if dist <= radius:
            results.append((node.point, node.data, dist))

        # Determine which subtrees might contain points in range
        axis = node.axis
        diff = center[axis] - node.point[axis]

        # Always search the closer subtree
        if diff <= 0:
            self._range_query_recursive(node.left, center, radius, results)
            # Search other subtree if it might contain points in range
            if abs(diff) <= radius:
                self._range_query_recursive(node.right, center, radius, results)
        else:
            self._range_query_recursive(node.right, center, radius, results)
            if abs(diff) <= radius:
                self._range_query_recursive(node.left, center, radius, results)

    def k_nearest_neighbors(
        self, query: Tuple[float, float], k: int, exclude_data: Any = None
    ) -> List[Tuple[Tuple[float, float], Any, float]]:
        """
        Find k nearest neighbors to query point.

        Args:
            query: (x, y) query point
            k: Number of neighbors to find
            exclude_data: Data to exclude from results

        Returns:
            List of ((x, y), data, distance) tuples, sorted by distance
        """
        if not self.root or k <= 0:
            return []

        # Use a max heap (negative distances) to track k best
        import heapq

        heap = []  # Max heap using negative distances
        self._knn_recursive(self.root, query, k, heap, exclude_data)

        # Convert heap to sorted list
        results = []
        while heap:
            neg_dist, point, data = heapq.heappop(heap)
            results.append((point, data, -neg_dist))

        results.reverse()  # Sort by increasing distance
        return results

    def _knn_recursive(
        self,
        node: Optional[KDTreeNode],
        query: Tuple[float, float],
        k: int,
        heap: List,
        exclude_data: Any,
    ) -> None:
        """Recursively search for k nearest neighbors."""
        import heapq

        if node is None:
            return

        dist = self._distance(query, node.point)

        # Add to heap if not excluded
        if node.data != exclude_data:
            if len(heap) < k:
                heapq.heappush(heap, (-dist, node.point, node.data))
            elif dist < -heap[0][0]:
                heapq.heapreplace(heap, (-dist, node.point, node.data))

        # Get current max distance in heap
        max_dist = -heap[0][0] if heap else float("inf")

        # Determine which subtree to search first
        axis = node.axis
        diff = query[axis] - node.point[axis]

        if diff <= 0:
            first, second = node.left, node.right
        else:
            first, second = node.right, node.left

        self._knn_recursive(first, query, k, heap, exclude_data)

        # Update max_dist after searching first subtree
        max_dist = -heap[0][0] if len(heap) >= k else float("inf")

        # Check if we need to search the other subtree
        if abs(diff) < max_dist or len(heap) < k:
            self._knn_recursive(second, query, k, heap, exclude_data)

    @staticmethod
    def _distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points."""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        return math.sqrt(dx * dx + dy * dy)

    def __len__(self) -> int:
        return self.size

    def __bool__(self) -> bool:
        return self.root is not None


def build_unit_kdtree(units) -> KDTree:
    """
    Build a K-D Tree from SC2 units.

    Args:
        units: SC2 Units object or list of units

    Returns:
        KDTree with unit positions and unit references
    """
    points = []
    for unit in units:
        pos = unit.position
        points.append(((pos.x, pos.y), unit))

    return KDTree(points)
