# -*- coding: utf-8 -*-
"""
Common Helpers - 공통 유틸리티 함수

목적:
1. 중복 코드 제거
2. 일관된 체크 로직
3. 유지보수성 개선
"""

from typing import Any, Optional, List


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
    if hasattr(units, 'exists'):
        return units.exists

    # Standard list/collection
    if hasattr(units, '__len__'):
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
    if hasattr(units, 'first'):
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
        if hasattr(units, 'closest_to'):
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
    if hasattr(units, 'amount'):
        return units.amount

    # Standard list/collection
    if hasattr(units, '__len__'):
        return len(units)

    return 0


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
