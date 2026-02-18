# -*- coding: utf-8 -*-
"""
Targeting utilities for combat logic.

Provides basic prioritization for high-threat or low-health targets.
"""

import logging
from typing import Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:  # Fallback for tooling environments
    UnitTypeId = None


def _unit_type_ids(names: Sequence[str]) -> List[object]:
    if not UnitTypeId:
        return []
    ids: List[object] = []
    for name in names:
        unit_type = getattr(UnitTypeId, name, None)
        if unit_type is not None:
            ids.append(unit_type)
        else:
            logger.debug("UnitTypeId has no attribute %r -- skipped", name)
    return ids


HIGH_VALUE_TYPES = set(
    _unit_type_ids(
        [
            "SIEGETANKSIEGED",
            "SIEGETANK",
            "COLOSSUS",
            "IMMORTAL",
            "DISRUPTOR",
            "HIGHTEMPLAR",
            "ARCHON",
            "WIDOWMINE",
            "WIDOWMINEBURROWED",
            "BATTLECRUISER",
            "CARRIER",
            "TEMPEST",
            "GHOST",
            "VOIDRAY",
            "BANSHEE",
            "LIBERATOR",
            "LIBERATORAG",
        ]
    )
)

LOW_PRIORITY_TYPES = set(
    _unit_type_ids(
        [
            "INTERCEPTOR",
            "LARVA",
            "EGG",
            "CHANGELING",
            "CHANGELINGZEALOT",
            "CHANGELINGMARINESHIELD",
            "CHANGELINGMARINE",
            "CHANGELINGZERGLINGWINGS",
            "CHANGELINGZERGLING",
            "ADEPTPHASESHIFT",
        ]
    )
)


def _health_ratio(unit) -> float:
    health = getattr(unit, "health", None)
    health_max = getattr(unit, "health_max", None)
    # None check: health or health_max 가 None/0이면 안전 기본값 반환
    if health is None or health_max is None or health_max <= 0:
        return 1.0
    return max(0.0, min(1.0, health / health_max))


def _shield_ratio(unit) -> float:
    shield = getattr(unit, "shield", None)
    shield_max = getattr(unit, "shield_max", None)
    # None check: shield 또는 shield_max 가 None/0이면 안전 기본값 반환
    if shield is None or shield_max is None or shield_max <= 0:
        return 1.0
    return max(0.0, min(1.0, shield / shield_max))


def _score_target(unit) -> float:
    """단일 유닛에 대한 우선순위 점수 계산 (높을수록 우선 공격)."""
    if unit is None:
        return -999.0

    type_id = getattr(unit, "type_id", None)

    # LOW PRIORITY: 교전 가치가 낮은 유닛
    if type_id is not None and type_id in LOW_PRIORITY_TYPES:
        return -100.0

    base = 1.0
    if type_id is not None and type_id in HIGH_VALUE_TYPES:
        base += 5.0  # 고가치 유닛 보너스

    base += (1.0 - _health_ratio(unit)) * 2.0
    base += (1.0 - _shield_ratio(unit)) * 1.0

    if getattr(unit, "is_flying", False):
        base += 0.2

    if getattr(unit, "is_cloaked", False):
        base += 0.5

    return base


# 프레임 단위 캐시: 동일 적 집합에 대한 중복 정렬 방지
_prioritized_cache: dict = {"enemies_id": None, "result": []}


def prioritize_targets(enemies: Iterable) -> List:
    """Return enemies sorted by priority (highest first).

    동일 적 집합(tag frozenset 기준)에 대한 결과를 캐싱하여
    같은 프레임 내 반복 호출 시 중복 정렬을 방지합니다.
    """
    if enemies is None:
        return []

    enemy_list = list(enemies)
    if not enemy_list:
        return []

    # None 유닛 필터링
    enemy_list = [e for e in enemy_list if e is not None]
    if not enemy_list:
        return []

    # 캐시 키: 태그 frozenset
    cache_id = None
    try:
        cache_id = frozenset(e.tag for e in enemy_list)
    except (AttributeError, TypeError):
        logger.debug("prioritize_targets: tag 추출 실패, 캐시 생략")

    if cache_id is not None and cache_id == _prioritized_cache.get("enemies_id"):
        return _prioritized_cache["result"]

    enemy_list.sort(key=_score_target, reverse=True)

    if cache_id is not None:
        _prioritized_cache["enemies_id"] = cache_id
        _prioritized_cache["result"] = enemy_list

    return enemy_list


def select_target(unit, enemies: Iterable, max_range: float = 12.0) -> Optional[object]:
    """유닛 근처에서 최적의 공격 대상을 선택합니다."""
    if unit is None:
        logger.debug("select_target: unit is None")
        return None
    if enemies is None:
        return None

    position = getattr(unit, "position", None)

    if hasattr(enemies, "closer_than") and position is not None:
        try:
            enemy_list = list(enemies.closer_than(max_range, position))
        except Exception:
            logger.debug("closer_than 호출 실패 -- 전체 목록 사용")
            enemy_list = list(enemies)
    else:
        enemy_list = list(enemies)

    if not enemy_list:
        return None

    prioritized = prioritize_targets(enemy_list)
    if not prioritized:
        return None
    return prioritized[0]


class Targeting:
    """Wrapper class for targeting functions (used by combat/initialization.py)."""

    def __init__(self, bot):
        if bot is None:
            logger.warning("Targeting: bot is None -- 일부 기능이 제한될 수 있습니다")
        self.bot = bot

    def prioritize(self, enemies: Iterable) -> List:
        return prioritize_targets(enemies)

    def select(self, unit, enemies: Iterable, max_range: float = 12.0) -> Optional[object]:
        return select_target(unit, enemies, max_range)

    def score(self, unit) -> float:
        if unit is None:
            return -999.0
        return _score_target(unit)
