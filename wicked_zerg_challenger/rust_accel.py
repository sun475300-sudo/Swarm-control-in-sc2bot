# -*- coding: utf-8 -*-
"""Rust acceleration bridge with safe Python fallback."""

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple


try:
    # Optional extension built from rust_accel/Cargo.toml
    from swarm_rust_accel import nearest_point_index as _nearest_point_index_rust
except Exception:
    _nearest_point_index_rust = None

try:
    from wicked_zerg_challenger.opencl_accel import nearest_point_index_opencl as _nearest_point_index_opencl
except Exception:
    try:
        from opencl_accel import nearest_point_index_opencl as _nearest_point_index_opencl
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


def points_to_xy_tuples(points: Iterable) -> list[Tuple[float, float]]:
    """Convert Point2-like objects into plain (x, y) tuples."""
    return [(float(p.x), float(p.y)) for p in points]
