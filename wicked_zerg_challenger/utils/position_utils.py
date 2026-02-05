"""
Position Utilities - Centralized position calculation helpers

Provides common position calculation functions to eliminate code duplication
across the codebase. Uses efficient algorithms and consistent interfaces.
"""

from typing import TYPE_CHECKING, List, Optional, Union
from sc2.position import Point2

if TYPE_CHECKING:
    from sc2.units import Units
    from sc2.unit import Unit


def get_center_position(units: Union[List, "Units"]) -> Point2:
    """
    Calculate geometric center of units

    Args:
        units: List or Units collection

    Returns:
        Center position as Point2

    Example:
        >>> center = get_center_position(army_units)
        >>> rally_point = center.towards(enemy_start, 5)
    """
    if not units:
        return Point2((0, 0))

    if len(units) == 1:
        return units[0].position

    center_x = sum(u.position.x for u in units) / len(units)
    center_y = sum(u.position.y for u in units) / len(units)
    return Point2((center_x, center_y))


def get_weighted_center(
    units: Union[List, "Units"],
    weight_by_health: bool = False,
    weight_by_supply: bool = False
) -> Point2:
    """
    Calculate weighted center of units

    Args:
        units: List or Units collection
        weight_by_health: If True, weight positions by unit HP
        weight_by_supply: If True, weight positions by unit supply cost

    Returns:
        Weighted center position as Point2

    Example:
        >>> # Prioritize high-HP units in center calculation
        >>> center = get_weighted_center(army, weight_by_health=True)
        >>> # Prioritize high-supply units (e.g., ultras over lings)
        >>> center = get_weighted_center(army, weight_by_supply=True)
    """
    if not units:
        return Point2((0, 0))

    if len(units) == 1:
        return units[0].position

    # Health-weighted
    if weight_by_health:
        total_health = sum(u.health for u in units)
        if total_health == 0:
            return get_center_position(units)

        center_x = sum(u.position.x * u.health for u in units) / total_health
        center_y = sum(u.position.y * u.health for u in units) / total_health
        return Point2((center_x, center_y))

    # Supply-weighted
    if weight_by_supply:
        total_supply = sum(u.supply_cost for u in units)
        if total_supply == 0:
            return get_center_position(units)

        center_x = sum(u.position.x * u.supply_cost for u in units) / total_supply
        center_y = sum(u.position.y * u.supply_cost for u in units) / total_supply
        return Point2((center_x, center_y))

    # Default: geometric center
    return get_center_position(units)


def get_closest_unit(units: Union[List, "Units"], position: Point2) -> Optional["Unit"]:
    """
    Get the closest unit to a position

    Args:
        units: List or Units collection
        position: Target position

    Returns:
        Closest unit, or None if units is empty

    Example:
        >>> enemy_center = get_center_position(enemy_units)
        >>> closest_enemy = get_closest_unit(enemy_units, my_army_center)
    """
    if not units:
        return None

    # Use built-in closest_to if available (Units collection)
    if hasattr(units, 'closest_to'):
        return units.closest_to(position)

    # Fallback for lists
    return min(units, key=lambda u: u.position.distance_to(position))


def get_furthest_unit(units: Union[List, "Units"], position: Point2) -> Optional["Unit"]:
    """
    Get the furthest unit from a position

    Args:
        units: List or Units collection
        position: Target position

    Returns:
        Furthest unit, or None if units is empty

    Example:
        >>> furthest = get_furthest_unit(my_units, enemy_position)
        >>> # Retreat to furthest unit's position
        >>> retreat_point = furthest.position
    """
    if not units:
        return None

    # Use built-in furthest_to if available (Units collection)
    if hasattr(units, 'furthest_to'):
        return units.furthest_to(position)

    # Fallback for lists
    return max(units, key=lambda u: u.position.distance_to(position))


def get_average_distance(units: Union[List, "Units"], position: Point2) -> float:
    """
    Calculate average distance from units to a position

    Args:
        units: List or Units collection
        position: Target position

    Returns:
        Average distance in game units

    Example:
        >>> avg_dist = get_average_distance(my_units, enemy_base)
        >>> if avg_dist < 10:
        >>>     # Units are close enough to attack
    """
    if not units:
        return 0.0

    total_distance = sum(u.position.distance_to(position) for u in units)
    return total_distance / len(units)


def get_spread_radius(units: Union[List, "Units"]) -> float:
    """
    Calculate spread radius of units (max distance from center)

    Args:
        units: List or Units collection

    Returns:
        Maximum distance from center to any unit

    Example:
        >>> spread = get_spread_radius(my_army)
        >>> if spread > 15:
        >>>     # Army is too spread out, regroup
    """
    if not units or len(units) <= 1:
        return 0.0

    center = get_center_position(units)
    max_distance = max(u.position.distance_to(center) for u in units)
    return max_distance


def is_position_safe(
    position: Point2,
    enemy_units: Union[List, "Units"],
    safe_distance: float = 10.0
) -> bool:
    """
    Check if a position is safe (no enemies within safe_distance)

    Args:
        position: Position to check
        enemy_units: Enemy units to check against
        safe_distance: Minimum safe distance

    Returns:
        True if safe, False otherwise

    Example:
        >>> if is_position_safe(expansion_location, enemy_units, safe_distance=15):
        >>>     # Safe to expand
    """
    if not enemy_units:
        return True

    # Use C++ closer_than if available
    if hasattr(enemy_units, 'closer_than'):
        return len(enemy_units.closer_than(safe_distance, position)) == 0

    # Fallback for lists
    for unit in enemy_units:
        if unit.position.distance_to(position) < safe_distance:
            return False
    return True


def get_perimeter_positions(
    center: Point2,
    radius: float,
    count: int = 8
) -> List[Point2]:
    """
    Get positions arranged in a circle around a center point

    Args:
        center: Center position
        radius: Radius of the circle
        count: Number of positions to generate

    Returns:
        List of positions arranged in a circle

    Example:
        >>> # Create defensive positions around a base
        >>> defensive_positions = get_perimeter_positions(
        >>>     base.position, radius=10, count=8
        >>> )
    """
    import math

    positions = []
    angle_step = 2 * math.pi / count

    for i in range(count):
        angle = i * angle_step
        x = center.x + radius * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        positions.append(Point2((x, y)))

    return positions


def interpolate_position(start: Point2, end: Point2, ratio: float) -> Point2:
    """
    Interpolate between two positions

    Args:
        start: Start position
        end: End position
        ratio: Interpolation ratio (0.0 = start, 1.0 = end)

    Returns:
        Interpolated position

    Example:
        >>> # Get position 30% of the way from start to end
        >>> waypoint = interpolate_position(my_base, enemy_base, 0.3)
    """
    x = start.x + (end.x - start.x) * ratio
    y = start.y + (end.y - start.y) * ratio
    return Point2((x, y))


def clamp_position(position: Point2, min_x: float, max_x: float,
                   min_y: float, max_y: float) -> Point2:
    """
    Clamp a position to within bounds

    Args:
        position: Position to clamp
        min_x, max_x: X bounds
        min_y, max_y: Y bounds

    Returns:
        Clamped position

    Example:
        >>> # Keep position within map bounds
        >>> safe_pos = clamp_position(target, 0, map_width, 0, map_height)
    """
    x = max(min_x, min(max_x, position.x))
    y = max(min_y, min(max_y, position.y))
    return Point2((x, y))


def get_bounding_box(units: Union[List, "Units"]) -> tuple[Point2, Point2]:
    """
    Get bounding box of units (min and max corners)

    Args:
        units: List or Units collection

    Returns:
        Tuple of (min_corner, max_corner) as Point2

    Example:
        >>> min_corner, max_corner = get_bounding_box(army_units)
        >>> width = max_corner.x - min_corner.x
        >>> height = max_corner.y - min_corner.y
    """
    if not units:
        return Point2((0, 0)), Point2((0, 0))

    min_x = min(u.position.x for u in units)
    max_x = max(u.position.x for u in units)
    min_y = min(u.position.y for u in units)
    max_y = max(u.position.y for u in units)

    return Point2((min_x, min_y)), Point2((max_x, max_y))
