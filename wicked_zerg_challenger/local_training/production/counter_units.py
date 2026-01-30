# -*- coding: utf-8 -*-
"""
Counter Units Module

적 유닛 구성에 대한 카운터 유닛 선택 로직을 담당하는 모듈
"""

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        ZERGLING = "ZERGLING"
        ROACH = "ROACH"
        HYDRALISK = "HYDRALISK"
        MUTALISK = "MUTALISK"
        SPAWNINGPOOL = "SPAWNINGPOOL"
        BANELINGNEST = "BANELINGNEST"


def get_counter_unit(resilience, enemy_units, has_roach_warren: bool, has_hydra_den: bool, has_spire: bool):
    """
    적 구성을 분석하고 최적의 카운터 유닛 반환

    Counter logic:
    - vs Marines/Zealots/Zerglings (light infantry): Banelings (if nest) > Roaches
    - vs Roaches/Stalkers/Marauders (armored ground): Hydralisks > Roaches
    - vs Air units (Void Rays, Mutas, Vikings): Hydralisks > Mutalisks
    - vs Siege Tanks/Colossus (siege): Mutalisks (to flank) > Roaches
    - vs Immortals (anti-armor): Zerglings (swarm) > Hydralisks

    Args:
        resilience: ProductionResilience 인스턴스
        enemy_units: 감지된 적 유닛 리스트
        has_roach_warren: 바퀴굴 준비 여부
        has_hydra_den: 히드라 둥지 준비 여부
        has_spire: 스파이어 준비 여부

    Returns:
        UnitTypeId: 추천 카운터 유닛 (또는 None)
    """
    if not enemy_units:
        return None

    b = resilience.bot

    # Count enemy unit types
    enemy_counts = {
        "light_infantry": 0,  # Marines, Zealots, Zerglings
        "armored_ground": 0,  # Roaches, Stalkers, Marauders
        "air": 0,             # Any flying units
        "siege": 0,           # Siege Tanks, Colossus
        "anti_armor": 0,      # Immortals
    }

    # Light infantry unit IDs
    light_infantry_ids = ["MARINE", "ZEALOT", "ZERGLING", "ADEPT"]
    armored_ground_ids = ["ROACH", "STALKER", "MARAUDER", "IMMORTAL", "RAVAGER"]
    air_unit_ids = ["VOIDRAY", "PHOENIX", "ORACLE", "CARRIER", "TEMPEST",
                    "VIKINGFIGHTER", "BANSHEE", "BATTLECRUISER", "LIBERATOR",
                    "MUTALISK", "CORRUPTOR", "BROODLORD"]
    siege_ids = ["SIEGETANK", "SIEGETANKSIEGED", "COLOSSUS", "DISRUPTOR"]
    anti_armor_ids = ["IMMORTAL"]

    for enemy in enemy_units:
        enemy_name = getattr(enemy.type_id, "name", "")

        if any(light_id in enemy_name for light_id in light_infantry_ids):
            enemy_counts["light_infantry"] += 1
        if any(armored_id in enemy_name for armored_id in armored_ground_ids):
            enemy_counts["armored_ground"] += 1
        if any(air_id in enemy_name for air_id in air_unit_ids):
            enemy_counts["air"] += 1
        if any(siege_id in enemy_name for siege_id in siege_ids):
            enemy_counts["siege"] += 1
        if any(aa_id in enemy_name for aa_id in anti_armor_ids):
            enemy_counts["anti_armor"] += 1

    # Determine main threat
    max_threat = max(enemy_counts.values())
    if max_threat == 0:
        return None

    main_threats = [k for k, v in enemy_counts.items() if v == max_threat]
    main_threat = main_threats[0]

    # Return counter unit based on threat
    if main_threat == "air":
        # vs Air: Hydralisks > Mutalisks
        if has_hydra_den and b.can_afford(UnitTypeId.HYDRALISK):
            return UnitTypeId.HYDRALISK
        if has_spire and b.can_afford(UnitTypeId.MUTALISK):
            return UnitTypeId.MUTALISK

    elif main_threat == "light_infantry":
        # vs Light: Banelings > Roaches
        has_baneling_nest = b.structures(UnitTypeId.BANELINGNEST).ready.exists
        if has_baneling_nest:
            # Note: Banelings are morphed from Zerglings, not trained from larvae
            # Return None here; baneling morphing should be handled separately
            pass
        if has_roach_warren and b.can_afford(UnitTypeId.ROACH):
            return UnitTypeId.ROACH

    elif main_threat == "armored_ground":
        # vs Armored: Hydralisks > Roaches
        if has_hydra_den and b.can_afford(UnitTypeId.HYDRALISK):
            return UnitTypeId.HYDRALISK
        if has_roach_warren and b.can_afford(UnitTypeId.ROACH):
            return UnitTypeId.ROACH

    elif main_threat == "siege":
        # vs Siege: Mutalisks (flank) > Roaches
        if has_spire and b.can_afford(UnitTypeId.MUTALISK):
            return UnitTypeId.MUTALISK
        if has_roach_warren and b.can_afford(UnitTypeId.ROACH):
            return UnitTypeId.ROACH

    elif main_threat == "anti_armor":
        # vs Immortals: Zerglings (swarm) > Hydralisks
        if b.can_afford(UnitTypeId.ZERGLING) and b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
            return UnitTypeId.ZERGLING
        if has_hydra_den and b.can_afford(UnitTypeId.HYDRALISK):
            return UnitTypeId.HYDRALISK

    return None
