# -*- coding: utf-8 -*-
"""
SC2 Encyclopedia - 유닛/건물 상성 참조 데이터베이스

저그 관점에서의 스타크래프트 2 유닛 백과사전.
DynamicCounterSystem, ProtossCounterSystem 등에서 참조합니다.
"""

from typing import Dict, List, Optional, Tuple


# ================================================================
# === Zerg Units (아군 유닛 정보) ===
# ================================================================
ZERG_UNITS = {
    "ZERGLING": {
        "name": "저글링", "cost": (25, 0, 0.5),  # minerals, gas, supply
        "hp": 35, "armor": 0, "dps": 5.9, "speed": 4.13,
        "attributes": ["light", "biological"],
        "strong_vs": ["MARINE", "ZEALOT", "STALKER", "IMMORTAL", "REAPER"],
        "weak_vs": ["HELLION", "COLOSSUS", "BANELING", "ARCHON", "ADEPT"],
        "role": "초반 러시, 수적 우세, 견제",
        "upgrade_path": "대사촉진(speed), 부신(adrenal)",
    },
    "BANELING": {
        "name": "맹독충", "cost": (25, 25, 0),  # morph from zergling
        "hp": 30, "armor": 0, "dps": 0, "speed": 3.5,
        "attributes": ["biological"],
        "strong_vs": ["MARINE", "ZEALOT", "ZERGLING", "SCV", "PROBE"],
        "weak_vs": ["MARAUDER", "STALKER", "ROACH", "SIEGE_TANK"],
        "role": "범위 피해, 경보병 학살, 건물 파괴",
        "upgrade_path": "원심분리기(speed), 점막생성(creep)",
    },
    "ROACH": {
        "name": "바퀴", "cost": (75, 25, 2),
        "hp": 145, "armor": 1, "dps": 8.4, "speed": 3.15,
        "attributes": ["armored", "biological"],
        "strong_vs": ["ZEALOT", "MARINE", "HELLION", "REAPER"],
        "weak_vs": ["IMMORTAL", "MARAUDER", "VOID_RAY", "STALKER"],
        "role": "초중반 전선 유지, 잠복 회복",
        "upgrade_path": "글리얼재생(burrow regen), 땅굴발톱(tunneling)",
    },
    "RAVAGER": {
        "name": "파멸충", "cost": (25, 75, 1),  # morph from roach
        "hp": 120, "armor": 1, "dps": 12.6, "speed": 3.85,
        "attributes": ["biological"],
        "strong_vs": ["FORCE_FIELD", "LIBERATOR_ZONE", "SIEGED_TANK"],
        "weak_vs": ["IMMORTAL", "MARAUDER", "VOID_RAY"],
        "role": "역장 해제, 시즈 파괴, 강제장 파괴",
        "upgrade_path": "없음",
    },
    "HYDRALISK": {
        "name": "히드라리스크", "cost": (100, 50, 2),
        "hp": 90, "armor": 0, "dps": 12.0, "speed": 3.15,
        "attributes": ["light", "biological"],
        "strong_vs": ["VOID_RAY", "PHOENIX", "BANSHEE", "MUTALISK", "STALKER"],
        "weak_vs": ["COLOSSUS", "SIEGE_TANK", "HIGH_TEMPLAR", "DISRUPTOR"],
        "role": "대공 + 대지 만능 딜러",
        "upgrade_path": "근육강화(speed), 가시솟음(range)",
    },
    "MUTALISK": {
        "name": "뮤탈리스크", "cost": (100, 100, 2),
        "hp": 120, "armor": 0, "dps": 6.2, "speed": 5.6,
        "attributes": ["light", "biological"],
        "strong_vs": ["WORKER", "TANK_UNSIEGED", "LIBERATOR_UNSIEGED", "OVERLORD"],
        "weak_vs": ["MARINE", "ARCHON", "PHOENIX", "THOR", "CORRUPTOR"],
        "role": "기동 견제, 일꾼 학살, 멀티 타격",
        "upgrade_path": "없음 (공격/방어 업그레이드)",
    },
    "CORRUPTOR": {
        "name": "타락귀", "cost": (150, 100, 2),
        "hp": 200, "armor": 2, "dps": 10.7, "speed": 4.72,
        "attributes": ["armored", "biological"],
        "strong_vs": ["CARRIER", "BATTLECRUISER", "TEMPEST", "VOID_RAY", "COLOSSUS"],
        "weak_vs": ["MARINE", "HYDRALISK", "STALKER", "PHOENIX"],
        "role": "대형 공중유닛 킬러",
        "upgrade_path": "없음 → 귀부인 변태",
    },
    "BROODLORD": {
        "name": "귀부인", "cost": (150, 150, 2),  # morph from corruptor
        "hp": 225, "armor": 1, "dps": 11.2, "speed": 1.97,
        "attributes": ["armored", "biological", "massive"],
        "strong_vs": ["GROUND_ARMY", "STALKER", "ROACH", "MARINE"],
        "weak_vs": ["VIKING", "CORRUPTOR", "VOID_RAY", "TEMPEST"],
        "role": "후반 핵심 유닛, 지상군 녹이기",
        "upgrade_path": "없음",
    },
    "LURKER": {
        "name": "가시지옥", "cost": (50, 100, 1),  # morph from hydra
        "hp": 200, "armor": 1, "dps": 20.0, "speed": 4.13,
        "attributes": ["armored", "biological"],
        "strong_vs": ["MARINE", "ZEALOT", "ZERGLING", "GROUND_ARMY"],
        "weak_vs": ["SIEGE_TANK", "DISRUPTOR", "AIR_UNITS", "OBSERVER"],
        "role": "영역 장악, 잠복 방어선",
        "upgrade_path": "적응형 외피(range), 지중잠복(deep burrow)",
    },
    "INFESTOR": {
        "name": "감염충", "cost": (100, 150, 2),
        "hp": 90, "armor": 0, "dps": 0, "speed": 3.15,
        "attributes": ["armored", "biological", "psionic"],
        "strong_vs": ["MARINE_BALL", "GATEWAY_ARMY", "MECH"],
        "weak_vs": ["EMP", "FEEDBACK", "DETECTION"],
        "role": "곰팡이(범위 잠금), 신경기생, 감염된 테란",
        "upgrade_path": "없음",
    },
    "VIPER": {
        "name": "살모사", "cost": (100, 200, 3),
        "hp": 150, "armor": 1, "dps": 0, "speed": 4.13,
        "attributes": ["armored", "biological", "psionic"],
        "strong_vs": ["SIEGE_TANK", "COLOSSUS", "BATTLECRUISER", "CARRIER"],
        "weak_vs": ["FEEDBACK", "SNIPE", "MASS_AIR"],
        "role": "끌어당기기(abduct), 기생폭탄, 실명구름",
        "upgrade_path": "없음",
    },
    "ULTRALISK": {
        "name": "울트라리스크", "cost": (300, 200, 6),
        "hp": 500, "armor": 2, "dps": 35.7, "speed": 4.13,
        "attributes": ["armored", "biological", "massive"],
        "strong_vs": ["MARINE", "ZEALOT", "ZERGLING", "LIGHT_GROUND"],
        "weak_vs": ["IMMORTAL", "MARAUDER", "VOID_RAY", "NEURAL_PARASITE"],
        "role": "후반 탱커, 전선 돌파",
        "upgrade_path": "키틴질 외피(armor+2), 조직 동화",
    },
    "QUEEN": {
        "name": "여왕", "cost": (150, 0, 2),
        "hp": 175, "armor": 1, "dps": 11.2, "speed": 1.31,
        "attributes": ["biological", "psionic"],
        "strong_vs": ["BANSHEE", "ORACLE", "HELLION", "REAPER"],
        "weak_vs": ["STALKER", "MARINE_BALL", "IMMORTAL"],
        "role": "유충주입, 점막확장, 수혈, 초반 대공",
        "upgrade_path": "없음",
    },
    "OVERSEER": {
        "name": "감시군주", "cost": (50, 50, 0),  # morph from overlord
        "hp": 200, "armor": 1, "dps": 0, "speed": 2.62,
        "attributes": ["armored", "biological", "detector"],
        "strong_vs": ["CLOAKED_UNITS", "BURROWED_UNITS", "DT"],
        "weak_vs": ["VIKING", "PHOENIX", "MARINE"],
        "role": "감지, 변환체 정찰, 오염",
        "upgrade_path": "감시군주 속도",
    },
}


# ================================================================
# === Counter Matrix (상성 매트릭스) ===
# ================================================================
COUNTER_MATRIX = {
    # === vs Terran ===
    "MARINE": {"counter": ["BANELING", "LURKER", "ULTRALISK"], "priority": "HIGH"},
    "MARAUDER": {"counter": ["ZERGLING_SURROUND", "BROODLORD", "ULTRALISK"], "priority": "MEDIUM"},
    "HELLION": {"counter": ["ROACH", "QUEEN", "ZERGLING_SURROUND"], "priority": "MEDIUM"},
    "SIEGE_TANK": {"counter": ["RAVAGER", "MUTALISK", "VIPER"], "priority": "CRITICAL"},
    "THOR": {"counter": ["ZERGLING_SURROUND", "ROACH", "VIPER"], "priority": "HIGH"},
    "BATTLECRUISER": {"counter": ["CORRUPTOR", "QUEEN", "VIPER"], "priority": "CRITICAL"},
    "LIBERATOR": {"counter": ["CORRUPTOR", "RAVAGER", "VIPER"], "priority": "HIGH"},
    "BANSHEE": {"counter": ["QUEEN", "HYDRALISK", "CORRUPTOR"], "priority": "HIGH"},
    "WIDOW_MINE": {"counter": ["OVERSEER", "ROACH", "OVERLORD_BAIT"], "priority": "MEDIUM"},
    "CYCLONE": {"counter": ["ZERGLING", "ROACH", "BANELING"], "priority": "MEDIUM"},
    "GHOST": {"counter": ["ZERGLING_SURROUND", "ULTRALISK", "BANELING"], "priority": "HIGH"},
    "RAVEN": {"counter": ["CORRUPTOR", "HYDRALISK"], "priority": "MEDIUM"},
    "MEDIVAC": {"counter": ["CORRUPTOR", "HYDRALISK", "MUTALISK"], "priority": "MEDIUM"},
    "VIKING": {"counter": ["HYDRALISK", "CORRUPTOR", "QUEEN"], "priority": "LOW"},

    # === vs Protoss ===
    "ZEALOT": {"counter": ["ROACH", "LURKER", "BANELING"], "priority": "MEDIUM"},
    "STALKER": {"counter": ["ZERGLING_SURROUND", "HYDRALISK", "ROACH"], "priority": "MEDIUM"},
    "ADEPT": {"counter": ["ROACH", "QUEEN", "ZERGLING"], "priority": "MEDIUM"},
    "SENTRY": {"counter": ["RAVAGER", "ZERGLING_SURROUND"], "priority": "LOW"},
    "IMMORTAL": {"counter": ["ZERGLING_SURROUND", "HYDRALISK", "BROODLORD"], "priority": "CRITICAL"},
    "COLOSSUS": {"counter": ["CORRUPTOR", "VIPER", "RAVAGER"], "priority": "CRITICAL"},
    "DISRUPTOR": {"counter": ["SPLIT_MICRO", "MUTALISK", "LURKER"], "priority": "HIGH"},
    "HIGH_TEMPLAR": {"counter": ["ZERGLING_FLANK", "GHOST_SNIPE", "ABDUCT"], "priority": "CRITICAL"},
    "ARCHON": {"counter": ["HYDRALISK", "BROODLORD", "LURKER"], "priority": "HIGH"},
    "DARK_TEMPLAR": {"counter": ["OVERSEER", "QUEEN", "SPORE_CRAWLER"], "priority": "CRITICAL"},
    "VOID_RAY": {"counter": ["HYDRALISK", "CORRUPTOR", "QUEEN"], "priority": "HIGH"},
    "PHOENIX": {"counter": ["HYDRALISK", "QUEEN", "CORRUPTOR"], "priority": "MEDIUM"},
    "CARRIER": {"counter": ["CORRUPTOR", "VIPER", "HYDRALISK"], "priority": "CRITICAL"},
    "TEMPEST": {"counter": ["CORRUPTOR", "VIPER_ABDUCT", "MUTALISK"], "priority": "HIGH"},
    "ORACLE": {"counter": ["QUEEN", "SPORE_CRAWLER", "HYDRALISK"], "priority": "HIGH"},
    "PRISM": {"counter": ["HYDRALISK", "QUEEN", "CORRUPTOR"], "priority": "HIGH"},

    # === vs Zerg (Mirror) ===
    "ZERGLING_ENEMY": {"counter": ["BANELING", "ROACH", "LURKER"], "priority": "MEDIUM"},
    "ROACH_ENEMY": {"counter": ["HYDRALISK", "RAVAGER", "ROACH"], "priority": "MEDIUM"},
    "MUTALISK_ENEMY": {"counter": ["HYDRALISK", "CORRUPTOR", "QUEEN"], "priority": "HIGH"},
    "BROODLORD_ENEMY": {"counter": ["CORRUPTOR", "VIPER", "INFESTOR"], "priority": "CRITICAL"},
    "LURKER_ENEMY": {"counter": ["RAVAGER", "VIPER", "AIR_UNITS"], "priority": "HIGH"},
}


# ================================================================
# === Tech Requirements (기술 요구사항) ===
# ================================================================
TECH_REQUIREMENTS = {
    "ZERGLING": {"building": "SPAWNINGPOOL"},
    "BANELING": {"building": "BANELINGNEST", "morph_from": "ZERGLING"},
    "ROACH": {"building": "ROACHWARREN"},
    "RAVAGER": {"building": "ROACHWARREN", "morph_from": "ROACH"},
    "HYDRALISK": {"building": "HYDRALISKDEN", "requires": "LAIR"},
    "LURKER": {"building": "LURKERDEN", "morph_from": "HYDRALISK", "requires": "LAIR"},
    "MUTALISK": {"building": "SPIRE", "requires": "LAIR"},
    "CORRUPTOR": {"building": "SPIRE", "requires": "LAIR"},
    "BROODLORD": {"building": "GREATERSPIRE", "morph_from": "CORRUPTOR", "requires": "HIVE"},
    "INFESTOR": {"building": "INFESTATIONPIT", "requires": "LAIR"},
    "VIPER": {"building": "INFESTATIONPIT", "requires": "HIVE"},
    "ULTRALISK": {"building": "ULTRALISKCAVERN", "requires": "HIVE"},
    "QUEEN": {"building": "SPAWNINGPOOL"},
    "OVERSEER": {"morph_from": "OVERLORD", "requires": "LAIR"},
}


# ================================================================
# === Timing Benchmarks (타이밍 기준) ===
# ================================================================
TIMING_BENCHMARKS = {
    "zergling_speed": {"time": 195, "description": "대사촉진 완료 (3:15)"},
    "first_queen": {"time": 120, "description": "첫 여왕 생산 (2:00)"},
    "natural_expand": {"time": 60, "description": "자연 기지 (1:00 - 1분멀티)"},
    "roach_warren": {"time": 180, "description": "바퀴굴 건설 (3:00)"},
    "lair": {"time": 240, "description": "둥지 변태 (4:00)"},
    "third_base": {"time": 240, "description": "셋째 기지 (4:00)"},
    "hydra_den": {"time": 300, "description": "히드라 둥지 (5:00)"},
    "spire": {"time": 360, "description": "스파이어 (6:00)"},
    "hive": {"time": 540, "description": "군락 변태 (9:00)"},
    "ultralisk_cavern": {"time": 600, "description": "울트라리스크 동굴 (10:00)"},
    "max_supply": {"time": 600, "description": "200 보급 도달 (10:00)"},
}


# ================================================================
# === Helper Functions ===
# ================================================================
def get_counter(enemy_unit: str) -> Optional[Dict]:
    """적 유닛에 대한 카운터 정보 반환"""
    key = enemy_unit.upper().replace(" ", "_")
    return COUNTER_MATRIX.get(key)


def get_unit_info(unit_name: str) -> Optional[Dict]:
    """유닛 정보 반환"""
    key = unit_name.upper().replace(" ", "_")
    return ZERG_UNITS.get(key)


def get_tech_path(unit_name: str) -> Optional[Dict]:
    """유닛 생산에 필요한 기술 경로 반환"""
    key = unit_name.upper().replace(" ", "_")
    return TECH_REQUIREMENTS.get(key)


def suggest_composition(enemy_comp: List[str]) -> Dict[str, int]:
    """
    적 조합에 대한 추천 아군 조합 반환.

    Args:
        enemy_comp: ["MARINE", "SIEGE_TANK", "MEDIVAC"] 등

    Returns:
        {"ZERGLING": 20, "BANELING": 10, "CORRUPTOR": 4} 등
    """
    counter_count = {}

    for enemy in enemy_comp:
        info = get_counter(enemy)
        if not info:
            continue

        priority_weight = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0.5}
        weight = priority_weight.get(info["priority"], 1)

        for counter_unit in info["counter"]:
            if counter_unit in counter_count:
                counter_count[counter_unit] += weight
            else:
                counter_count[counter_unit] = weight

    # Sort by weight
    sorted_comp = dict(sorted(counter_count.items(), key=lambda x: x[1], reverse=True))
    return sorted_comp


def get_encyclopedia_report(unit_name: str) -> str:
    """유닛의 전체 정보를 문자열로 반환"""
    info = get_unit_info(unit_name)
    if not info:
        return f"'{unit_name}' 유닛 정보를 찾을 수 없습니다."

    tech = get_tech_path(unit_name)

    report = f"""
=== {info['name']} ({unit_name}) ===
비용: {info['cost'][0]}광/{info['cost'][1]}가스/{info['cost'][2]}보급
체력: {info['hp']} | 방어: {info['armor']} | DPS: {info['dps']} | 속도: {info['speed']}
속성: {', '.join(info['attributes'])}
역할: {info['role']}
강한 상대: {', '.join(info['strong_vs'])}
약한 상대: {', '.join(info['weak_vs'])}
업그레이드: {info['upgrade_path']}"""

    if tech:
        report += f"\n기술 요구: {tech.get('building', '-')} | 상위건물: {tech.get('requires', '-')}"
        if tech.get('morph_from'):
            report += f" | 변태원본: {tech['morph_from']}"

    return report
