# -*- coding: utf-8 -*-
"""Rust acceleration bridge with safe Python fallback."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from swarm_rust_accel import batch_nearest_points as _batch_nearest_points_rust
    from swarm_rust_accel import calculate_retreat_path as _calculate_retreat_path_rust
    from swarm_rust_accel import cluster_points as _cluster_points_rust
    from swarm_rust_accel import (
        combat_power_comparison as _combat_power_comparison_rust,
    )
    from swarm_rust_accel import (
        compute_feedback_priority as _compute_feedback_priority_rust,
    )
    from swarm_rust_accel import formation_positions as _formation_positions_rust
    from swarm_rust_accel import find_unit_clusters as _find_unit_clusters_rust
    from swarm_rust_accel import nearest_point_index as _nearest_point_index_rust
    from swarm_rust_accel import path_distance as _path_distance_rust
    from swarm_rust_accel import route_distance as _route_distance_rust
    from swarm_rust_accel import threat_assessment as _threat_assessment_rust
except Exception:
    _nearest_point_index_rust = None
    _compute_feedback_priority_rust = None
    _combat_power_comparison_rust = None
    _batch_nearest_points_rust = None
    _path_distance_rust = None
    _route_distance_rust = None
    _cluster_points_rust = None
    _formation_positions_rust = None
    _find_unit_clusters_rust = None
    _threat_assessment_rust = None
    _calculate_retreat_path_rust = None

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


def find_unit_clusters(
    positions: Sequence[Tuple[float, float]],
    radius: float,
    min_count: int,
) -> List[Tuple[float, float, int]]:
    """Find dense unit clusters via Rust or deterministic CPU fallback."""
    if _find_unit_clusters_rust is not None:
        try:
            return _find_unit_clusters_rust(list(positions), float(radius), int(min_count))
        except Exception:
            pass

    clusters: List[Tuple[float, float, int]] = []
    radius_sq = float(radius) * float(radius)
    for x, y in positions:
        count = 0
        for px, py in positions:
            dx = px - x
            dy = py - y
            if dx * dx + dy * dy <= radius_sq:
                count += 1
        if count >= min_count:
            clusters.append((float(x), float(y), int(count)))
    clusters.sort(key=lambda item: item[2], reverse=True)
    return clusters


def threat_assessment(
    enemy_data: Sequence[Tuple[float, float, float, float, float]],
    base_position: Tuple[float, float],
    max_distance: float,
) -> float:
    """Score nearby enemy threat using HP, DPS, range, and proximity."""
    if _threat_assessment_rust is not None:
        try:
            return float(
                _threat_assessment_rust(
                    list(enemy_data), tuple(base_position), float(max_distance)
                )
            )
        except Exception:
            pass

    bx, by = base_position
    max_distance = max(float(max_distance), 1e-6)
    score = 0.0
    for x, y, hp, dps, attack_range in enemy_data:
        dx = float(x) - bx
        dy = float(y) - by
        distance = (dx * dx + dy * dy) ** 0.5
        if distance <= max_distance:
            proximity = 1.0 - (distance / max_distance)
            score += max(0.0, hp) * max(0.0, dps) * proximity * (max(attack_range, 1.0) / 6.0)
    return score


def calculate_retreat_path(
    unit_pos: Tuple[float, float],
    base_positions: Sequence[Tuple[float, float]],
    creep_positions: Sequence[Tuple[float, float]] = (),
    spine_positions: Sequence[Tuple[float, float]] = (),
) -> Tuple[float, float]:
    """Choose the safest known retreat anchor with creep/spine bonuses."""
    if not base_positions:
        return tuple(unit_pos)

    if _calculate_retreat_path_rust is not None:
        try:
            return tuple(
                _calculate_retreat_path_rust(
                    tuple(unit_pos),
                    list(base_positions),
                    list(creep_positions),
                    list(spine_positions),
                )
            )
        except Exception:
            pass

    ux, uy = unit_pos
    best_pos = tuple(base_positions[0])
    best_score = float("-inf")
    for bx, by in base_positions:
        distance = ((bx - ux) ** 2 + (by - uy) ** 2) ** 0.5
        score = -distance
        for cx, cy in creep_positions:
            if ((cx - bx) ** 2 + (cy - by) ** 2) ** 0.5 < 5.0:
                score += 10.0
        for sx, sy in spine_positions:
            if ((sx - bx) ** 2 + (sy - by) ** 2) ** 0.5 < 8.0:
                score += 20.0
        if score > best_score:
            best_score = score
            best_pos = (float(bx), float(by))
    return best_pos


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
        "find_unit_clusters": _find_unit_clusters_rust is not None,
        "threat_assessment": _threat_assessment_rust is not None,
        "calculate_retreat_path": _calculate_retreat_path_rust is not None,
        "opencl": _nearest_point_index_opencl is not None,
    }
