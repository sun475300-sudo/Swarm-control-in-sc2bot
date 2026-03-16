# -*- coding: utf-8 -*-
"""
3D Voxel Grid — Spatial Partition for Drone Airspace

SC2 SpatialGrid(2D)를 3D 복셀 공간으로 확장.
셀 키: (cell_x, cell_y) → (cell_x, cell_y, cell_z)

Origin: wicked_zerg_challenger/utils/spatial_partition.py
"""

from typing import Any, Dict, List, Optional, Tuple
import math

# Type alias: 3D 좌표 튜플
Pos3 = Tuple[float, float, float]
Cell3 = Tuple[int, int, int]


class VoxelGrid:
    """
    3D Grid-based spatial partitioning for drone airspace management.

    SC2 SpatialGrid의 3D 확장:
    - 2D 셀 (cell_x, cell_y) → 3D 복셀 (cell_x, cell_y, cell_z)
    - 2D 원 범위 검색 → 3D 구 범위 검색
    - 2D 유클리드 거리 → 3D 유클리드 거리

    Time Complexity:
    - Insert: O(1)
    - Query neighbors: O(k) where k is drones in nearby voxels
    - Range query: O(voxels_checked × drones_per_voxel)
    """

    def __init__(
        self,
        cell_size: float = 10.0,
        map_size: Tuple[float, float, float] = (1000.0, 1000.0, 120.0),
    ):
        """
        Args:
            cell_size: 복셀 한 변의 크기 (미터). SC2의 5.0 → 드론 10.0m
            map_size: (width, depth, max_altitude) 공역 크기 (미터)
        """
        self.cell_size = max(cell_size, 0.001)
        self.map_width = map_size[0]
        self.map_depth = map_size[1]
        self.map_altitude = map_size[2]

        self.grid_w = int(math.ceil(self.map_width / self.cell_size))
        self.grid_d = int(math.ceil(self.map_depth / self.cell_size))
        self.grid_h = int(math.ceil(self.map_altitude / self.cell_size))

        # 3D 복셀 저장소: (cx, cy, cz) → [(position, data), ...]
        self.grid: Dict[Cell3, List[Tuple[Pos3, Any]]] = {}
        self.data_to_cell: Dict[int, Cell3] = {}
        self.size = 0

    def clear(self) -> None:
        self.grid.clear()
        self.data_to_cell.clear()
        self.size = 0

    def _get_cell(self, x: float, y: float, z: float) -> Cell3:
        """연속 좌표 → 이산 복셀 인덱스. 기존 2D _get_cell + z축."""
        s = self.cell_size
        cx = max(0, min(int(x / s), self.grid_w - 1))
        cy = max(0, min(int(y / s), self.grid_d - 1))
        cz = max(0, min(int(z / s), self.grid_h - 1))
        return (cx, cy, cz)

    def insert(self, position: Pos3, data: Any) -> None:
        """3D 좌표 삽입. 기존 SpatialGrid.insert()와 동일 구조."""
        cell = self._get_cell(position[0], position[1], position[2])
        if cell not in self.grid:
            self.grid[cell] = []
        self.grid[cell].append((position, data))
        self.data_to_cell[id(data)] = cell
        self.size += 1

    def remove(self, data: Any) -> bool:
        """데이터 제거. 기존 SpatialGrid.remove() 동일."""
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

    def update(self, position: Pos3, data: Any) -> None:
        self.remove(data)
        self.insert(position, data)

    def query_radius(
        self, center: Pos3, radius: float, exclude_data: Any = None
    ) -> List[Tuple[Pos3, Any, float]]:
        """
        3D 구 범위 검색. 기존 2D 원 검색의 3D 확장.

        기존: dx, dy 2중 루프 → 변경: dx, dy, dz 3중 루프
        """
        results = []
        cells_to_check = int(math.ceil(radius / self.cell_size)) + 1
        cc = self._get_cell(center[0], center[1], center[2])

        for dx in range(-cells_to_check, cells_to_check + 1):
            for dy in range(-cells_to_check, cells_to_check + 1):
                for dz in range(-cells_to_check, cells_to_check + 1):
                    cell = (cc[0] + dx, cc[1] + dy, cc[2] + dz)
                    if cell not in self.grid:
                        continue
                    for position, data in self.grid[cell]:
                        if data is exclude_data:
                            continue
                        dist = self._distance(center, position)
                        if dist <= radius:
                            results.append((position, data, dist))
        return results

    def query_altitude_layer(
        self, z_min: float, z_max: float
    ) -> List[Tuple[Pos3, Any]]:
        """특정 고도층의 모든 드론 검색 (UTM 신규 기능)."""
        results = []
        cz_min = max(0, int(z_min / self.cell_size))
        cz_max = min(self.grid_h - 1, int(z_max / self.cell_size))
        for cell, entries in self.grid.items():
            if cz_min <= cell[2] <= cz_max:
                results.extend(entries)
        return results

    def nearest_neighbor(
        self, query: Pos3, exclude_data: Any = None
    ) -> Optional[Tuple[Pos3, Any, float]]:
        """최근접 이웃 검색. 기존 SpatialGrid 확장 탐색 패턴."""
        max_dim = max(self.grid_w, self.grid_d, self.grid_h)
        for mult in range(1, max_dim + 1):
            results = self.query_radius(query, self.cell_size * mult, exclude_data)
            if results:
                results.sort(key=lambda r: r[2])
                return results[0]
        return None

    def k_nearest_neighbors(
        self, query: Pos3, k: int, exclude_data: Any = None
    ) -> List[Tuple[Pos3, Any, float]]:
        """k-최근접 이웃. 기존 SpatialGrid 패턴."""
        max_dim = max(self.grid_w, self.grid_d, self.grid_h)
        for mult in range(1, max_dim + 1):
            results = self.query_radius(query, self.cell_size * mult, exclude_data)
            if len(results) >= k:
                results.sort(key=lambda r: r[2])
                return results[:k]
        results.sort(key=lambda r: r[2])
        return results

    def get_density(self, center: Pos3, radius: float) -> int:
        """반경 내 드론 밀도 (UTM 혼잡도 지표)."""
        return len(self.query_radius(center, radius))

    @staticmethod
    def _distance(p1: Pos3, p2: Pos3) -> float:
        """3D 유클리드 거리. 기존 sqrt(dx²+dy²) → sqrt(dx²+dy²+dz²)"""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        dz = p1[2] - p2[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def __len__(self) -> int:
        return self.size

    def __bool__(self) -> bool:
        return self.size > 0
