# -*- coding: utf-8 -*-
"""
Flanking Coordinator - 양각 포위(샌드위치) 전술

병력을 2~3개 그룹으로 분리하여 적 진형의 양옆/뒤에서
동시에 덮치는 포위 공격 로직.

- 아군 서플라이 15+ 시 포위 기동 개시
- 적 중심에서 ±60도 오프셋으로 접근 웨이포인트 생성
- 모든 그룹이 접근 지점 도달 시 동시 돌격
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    UnitTypeId = None
    Point2 = None


class FlankingCoordinator:
    """
    양각 포위 전술 코디네이터

    아군 → 적 기본 벡터에서 ±ANGLE_OFFSET 만큼 회전하여
    2~3개 접근 경로를 생성하고, 유닛을 각 경로로 분배.
    모든 그룹이 접근 완료되면 동시 공격.
    """

    # 설정
    MIN_ARMY_SUPPLY = 15       # 포위 최소 보급
    NUM_GROUPS = 2             # 분할 그룹 수 (2 = 양각, 3 = 삼각)
    ANGLE_OFFSET_DEG = 60      # 기본 벡터에서의 편향 각도
    APPROACH_DISTANCE = 15.0   # 적으로부터 접근 웨이포인트 거리
    SYNC_TOLERANCE = 8.0       # 동시 돌격 허용 거리
    COOLDOWN = 30.0            # 포위 재시도 쿨다운(초)

    def __init__(self, bot):
        self.bot = bot
        self._flanking_active = False
        self._groups: Dict[int, List] = {}  # group_id -> [unit_tags]
        self._approach_points: Dict[int, object] = {}  # group_id -> Point2
        self._last_flank_time = 0.0
        self._phase = "IDLE"  # IDLE, APPROACH, ATTACK

    async def on_step(self, iteration: int) -> None:
        """매 프레임 호출"""
        try:
            game_time = getattr(self.bot, "time", 0.0)

            if self._phase == "IDLE":
                if game_time - self._last_flank_time < self.COOLDOWN:
                    return
                if self._check_flanking_opportunity():
                    self._phase = "APPROACH"
                    self._last_flank_time = game_time

            elif self._phase == "APPROACH":
                await self._execute_approach()
                if self._all_groups_in_position():
                    self._phase = "ATTACK"

            elif self._phase == "ATTACK":
                await self._sync_attack()
                self._phase = "IDLE"
                self._flanking_active = False
                self._groups.clear()
                self._approach_points.clear()

        except Exception as e:
            logger.warning(f"[FlankingCoordinator] on_step suppressed: {e}")
            self._phase = "IDLE"

    def _check_flanking_opportunity(self) -> bool:
        """포위 기동 개시 조건 확인"""
        if not hasattr(self.bot, "units") or not Point2:
            return False

        # 아군 전투 유닛 수집
        army = self._get_combat_units()
        if not army:
            return False

        army_supply = sum(getattr(u, "supply_cost", 1) for u in army)
        if army_supply < self.MIN_ARMY_SUPPLY:
            return False

        # 적 중심 확인
        enemy_center = self._get_enemy_center()
        if not enemy_center:
            return False

        # 그룹 분할 및 접근 지점 생성
        self._split_army_into_groups(army, enemy_center)
        return len(self._groups) >= 2

    def _split_army_into_groups(self, army: list, enemy_center) -> None:
        """
        병력을 NUM_GROUPS 개로 분리하고 각 그룹의 접근 웨이포인트 생성.

        기본 벡터(아군→적)에서 ±ANGLE_OFFSET 만큼 회전하여
        적의 양옆으로 접근 경로를 만듦.
        """
        if not army or not hasattr(self.bot, "townhalls") or not self.bot.townhalls:
            return

        our_base = self.bot.townhalls.first.position

        # 아군→적 기본 벡터
        dx = enemy_center.x - our_base.x
        dy = enemy_center.y - our_base.y
        base_angle = math.atan2(dy, dx)

        # 그룹별 접근 각도 계산
        offsets = []
        if self.NUM_GROUPS == 2:
            offsets = [-self.ANGLE_OFFSET_DEG, self.ANGLE_OFFSET_DEG]
        elif self.NUM_GROUPS == 3:
            offsets = [-self.ANGLE_OFFSET_DEG, 0, self.ANGLE_OFFSET_DEG]

        # 접근 웨이포인트 생성 (적 중심에서 APPROACH_DISTANCE 거리)
        for i, offset_deg in enumerate(offsets):
            angle = base_angle + math.radians(offset_deg)
            wx = enemy_center.x - self.APPROACH_DISTANCE * math.cos(angle)
            wy = enemy_center.y - self.APPROACH_DISTANCE * math.sin(angle)
            self._approach_points[i] = Point2((wx, wy))

        # 유닛을 라운드로빈으로 그룹에 배분
        for i in range(self.NUM_GROUPS):
            self._groups[i] = []

        for idx, unit in enumerate(army):
            group_id = idx % self.NUM_GROUPS
            self._groups[group_id].append(unit.tag)

        self._flanking_active = True

    async def _execute_approach(self) -> None:
        """각 그룹을 접근 웨이포인트로 이동"""
        if not hasattr(self.bot, "units"):
            return

        for group_id, tags in self._groups.items():
            target = self._approach_points.get(group_id)
            if not target:
                continue

            for tag in tags:
                unit = self._find_by_tag(tag)
                if not unit:
                    continue
                try:
                    if unit.distance_to(target) > self.SYNC_TOLERANCE:
                        self.bot.do(unit.move(target))
                except Exception as e:
                    logger.warning(f"[FlankingCoordinator] approach move suppressed: {e}")
                    continue

    def _all_groups_in_position(self) -> bool:
        """모든 그룹이 접근 지점에 도달했는지 확인"""
        for group_id, tags in self._groups.items():
            target = self._approach_points.get(group_id)
            if not target:
                continue

            units_in_pos = 0
            total = 0
            for tag in tags:
                unit = self._find_by_tag(tag)
                if not unit:
                    continue
                total += 1
                try:
                    if unit.distance_to(target) <= self.SYNC_TOLERANCE:
                        units_in_pos += 1
                except Exception as e:
                    logger.warning(f"[FlankingCoordinator] position check suppressed: {e}")
                    continue

            # 그룹의 60% 이상이 도착해야 함
            if total > 0 and units_in_pos / total < 0.6:
                return False

        return True

    async def _sync_attack(self) -> None:
        """모든 그룹 동시 돌격"""
        enemy_center = self._get_enemy_center()
        if not enemy_center:
            return

        for group_id, tags in self._groups.items():
            for tag in tags:
                unit = self._find_by_tag(tag)
                if not unit:
                    continue
                try:
                    self.bot.do(unit.attack(enemy_center))
                except Exception as e:
                    logger.warning(f"[FlankingCoordinator] sync attack suppressed: {e}")
                    continue

    def _get_combat_units(self) -> list:
        """전투 가능 유닛 반환 (퀸/드론 제외)"""
        if not hasattr(self.bot, "units") or not UnitTypeId:
            return []

        exclude = {UnitTypeId.DRONE, UnitTypeId.OVERLORD, UnitTypeId.QUEEN,
                    UnitTypeId.LARVA}

        # locked_units 존중 (harassment 등에 잠긴 유닛 제외)
        locked = set()
        if hasattr(self.bot, "harassment_coord") and self.bot.harassment_coord:
            locked = getattr(self.bot.harassment_coord, "locked_units", set())

        units = []
        for u in self.bot.units:
            if u.type_id in exclude:
                continue
            if u.tag in locked:
                continue
            if not u.can_attack:
                continue
            units.append(u)
        return units

    def _get_enemy_center(self):
        """적 전투 유닛 중심 위치"""
        if not hasattr(self.bot, "enemy_units"):
            return None
        enemies = self.bot.enemy_units
        if not enemies or not enemies.exists:
            return None
        # 전투 유닛만 (일꾼 제외)
        combat_enemies = enemies.filter(lambda e: e.can_attack and not e.is_structure)
        if combat_enemies and combat_enemies.exists:
            return combat_enemies.center
        return enemies.center

    def _find_by_tag(self, tag: int):
        """태그로 유닛 찾기"""
        if not hasattr(self.bot, "units"):
            return None
        for u in self.bot.units:
            if u.tag == tag:
                return u
        return None

    @property
    def is_flanking(self) -> bool:
        return self._flanking_active

    def get_status(self) -> Dict:
        return {
            "phase": self._phase,
            "groups": len(self._groups),
            "units_per_group": {k: len(v) for k, v in self._groups.items()},
            "active": self._flanking_active,
        }
