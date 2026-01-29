"""
Unit Helpers - 유닛 관련 공통 유틸리티 함수

여러 파일에서 반복되는 유닛 처리 로직을 중앙화합니다.
- find_nearby_enemies: 거리 기반 적 유닛 검색
- get_health_ratio: 유닛 HP 비율 계산
- filter_workers_by_task: 작업별 일꾼 필터링
- execute_unit_action: 안전한 유닛 명령 실행
- calculate_unit_supply: Supply 계산
"""

from typing import List, Optional, Callable, Any
from utils.logger import get_logger

try:
    from sc2.unit import Unit
    from sc2.units import Units
    from sc2.position import Point2
except ImportError:
    Unit = None
    Units = None
    Point2 = None

logger = get_logger("UnitHelpers")


def find_nearby_enemies(unit: Unit, enemy_units: Units, range: float) -> Units:
    """
    특정 거리 내의 적 유닛 찾기

    Args:
        unit: 기준 유닛
        enemy_units: 적 유닛 컬렉션
        range: 검색 거리

    Returns:
        거리 내의 적 유닛 컬렉션
    """
    if not unit or not enemy_units:
        return Units([], None)

    try:
        # closer_than 메서드 사용 (최적화)
        if hasattr(enemy_units, "closer_than"):
            return enemy_units.closer_than(range, unit)
        else:
            # 폴백: 직접 필터링
            return Units([e for e in enemy_units if e.distance_to(unit) < range], None)
    except Exception as e:
        logger.debug(f"find_nearby_enemies error: {e}")
        return Units([], None)


def get_health_ratio(unit: Unit) -> float:
    """
    유닛의 HP 비율 계산

    Args:
        unit: 대상 유닛

    Returns:
        HP 비율 (0.0 ~ 1.0), 오류 시 0.0
    """
    if not unit:
        return 0.0

    try:
        if hasattr(unit, "health") and hasattr(unit, "health_max"):
            if unit.health_max > 0:
                return unit.health / unit.health_max
        return 0.0
    except (AttributeError, ZeroDivisionError) as e:
        logger.debug(f"get_health_ratio error: {e}")
        return 0.0


def get_shield_ratio(unit: Unit) -> float:
    """
    유닛의 Shield 비율 계산 (Protoss 전용)

    Args:
        unit: 대상 유닛

    Returns:
        Shield 비율 (0.0 ~ 1.0), 오류 시 0.0
    """
    if not unit:
        return 0.0

    try:
        if hasattr(unit, "shield") and hasattr(unit, "shield_max"):
            if unit.shield_max > 0:
                return unit.shield / unit.shield_max
        return 0.0
    except (AttributeError, ZeroDivisionError) as e:
        logger.debug(f"get_shield_ratio error: {e}")
        return 0.0


def filter_workers_by_task(workers: Units, task_filter: Callable[[Unit], bool]) -> Units:
    """
    작업 조건에 따라 일꾼 필터링

    Args:
        workers: 일꾼 유닛 컬렉션
        task_filter: 필터 함수 (lambda w: w.is_gathering)

    Returns:
        필터링된 일꾼 컬렉션
    """
    if not workers:
        return Units([], None)

    try:
        return workers.filter(task_filter)
    except Exception as e:
        logger.debug(f"filter_workers_by_task error: {e}")
        return Units([], None)


def execute_unit_action(unit: Unit, action: Callable, *args, **kwargs) -> bool:
    """
    안전한 유닛 명령 실행 (try-except 래퍼)

    Args:
        unit: 대상 유닛
        action: 실행할 액션 (bot.do, unit.attack 등)
        *args, **kwargs: 액션 파라미터

    Returns:
        성공 여부
    """
    if not unit:
        return False

    try:
        action(*args, **kwargs)
        return True
    except (AttributeError, TypeError, ValueError) as e:
        logger.debug(f"execute_unit_action error for {unit.type_id}: {e}")
        return False


def calculate_unit_supply(units: Units) -> int:
    """
    유닛 컬렉션의 총 Supply 계산

    Args:
        units: 유닛 컬렉션

    Returns:
        총 Supply
    """
    if not units:
        return 0

    try:
        # Supply 값이 있는 유닛만 합산
        total_supply = 0
        for unit in units:
            if hasattr(unit, "supply_cost"):
                total_supply += unit.supply_cost
            else:
                # 기본값 (알 수 없는 유닛은 1)
                total_supply += 1
        return total_supply
    except Exception as e:
        logger.debug(f"calculate_unit_supply error: {e}")
        return len(units)  # 폴백: 유닛 개수


def is_unit_idle(unit: Unit) -> bool:
    """
    유닛이 idle 상태인지 확인

    Args:
        unit: 대상 유닛

    Returns:
        idle 여부
    """
    if not unit:
        return False

    try:
        return unit.is_idle if hasattr(unit, "is_idle") else False
    except AttributeError:
        return False


def is_unit_attacking(unit: Unit) -> bool:
    """
    유닛이 공격 중인지 확인

    Args:
        unit: 대상 유닛

    Returns:
        공격 중 여부
    """
    if not unit:
        return False

    try:
        if hasattr(unit, "is_attacking"):
            return unit.is_attacking
        # 폴백: order 체크
        if hasattr(unit, "orders") and unit.orders:
            attack_abilities = {"ATTACK", "ATTACKATTACK"}
            return any(order.ability.button_name in attack_abilities for order in unit.orders)
        return False
    except (AttributeError, TypeError):
        return False


def get_unit_range(unit: Unit) -> float:
    """
    유닛의 공격 사거리 가져오기

    Args:
        unit: 대상 유닛

    Returns:
        공격 사거리, 없으면 0
    """
    if not unit:
        return 0.0

    try:
        if hasattr(unit, "ground_range"):
            return unit.ground_range
        elif hasattr(unit, "air_range"):
            return unit.air_range
        return 0.0
    except AttributeError:
        return 0.0


def can_unit_attack(unit: Unit, target: Unit) -> bool:
    """
    유닛이 타겟을 공격할 수 있는지 확인

    Args:
        unit: 공격자
        target: 타겟

    Returns:
        공격 가능 여부
    """
    if not unit or not target:
        return False

    try:
        # 거리 체크
        attack_range = get_unit_range(unit)
        if attack_range <= 0:
            return False

        distance = unit.distance_to(target)
        if distance > attack_range + 3:  # 버퍼 포함
            return False

        # 공격 능력 체크
        if hasattr(unit, "can_attack"):
            return unit.can_attack(target)

        return True
    except (AttributeError, ValueError):
        return False
