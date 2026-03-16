# -*- coding: utf-8 -*-
"""
3D K-D Tree for Drone Proximity Queries

SC2 KDTree(2D)를 3D로 확장.
핵심 변경: axis = depth % 2 → axis = depth % 3

Origin: wicked_zerg_challenger/utils/kd_tree.py
"""

from typing import Any, List, Optional, Tuple
import math
import heapq

Pos3 = Tuple[float, float, float]


class KDTree3DNode:
    """3D K-D Tree 노드. 기존 KDTreeNode + z축."""

    __slots__ = ("point", "data", "left", "right", "axis")

    def __init__(
        self,
        point: Pos3,
        data: Any = None,
        left: Optional["KDTree3DNode"] = None,
        right: Optional["KDTree3DNode"] = None,
        axis: int = 0,
    ):
        self.point = point
        self.data = data
        self.left = left
        self.right = right
        self.axis = axis  # 0=x, 1=y, 2=z (기존: 0=x, 1=y)


class KDTree3D:
    """
    3D K-D Tree for efficient spatial queries in drone airspace.

    기존 KDTree와의 차이점:
    - axis = depth % 3 (기존 % 2)
    - distance: sqrt(dx²+dy²+dz²)
    - 나머지 알고리즘은 동일

    Time Complexity:
    - Build: O(N log N)
    - Nearest neighbor: O(log N) average
    - Range query: O(N^(2/3) + k)
    """

    def __init__(self, points: Optional[List[Tuple[Pos3, Any]]] = None):
        self.root: Optional[KDTree3DNode] = None
        self.size = 0
        if points:
            self.build(points)

    def build(self, points: List[Tuple[Pos3, Any]]) -> None:
        if not points:
            self.root = None
            self.size = 0
            return
        self.size = len(points)
        self.root = self._build_recursive(list(points), depth=0)

    def _build_recursive(
        self, points: List[Tuple[Pos3, Any]], depth: int
    ) -> Optional[KDTree3DNode]:
        if not points:
            return None

        axis = depth % 3  # ← 핵심 변경: 2 → 3 (x, y, z 순환)
        points.sort(key=lambda p: p[0][axis])
        mid = len(points) // 2

        point, data = points[mid]
        return KDTree3DNode(
            point=point,
            data=data,
            axis=axis,
            left=self._build_recursive(points[:mid], depth + 1),
            right=self._build_recursive(points[mid + 1:], depth + 1),
        )

    def nearest_neighbor(
        self, query: Pos3, exclude_data: Any = None
    ) -> Optional[Tuple[Pos3, Any, float]]:
        if not self.root:
            return None
        best: List = [None, float("inf")]
        self._nn_recursive(self.root, query, best, exclude_data)
        if best[0] is None:
            return None
        return (best[0].point, best[0].data, best[1])

    def _nn_recursive(
        self, node: Optional[KDTree3DNode], query: Pos3,
        best: List, exclude_data: Any
    ) -> None:
        if node is None:
            return
        dist = self._distance(query, node.point)
        if dist < best[1] and node.data is not exclude_data:
            best[0] = node
            best[1] = dist

        axis = node.axis
        diff = query[axis] - node.point[axis]
        first, second = (node.left, node.right) if diff <= 0 else (node.right, node.left)

        self._nn_recursive(first, query, best, exclude_data)
        if abs(diff) < best[1]:
            self._nn_recursive(second, query, best, exclude_data)

    def range_query(
        self, center: Pos3, radius: float
    ) -> List[Tuple[Pos3, Any, float]]:
        results: List[Tuple[Pos3, Any, float]] = []
        if self.root:
            self._range_recursive(self.root, center, radius, results)
        return results

    def _range_recursive(
        self, node: Optional[KDTree3DNode], center: Pos3,
        radius: float, results: List
    ) -> None:
        if node is None:
            return
        dist = self._distance(center, node.point)
        if dist <= radius:
            results.append((node.point, node.data, dist))

        axis = node.axis
        diff = center[axis] - node.point[axis]
        if diff <= 0:
            self._range_recursive(node.left, center, radius, results)
            if abs(diff) <= radius:
                self._range_recursive(node.right, center, radius, results)
        else:
            self._range_recursive(node.right, center, radius, results)
            if abs(diff) <= radius:
                self._range_recursive(node.left, center, radius, results)

    def k_nearest_neighbors(
        self, query: Pos3, k: int, exclude_data: Any = None
    ) -> List[Tuple[Pos3, Any, float]]:
        if not self.root or k <= 0:
            return []
        heap: List = []
        self._knn_recursive(self.root, query, k, heap, exclude_data)
        results = []
        while heap:
            neg_dist, point, data = heapq.heappop(heap)
            results.append((point, data, -neg_dist))
        results.reverse()
        return results

    def _knn_recursive(
        self, node: Optional[KDTree3DNode], query: Pos3,
        k: int, heap: List, exclude_data: Any
    ) -> None:
        if node is None:
            return
        dist = self._distance(query, node.point)
        if node.data is not exclude_data:
            if len(heap) < k:
                heapq.heappush(heap, (-dist, node.point, node.data))
            elif dist < -heap[0][0]:
                heapq.heapreplace(heap, (-dist, node.point, node.data))

        max_dist = -heap[0][0] if heap else float("inf")
        axis = node.axis
        diff = query[axis] - node.point[axis]
        first, second = (node.left, node.right) if diff <= 0 else (node.right, node.left)

        self._knn_recursive(first, query, k, heap, exclude_data)
        max_dist = -heap[0][0] if len(heap) >= k else float("inf")
        if abs(diff) < max_dist or len(heap) < k:
            self._knn_recursive(second, query, k, heap, exclude_data)

    @staticmethod
    def _distance(p1: Pos3, p2: Pos3) -> float:
        """3D 유클리드 거리."""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        dz = p1[2] - p2[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def __len__(self) -> int:
        return self.size

    def __bool__(self) -> bool:
        return self.root is not None
