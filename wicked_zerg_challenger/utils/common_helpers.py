# -*- coding: utf-8 -*-
"""
Common Helpers - 공통 유틸리티 함수

목적:
1. 중복 코드 제거
2. 일관된 체크 로직
3. 유지보수성 개선
"""

from typing import Any, Optional


def has_units(units: Any) -> bool:
    """
    유닛 컬렉션이 비어있지 않은지 확인

    Args:
        units: SC2 Units collection 또는 리스트

    Returns:
        유닛이 존재하면 True, 없으면 False

    Example:
        >>> if has_units(self.bot.units(UnitTypeId.ZERGLING)):
        >>>     # Do something with zerglings
    """
    if units is None:
        return False

    # SC2 Units collection
    if hasattr(units, "exists"):
        return units.exists

    # Standard list/collection
    if hasattr(units, "__len__"):
        return len(units) > 0

    return False


def safe_first(units: Any) -> Optional[Any]:
    """
    컬렉션의 첫 번째 요소를 안전하게 가져옴

    Args:
        units: SC2 Units collection 또는 리스트

    Returns:
        첫 번째 유닛, 없으면 None

    Example:
        >>> hatchery = safe_first(self.bot.townhalls)
        >>> if hatchery:
        >>>     # Use hatchery
    """
    if not has_units(units):
        return None

    # SC2 Units collection
    if hasattr(units, "first"):
        return units.first

    # Standard list/collection
    try:
        return units[0]
    except (IndexError, KeyError, TypeError):
        return None


def safe_closest(units: Any, position) -> Optional[Any]:
    """
    위치에서 가장 가까운 유닛을 안전하게 가져옴

    Args:
        units: SC2 Units collection
        position: 기준 위치

    Returns:
        가장 가까운 유닛, 없으면 None

    Example:
        >>> closest_enemy = safe_closest(enemy_units, my_unit.position)
        >>> if closest_enemy:
        >>>     my_unit.attack(closest_enemy)
    """
    if not has_units(units):
        return None

    if not position:
        return None

    try:
        if hasattr(units, "closest_to"):
            return units.closest_to(position)

        # Fallback: manual distance calculation
        return min(units, key=lambda u: u.distance_to(position))
    except (ValueError, AttributeError, TypeError):
        return None


def safe_amount(units: Any) -> int:
    """
    유닛 수를 안전하게 가져옴

    Args:
        units: SC2 Units collection 또는 리스트

    Returns:
        유닛 수 (없으면 0)

    Example:
        >>> ling_count = safe_amount(self.bot.units(UnitTypeId.ZERGLING))
    """
    if not has_units(units):
        return 0

    # SC2 Units collection
    if hasattr(units, "amount"):
        return units.amount

    # Standard list/collection
    if hasattr(units, "__len__"):
        return len(units)

    return 0


def units_amount(units: Any) -> int:
    """
    유닛 수를 안전하게 가져옴 (safe_amount의 별칭)

    Args:
        units: SC2 Units collection 또는 리스트

    Returns:
        유닛 수 (없으면 0)

    Example:
        >>> ling_count = units_amount(self.bot.units(UnitTypeId.ZERGLING))
    """
    return safe_amount(units)


def filter_by_type(units: Any, names) -> Any:
    """
    type_id.name이 names에 속하는 유닛만 필터링

    Args:
        units: SC2 Units collection 또는 리스트
        names: 허용할 type_id.name 값들의 컬렉션

    Returns:
        필터링된 유닛 컬렉션 (SC2 Units.filter 지원 시 이를 사용, 아니면 list)

    Example:
        >>> army = filter_by_type(self.bot.units, {"ZERGLING", "ROACH"})
    """
    if hasattr(units, "filter"):
        return units.filter(lambda u: u.type_id.name in names)
    return [u for u in units if getattr(u.type_id, "name", "") in names]


def closest_enemy(unit: Any, enemy_units: Any) -> Optional[Any]:
    """
    unit 기준으로 enemy_units 중 가장 가까운 유닛을 안전하게 가져옴

    Args:
        unit: 기준 유닛 (position 또는 distance_to를 가짐)
        enemy_units: 거리 비교 대상 유닛 컬렉션

    Returns:
        가장 가까운 유닛, 없거나 실패 시 None

    Example:
        >>> nearest = closest_enemy(my_unit, enemy_units)
    """
    if hasattr(enemy_units, "closest_to"):
        try:
            return enemy_units.closest_to(unit.position)
        except (AttributeError, TypeError, ValueError):
            return None

    items = list(enemy_units) if enemy_units is not None else []
    if not items:
        return None

    closest, closest_dist = None, None
    for enemy in items:
        try:
            dist = unit.distance_to(enemy)
        except (AttributeError, TypeError):
            continue
        if closest_dist is None or dist < closest_dist:
            closest, closest_dist = enemy, dist
    return closest


def centroid(units: Any) -> Optional[Any]:
    """
    유닛들의 기하학적 중심 위치 계산 (Point2)

    Args:
        units: SC2 Units collection 또는 리스트

    Returns:
        중심 Point2, 유닛이 없으면 None

    Example:
        >>> center = centroid(enemy_units)
        >>> if center:
        >>>     rally_point = center.towards(self.bot.start_location, 5)
    """
    items = list(units) if units is not None else []
    if not items:
        return None

    from sc2.position import Point2

    x_sum = sum(u.position.x for u in items)
    y_sum = sum(u.position.y for u in items)
    return Point2((x_sum / len(items), y_sum / len(items)))


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    값을 최소/최대 범위 내로 제한

    Args:
        value: 원본 값
        min_value: 최소값
        max_value: 최대값

    Returns:
        제한된 값

    Example:
        >>> worker_count = clamp(calculated_workers, 0, 24)
    """
    return max(min_value, min(value, max_value))


def percentage(value: float, total: float) -> float:
    """
    백분율 계산 (0.0 ~ 1.0)

    Args:
        value: 현재 값
        total: 전체 값

    Returns:
        백분율 (0.0 ~ 1.0), total이 0이면 0.0

    Example:
        >>> health_pct = percentage(unit.health, unit.health_max)
        >>> if health_pct < 0.3:
        >>>     retreat()
    """
    if total <= 0:
        return 0.0

    return clamp(value / total, 0.0, 1.0)
