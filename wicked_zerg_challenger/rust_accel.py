# -*- coding: utf-8 -*-
"""Rust acceleration bridge with safe Python fallback."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Any


try:
    from swarm_rust_accel import (
        nearest_point_index as _nearest_point_index_rust,
        compute_feedback_priority as _compute_feedback_priority_rust,
        combat_power_comparison as _combat_power_comparison_rust,
        batch_nearest_points as _batch_nearest_points_rust,
        path_distance as _path_distance_rust,
        route_distance as _route_distance_rust,
        cluster_points as _cluster_points_rust,
        formation_positions as _formation_positions_rust,
    )
except Exception:
    _nearest_point_index_rust = None
    _compute_feedback_priority_rust = None
    _combat_power_comparison_rust = None
    _batch_nearest_points_rust = None
    _path_distance_rust = None
    _route_distance_rust = None
    _cluster_points_rust = None
    _formation_positions_rust = None

try:
    from wicked_zerg_challenger.opencl_accel import (
        nearest_point_index_opencl as _nearest_point_index_opencl,
    )
except Exception:
    try:
        from opencl_accel import (
            nearest_point_index_opencl as _nearest_point_index_opencl,
        )
    except Exception:
        _nearest_point_index_opencl = None


def nearest_point_index(
    origin: Tuple[float, float],
    points: Sequence[Tuple[float, float]],
) -> Optional[int]:
    """Return nearest point index from origin via Rust/OpenCL/CPU fallback."""
    if not points:
        return None

    ox, oy = origin

    if _nearest_point_index_rust is not None:
        try:
            return _nearest_point_index_rust(ox, oy, list(points))
        except Exception:
            pass

    if _nearest_point_index_opencl is not None:
        try:
            return _nearest_point_index_opencl((ox, oy), points)
        except Exception:
            pass

    best_idx = None
    best_dist_sq = float("inf")
    for i, (px, py) in enumerate(points):
        dx = ox - px
        dy = oy - py
        dist_sq = dx * dx + dy * dy
        if dist_sq < best_dist_sq:
            best_dist_sq = dist_sq
            best_idx = i

    return best_idx


def compute_feedback_priority(
    size_kb: float,
    player_count: int,
    winner_count: int,
    note_count: int,
) -> float:
    """Compute replay feedback priority score via Rust."""
    if _compute_feedback_priority_rust is not None:
        try:
            return _compute_feedback_priority_rust(
                size_kb, player_count, winner_count, note_count
            )
        except Exception:
            pass

    score = 1.0
    score += min(size_kb / 1024.0, 1.5)
    score += min(player_count * 0.25, 1.0)
    score += min(winner_count * 0.3, 0.6)
    score -= min(note_count * 0.2, 0.8)
    return max(score, 0.1)


def combat_power_comparison(
    my_units: Sequence[Tuple[float, float, float, float]],
    enemy_units: Sequence[Tuple[float, float, float, float]],
) -> float:
    """Compare combat power: (hp, max_hp, damage, range) for each unit."""
    if _combat_power_comparison_rust is not None:
        try:
            return _combat_power_comparison_rust(list(my_units), list(enemy_units))
        except Exception:
            pass

    def calc_power(units):
        return sum(
            (hp / max_hp if max_hp > 0 else 0) * damage * rng
            for hp, max_hp, damage, rng in units
        )

    my_power = calc_power(my_units)
    enemy_power = calc_power(enemy_units)
    return my_power / enemy_power if enemy_power > 0 else my_power


def batch_nearest_points(
    origins: Sequence[Tuple[float, float]],
    points: Sequence[Tuple[float, float]],
) -> List[Optional[int]]:
    """Find nearest point for multiple origins in parallel (Rust)."""
    if _batch_nearest_points_rust is not None:
        try:
            return _batch_nearest_points_rust(list(origins), list(points))
        except Exception:
            pass

    return [nearest_point_index(o, points) for o in origins]


def path_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate Euclidean distance between two points."""
    if _path_distance_rust is not None:
        try:
            return _path_distance_rust(x1, y1, x2, y2)
        except Exception:
            pass
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def route_distance(steps: Sequence[Tuple[float, float]]) -> float:
    """Calculate total distance along a path."""
    if _route_distance_rust is not None:
        try:
            return _route_distance_rust(list(steps))
        except Exception:
            pass

    if len(steps) < 2:
        return 0.0
    return sum(path_distance(steps[i], steps[i + 1]) for i in range(len(steps) - 1))


def cluster_points(
    points: Sequence[Tuple[float, float]],
    cluster_size: int,
) -> List[List[Tuple[float, float]]]:
    """Cluster points by angular distribution."""
    if _cluster_points_rust is not None:
        try:
            return _cluster_points_rust(list(points), cluster_size)
        except Exception:
            pass

    import math

    if not points or cluster_size <= 0:
        return []

    sorted_points = sorted(points, key=lambda p: math.atan2(p[1], p[0]))
    num_clusters = (len(sorted_points) + cluster_size - 1) // cluster_size
    clusters = [[] for _ in range(num_clusters)]
    for idx, point in enumerate(sorted_points):
        clusters[idx // cluster_size].append(point)
    return clusters


def formation_positions(
    count: int,
    spacing: float = 1.0,
    center_x: float = 0.0,
    center_y: float = 0.0,
    formation_type: str = "line",
) -> List[Tuple[float, float]]:
    """Generate formation positions: line, circle, wedge, grid."""
    if _formation_positions_rust is not None:
        try:
            return _formation_positions_rust(
                count, spacing, center_x, center_y, formation_type
            )
        except Exception:
            pass

    import math

    if count <= 0:
        return []

    if formation_type == "line":
        start_x = center_x - (count - 1) * spacing / 2
        return [(start_x + i * spacing, center_y) for i in range(count)]

    elif formation_type == "circle":
        radius = max(count * spacing / (2 * math.pi), spacing)
        return [
            (
                center_x + radius * math.cos(2 * math.pi * i / count),
                center_y + radius * math.sin(2 * math.pi * i / count),
            )
            for i in range(count)
        ]

    elif formation_type == "wedge":
        positions = []
        row = 0
        idx = 0
        while idx < count:
            units_in_row = row + 1
            start_x = center_x - (units_in_row - 1) * spacing / 2
            for j in range(min(units_in_row, count - idx)):
                positions.append((start_x + j * spacing, center_y - row * spacing))
                idx += 1
            row += 1
        return positions

    elif formation_type == "grid":
        cols = math.ceil(math.sqrt(count))
        start_x = center_x - (cols - 1) * spacing / 2
        start_y = center_y - (count // cols) * spacing / 2
        return [
            (start_x + (i % cols) * spacing, start_y + (i // cols) * spacing)
            for i in range(count)
        ]

    return [(center_x, center_y)] * count


def points_to_xy_tuples(points: Iterable) -> List[Tuple[float, float]]:
    """Convert Point2-like objects into plain (x, y) tuples."""
    return [(float(p.x), float(p.y)) for p in points]


def rust_available() -> Dict[str, bool]:
    """Check which Rust acceleration functions are available."""
    return {
        "nearest_point_index": _nearest_point_index_rust is not None,
        "compute_feedback_priority": _compute_feedback_priority_rust is not None,
        "combat_power_comparison": _combat_power_comparison_rust is not None,
        "batch_nearest_points": _batch_nearest_points_rust is not None,
        "path_distance": _path_distance_rust is not None,
        "route_distance": _route_distance_rust is not None,
        "cluster_points": _cluster_points_rust is not None,
        "formation_positions": _formation_positions_rust is not None,
        "opencl": _nearest_point_index_opencl is not None,
    }
