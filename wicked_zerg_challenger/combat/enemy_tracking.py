# -*- coding: utf-8 -*-
"""
Enemy Tracking Module

적 위치 추적 및 분석을 담당하는 모듈
"""


async def track_enemy_expansions(manager):
    """
    적 확장 기지 추적

    발견한 적 확장 위치를 기록하여 승리 조건 판단에 활용

    Args:
        manager: CombatManager 인스턴스
    """
    if not hasattr(manager.bot, "enemy_structures"):
        return

    enemy_structures = manager.bot.enemy_structures
    if not enemy_structures:
        return

    # 타운홀 타입
    townhall_types = {
        "NEXUS", "COMMANDCENTER", "ORBITALCOMMAND", "PLANETARYFORTRESS",
        "HATCHERY", "LAIR", "HIVE"
    }

    # 적 타운홀 찾기
    for struct in enemy_structures:
        struct_type = getattr(struct.type_id, "name", "").upper()
        if struct_type in townhall_types:
            # 확장 위치 기록
            pos = struct.position
            if pos not in manager._known_enemy_expansions:
                manager._known_enemy_expansions.add(pos)
                print(f"[VICTORY] New enemy expansion discovered at ({pos.x:.1f}, {pos.y:.1f})")


def get_anti_air_threats(enemy_units, position, range_check=15):
    """
    공중 공격 가능한 적 유닛 탐지

    Args:
        enemy_units: 적 유닛 리스트
        position: 확인할 위치
        range_check: 탐지 범위 (기본값: 15)

    Returns:
        공중 공격 가능한 적 유닛 리스트
    """
    anti_air_names = [
        "MARINE", "HYDRALISK", "STALKER", "PHOENIX", "VOIDRAY",
        "VIKINGFIGHTER", "THOR", "CYCLONE", "LIBERATOR",
        "QUEEN", "CORRUPTOR", "MUTALISK", "ARCHON",
        "MISSILETURRET", "SPORECRAWLER", "PHOTONCANNON"
    ]
    return [e for e in enemy_units
            if getattr(e.type_id, "name", "") in anti_air_names
            and e.distance_to(position) < range_check]


def find_densest_enemy_position(enemies):
    """
    가장 밀집된 적 위치 찾기 (맹독충용)

    Args:
        enemies: 적 유닛 리스트

    Returns:
        가장 밀집된 위치의 적 유닛 (None if no enemies)
    """
    if not enemies:
        return None

    max_density = 0
    densest_enemy = None

    for enemy in enemies:
        # 5 거리 내의 적 수 계산
        nearby_count = sum(1 for e in enemies if e.distance_to(enemy) < 5)
        if nearby_count > max_density:
            max_density = nearby_count
            densest_enemy = enemy

    return densest_enemy


def detect_nearby_enemies(bot, position, detection_range=25):
    """
    특정 위치 근처의 적 탐지

    Args:
        bot: 봇 인스턴스
        position: 확인할 위치
        detection_range: 탐지 범위 (기본값: 25)

    Returns:
        근처의 적 유닛 리스트
    """
    if not hasattr(bot, "enemy_units"):
        return []

    enemy_units = bot.enemy_units

    # Units collection has closer_than method
    if hasattr(enemy_units, "closer_than"):
        nearby_enemies = enemy_units.closer_than(detection_range, position)
        return list(nearby_enemies) if nearby_enemies else []
    else:
        # Fallback to manual distance check
        return [e for e in enemy_units if e.distance_to(position) < detection_range]


def get_closest_enemy(bot, position):
    """
    가장 가까운 적 유닛 찾기

    Args:
        bot: 봇 인스턴스
        position: 기준 위치

    Returns:
        가장 가까운 적 유닛 (None if no enemies)
    """
    if not hasattr(bot, "enemy_units"):
        return None

    enemy_units = bot.enemy_units
    if not enemy_units:
        return None

    # Units collection has closest_to method
    if hasattr(enemy_units, "closest_to"):
        return enemy_units.closest_to(position)
    else:
        # Fallback to manual search
        try:
            return min(enemy_units, key=lambda e: e.distance_to(position))
        except ValueError:
            return None


def track_enemy_army_composition(manager):
    """
    적 병력 구성 추적

    Args:
        manager: CombatManager 인스턴스

    Returns:
        dict: 적 유닛 타입별 개수
    """
    composition = {}

    if not hasattr(manager.bot, "enemy_units"):
        return composition

    for unit in manager.bot.enemy_units:
        unit_type = getattr(unit.type_id, "name", "UNKNOWN")
        composition[unit_type] = composition.get(unit_type, 0) + 1

    return composition
