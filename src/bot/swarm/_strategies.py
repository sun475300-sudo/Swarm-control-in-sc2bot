"""Pure strategy primitives used by the 30 ``BehaviorNN`` modules.

Every function takes a list of 2D points (and optional parameters) and returns
a new list of 2D points the same length as the input. They are deterministic
unless an explicit ``seed`` is supplied for jitter-based strategies.
"""

from __future__ import annotations

import math
import random
from typing import Iterable, List, Optional, Sequence, Tuple

Point = Tuple[float, float]


def _coerce(points: Iterable) -> List[Point]:
    return [(float(x), float(y)) for x, y in points]


def _centroid(points: Sequence[Point]) -> Point:
    if not points:
        return (0.0, 0.0)
    sx = sum(p[0] for p in points)
    sy = sum(p[1] for p in points)
    return (sx / len(points), sy / len(points))


def cohere(points: Iterable, factor: float = 0.25) -> List[Point]:
    """Pull each point ``factor`` fraction toward the centroid."""
    pts = _coerce(points)
    if not pts:
        return []
    cx, cy = _centroid(pts)
    return [(x + (cx - x) * factor, y + (cy - y) * factor) for x, y in pts]


def scatter(points: Iterable, factor: float = 0.25) -> List[Point]:
    """Push each point ``factor`` fraction away from the centroid."""
    pts = _coerce(points)
    if not pts:
        return []
    cx, cy = _centroid(pts)
    return [(x + (x - cx) * factor, y + (y - cy) * factor) for x, y in pts]


def hold(points: Iterable) -> List[Point]:
    """Return positions unchanged (identity strategy)."""
    return _coerce(points)


def attack_move(points: Iterable, target: Point, step: float = 1.0) -> List[Point]:
    """Move each point ``step`` units toward ``target`` (capped at the target)."""
    pts = _coerce(points)
    tx, ty = target
    out: List[Point] = []
    for x, y in pts:
        dx, dy = tx - x, ty - y
        dist = math.hypot(dx, dy)
        if dist <= step or dist == 0.0:
            out.append((tx, ty))
        else:
            out.append((x + dx / dist * step, y + dy / dist * step))
    return out


def retreat(points: Iterable, threat: Point, step: float = 1.0) -> List[Point]:
    """Move each point ``step`` units away from ``threat``."""
    pts = _coerce(points)
    tx, ty = threat
    out: List[Point] = []
    for x, y in pts:
        dx, dy = x - tx, y - ty
        dist = math.hypot(dx, dy)
        if dist == 0.0:
            out.append((x + step, y))
        else:
            out.append((x + dx / dist * step, y + dy / dist * step))
    return out


def circle_target(points: Iterable, target: Point, radius: float = 5.0) -> List[Point]:
    """Place points evenly on a circle of ``radius`` around ``target``."""
    pts = _coerce(points)
    n = len(pts)
    if n == 0:
        return []
    cx, cy = target
    return [
        (
            cx + radius * math.cos(2 * math.pi * i / n),
            cy + radius * math.sin(2 * math.pi * i / n),
        )
        for i in range(n)
    ]


def line_formation(
    points: Iterable, origin: Point, spacing: float = 1.0, axis: str = "x"
) -> List[Point]:
    """Align points along a line through ``origin`` on the given axis."""
    pts = _coerce(points)
    n = len(pts)
    if n == 0:
        return []
    half = (n - 1) / 2.0
    if axis == "x":
        return [(origin[0] + (i - half) * spacing, origin[1]) for i in range(n)]
    return [(origin[0], origin[1] + (i - half) * spacing) for i in range(n)]


def wedge(
    points: Iterable, tip: Point, target: Point, spacing: float = 1.0
) -> List[Point]:
    """Form a V wedge with the apex at ``tip`` pointing toward ``target``."""
    pts = _coerce(points)
    n = len(pts)
    if n == 0:
        return []
    dx, dy = target[0] - tip[0], target[1] - tip[1]
    norm = math.hypot(dx, dy) or 1.0
    fx, fy = dx / norm, dy / norm
    # Perpendicular vector (rotate 90deg).
    px, py = -fy, fx
    out: List[Point] = []
    for i in range(n):
        side = -1 if i % 2 == 0 else 1
        offset = (i // 2 + 1) * spacing
        if i == 0:
            out.append(tip)
        else:
            ox = tip[0] - fx * offset + px * side * offset
            oy = tip[1] - fy * offset + py * side * offset
            out.append((ox, oy))
    return out


def box_formation(points: Iterable, origin: Point, spacing: float = 1.0) -> List[Point]:
    """Pack points into a square-ish grid centered on ``origin``."""
    pts = _coerce(points)
    n = len(pts)
    if n == 0:
        return []
    cols = max(1, int(math.ceil(math.sqrt(n))))
    out: List[Point] = []
    half = (cols - 1) / 2.0
    for i in range(n):
        r, c = divmod(i, cols)
        out.append((origin[0] + (c - half) * spacing, origin[1] + (r - half) * spacing))
    return out


def spread(
    points: Iterable, min_distance: float = 2.0, iterations: int = 5
) -> List[Point]:
    """Iteratively push points apart so none are closer than ``min_distance``."""
    pts = _coerce(points)
    for _ in range(iterations):
        moved = list(pts)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                ax, ay = moved[i]
                bx, by = moved[j]
                dx, dy = bx - ax, by - ay
                dist = math.hypot(dx, dy)
                if dist == 0.0:
                    moved[i] = (ax - min_distance / 2, ay)
                    moved[j] = (bx + min_distance / 2, by)
                elif dist < min_distance:
                    push = (min_distance - dist) / 2.0
                    ux, uy = dx / dist, dy / dist
                    moved[i] = (ax - ux * push, ay - uy * push)
                    moved[j] = (bx + ux * push, by + uy * push)
        pts = moved
    return pts


def kite(
    points: Iterable, target: Point, advance: float = 1.0, retreat_step: float = 0.5
) -> List[Point]:
    """Move toward ``target`` by ``advance`` then back off by ``retreat_step``."""
    advanced = attack_move(points, target, step=advance)
    return retreat(advanced, target, step=retreat_step)


def encircle(points: Iterable, target: Point, radius: float = 5.0) -> List[Point]:
    """Same as :func:`circle_target` (kept as a named strategy)."""
    return circle_target(points, target, radius)


def leapfrog(
    points: Iterable, target: Point, step: float = 1.0, phase: int = 0
) -> List[Point]:
    """Even-indexed units leap forward when ``phase`` is even, odd when odd."""
    pts = _coerce(points)
    out: List[Point] = []
    for i, (x, y) in enumerate(pts):
        if (i % 2) == (phase % 2):
            ((nx, ny),) = attack_move([(x, y)], target, step=step)
            out.append((nx, ny))
        else:
            out.append((x, y))
    return out


def patrol(
    points: Iterable, waypoint_a: Point, waypoint_b: Point, progress: float = 0.5
) -> List[Point]:
    """Linear interpolate between two waypoints by ``progress`` in [0, 1]."""
    p = max(0.0, min(1.0, progress))
    target = (
        waypoint_a[0] + (waypoint_b[0] - waypoint_a[0]) * p,
        waypoint_a[1] + (waypoint_b[1] - waypoint_a[1]) * p,
    )
    return attack_move(points, target, step=1.0)


def regroup(points: Iterable, factor: float = 0.5) -> List[Point]:
    """Stronger cohesion variant — pull aggressively to centroid."""
    return cohere(points, factor=factor)


def flee(points: Iterable, threat: Point, step: float = 2.0) -> List[Point]:
    """Higher-step variant of :func:`retreat`."""
    return retreat(points, threat, step=step)


def pursue_closest(
    points: Iterable, targets: Sequence[Point], step: float = 1.0
) -> List[Point]:
    """Each point moves toward the closest of ``targets`` by ``step``."""
    pts = _coerce(points)
    if not targets:
        return pts
    out: List[Point] = []
    for x, y in pts:
        best = min(targets, key=lambda t: math.hypot(t[0] - x, t[1] - y))
        ((nx, ny),) = attack_move([(x, y)], best, step=step)
        out.append((nx, ny))
    return out


def random_jitter(
    points: Iterable, magnitude: float = 0.5, seed: Optional[int] = None
) -> List[Point]:
    """Apply uniform random offsets in [-magnitude, +magnitude]."""
    pts = _coerce(points)
    rng = random.Random(seed)
    return [
        (x + rng.uniform(-magnitude, magnitude), y + rng.uniform(-magnitude, magnitude))
        for x, y in pts
    ]


def wall_off(points: Iterable, choke_a: Point, choke_b: Point) -> List[Point]:
    """Place points evenly across a choke between ``choke_a`` and ``choke_b``."""
    pts = _coerce(points)
    n = len(pts)
    if n == 0:
        return []
    if n == 1:
        return [((choke_a[0] + choke_b[0]) / 2, (choke_a[1] + choke_b[1]) / 2)]
    return [
        (
            choke_a[0] + (choke_b[0] - choke_a[0]) * i / (n - 1),
            choke_a[1] + (choke_b[1] - choke_a[1]) * i / (n - 1),
        )
        for i in range(n)
    ]


def charge(points: Iterable, target: Point, step: float = 3.0) -> List[Point]:
    """Sprint variant of :func:`attack_move`."""
    return attack_move(points, target, step=step)


def scout(points: Iterable, origin: Point, distance: float = 5.0) -> List[Point]:
    """Push each point radially outward from ``origin`` to ``distance``."""
    pts = _coerce(points)
    n = len(pts)
    if n == 0:
        return []
    return [
        (
            origin[0] + distance * math.cos(2 * math.pi * i / n),
            origin[1] + distance * math.sin(2 * math.pi * i / n),
        )
        for i in range(n)
    ]


def ambush(points: Iterable, ambush_point: Point, step: float = 1.0) -> List[Point]:
    """Converge slowly to ``ambush_point``."""
    return attack_move(points, ambush_point, step=step)


def defend(points: Iterable, base: Point, radius: float = 3.0) -> List[Point]:
    """Hold a defensive ring of ``radius`` around ``base``."""
    return circle_target(points, base, radius)


def split_groups(
    points: Iterable, target_a: Point, target_b: Point, step: float = 1.0
) -> List[Point]:
    """Even-indexed points head to ``target_a``, odd-indexed to ``target_b``."""
    pts = _coerce(points)
    out: List[Point] = []
    for i, (x, y) in enumerate(pts):
        target = target_a if i % 2 == 0 else target_b
        ((nx, ny),) = attack_move([(x, y)], target, step=step)
        out.append((nx, ny))
    return out


def vortex(points: Iterable, angle: float = math.pi / 12) -> List[Point]:
    """Rotate every point by ``angle`` radians around the centroid."""
    pts = _coerce(points)
    if not pts:
        return []
    cx, cy = _centroid(pts)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return [
        (
            cx + (x - cx) * cos_a - (y - cy) * sin_a,
            cy + (x - cx) * sin_a + (y - cy) * cos_a,
        )
        for x, y in pts
    ]


def ring_expand(points: Iterable, factor: float = 0.2) -> List[Point]:
    """Move every point outward from the centroid by ``factor``."""
    return scatter(points, factor=factor)


def ring_contract(points: Iterable, factor: float = 0.2) -> List[Point]:
    """Move every point inward to the centroid by ``factor``."""
    return cohere(points, factor=factor)


def zigzag(
    points: Iterable,
    target: Point,
    step: float = 1.0,
    lateral: float = 0.5,
    phase: int = 0,
) -> List[Point]:
    """Advance toward ``target`` while zig-zagging laterally."""
    pts = _coerce(points)
    if not pts:
        return []
    tx, ty = target
    out: List[Point] = []
    for i, (x, y) in enumerate(pts):
        dx, dy = tx - x, ty - y
        dist = math.hypot(dx, dy) or 1.0
        fx, fy = dx / dist, dy / dist
        px, py = -fy, fx
        side = 1 if (phase + i) % 2 == 0 else -1
        out.append(
            (x + fx * step + px * lateral * side, y + fy * step + py * lateral * side)
        )
    return out


def bait(
    points: Iterable,
    target: Point,
    retreat_point: Point,
    bait_step: float = 1.0,
    retreat_step: float = 1.0,
) -> List[Point]:
    """First point baits toward target; the rest retreat to ``retreat_point``."""
    pts = _coerce(points)
    if not pts:
        return []
    bait_unit = attack_move([pts[0]], target, step=bait_step)
    others = (
        attack_move(pts[1:], retreat_point, step=retreat_step) if len(pts) > 1 else []
    )
    return bait_unit + others


def rally(points: Iterable, rally_point: Point, step: float = 1.0) -> List[Point]:
    """Rally all points toward ``rally_point`` by ``step``."""
    return attack_move(points, rally_point, step=step)
