# -*- coding: utf-8 -*-
"""
Rally Point Calculator Module

병력 집결지 계산 및 관리를 담당하는 모듈
"""


def calculate_rally_point(manager):
    """
    랠리 포인트 계산 (병력 집결지)
    - 2베이스 이상: 앞마당 앞
    - 1베이스: 본진 입구

    Args:
        manager: CombatManager 인스턴스

    Returns:
        Point2: 랠리 포인트 위치 (None if not available)
    """
    if not hasattr(manager.bot, "townhalls") or not manager.bot.townhalls:
        return None

    # 메인 기지
    main_base = manager.bot.townhalls.first

    # 앞마당 찾기 - 맵 중앙에 가장 가까운 기지
    target_base = main_base
    if manager.bot.townhalls.amount > 1 and hasattr(manager.bot, "game_info"):
        try:
            target_base = manager.bot.townhalls.closest_to(manager.bot.game_info.map_center)
        except Exception:
            pass

    # 기지와 맵 중앙 사이 (전진 배치)
    if hasattr(manager.bot, "game_info"):
        map_center = manager.bot.game_info.map_center
        rally = target_base.position.towards(map_center, 10)
        return rally

    return target_base.position


def update_rally_point(manager):
    """
    병력 집결을 위한 랠리 포인트 업데이트

    Rally point is positioned:
    - Between our natural expansion and map center
    - On our side of the map for safety
    - Away from enemy attack routes

    Args:
        manager: CombatManager 인스턴스
    """
    if not hasattr(manager.bot, "townhalls") or not manager.bot.townhalls.exists:
        return

    try:
        from sc2.position import Point2
        # ★ Phase 38: 랠리 기준을 본진(townhalls.first)이 아닌 맵 중앙 최근접 기지로 변경
        # (이전: 3, 4 베이스 이후에도 본진 앞에 집결지 고정)
        if manager.bot.townhalls.amount > 1:
            try:
                our_base = manager.bot.townhalls.closest_to(manager.bot.game_info.map_center).position
            except Exception:
                our_base = manager.bot.townhalls.first.position
        else:
            our_base = manager.bot.townhalls.first.position
        map_center = manager.bot.game_info.map_center if hasattr(manager.bot, "game_info") else our_base

        # ★ Phase 18: 크립 위 교전 유도 — 랠리 포인트를 크립 위에 설정 ★
        # 30%~50% 사이에서 크립이 있는 가장 전진된 위치를 선택
        best_rally = None
        for ratio in [0.45, 0.40, 0.35, 0.30, 0.25]:
            rx = our_base.x + (map_center.x - our_base.x) * ratio
            ry = our_base.y + (map_center.y - our_base.y) * ratio
            candidate = Point2((rx, ry))
            # 크립 체크: has_creep 속성이 있으면 크립 위 우선
            if hasattr(manager.bot, "has_creep") and manager.bot.has_creep(candidate):
                best_rally = candidate
                break  # 가장 전진된 크립 위치 선택

        if best_rally is None:
            # 크립 없으면 기존 30% 위치
            rally_x = our_base.x + (map_center.x - our_base.x) * 0.3
            rally_y = our_base.y + (map_center.y - our_base.y) * 0.3
            best_rally = Point2((rally_x, rally_y))

        manager._rally_point = best_rally

    except Exception:
        if hasattr(manager.bot, "start_location"):
            manager._rally_point = manager.bot.start_location


async def gather_at_rally_point(manager, army_units, iteration: int):
    """
    병력을 랠리 포인트로 집결

    Only sends idle or wandering units to rally point.

    Args:
        manager: CombatManager 인스턴스
        army_units: 아군 유닛 리스트
        iteration: 현재 반복 횟수
    """
    if not manager._rally_point:
        return

    if iteration % 22 != 0:  # Only update every ~1 second
        return

    for unit in army_units:
        try:
            is_idle = getattr(unit, "is_idle", False)
            distance_to_rally = unit.distance_to(manager._rally_point)

            if is_idle and distance_to_rally > 5:
                manager.bot.do(unit.move(manager._rally_point))
            elif distance_to_rally > 20:
                # ★ Phase 38: 전투 중인 유닛은 강제 이동 금지 (이전: 모든 원거리 유닛 후퇴)
                # 근처에 적이 있으면 이동 명령 생략
                nearby_enemies = manager.bot.enemy_units.closer_than(12, unit) if hasattr(manager.bot, "enemy_units") and manager.bot.enemy_units else []
                if not nearby_enemies:
                    manager.bot.do(unit.move(manager._rally_point))
        except Exception:
            continue


def is_army_gathered(manager, army_units) -> bool:
    """
    병력이 랠리 포인트에 집결했는지 확인

    Returns True if at least 70% of units are near rally point.

    Args:
        manager: CombatManager 인스턴스
        army_units: 아군 유닛 리스트

    Returns:
        bool: 집결 완료 여부
    """
    if not manager._rally_point or not army_units:
        return True  # No rally point = consider gathered

    near_count = 0
    total = 0

    for unit in army_units:
        total += 1
        try:
            if unit.distance_to(manager._rally_point) < 15:
                near_count += 1
        except Exception:
            continue

    if total == 0:
        return True

    return (near_count / total) >= 0.7


def get_rally_position(manager):
    """
    현재 랠리 포인트 위치 조회

    Args:
        manager: CombatManager 인스턴스

    Returns:
        Point2: 랠리 포인트 위치 (None if not set)
    """
    return manager._rally_point


def set_rally_position(manager, position):
    """
    랠리 포인트 위치 설정

    Args:
        manager: CombatManager 인스턴스
        position: Point2 위치
    """
    manager._rally_point = position


def clear_rally_position(manager):
    """
    랠리 포인트 초기화

    Args:
        manager: CombatManager 인스턴스
    """
    manager._rally_point = None
