# -*- coding: utf-8 -*-
"""
Rally Point Manager - 랠리 포인트 관리

기능:
1. 병력 집결지 계산 및 업데이트
2. 병력 집결 관리
3. 공격 타이밍 판단
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sc2.position import Point2
    from sc2.unit import Unit
    from sc2.units import Units
else:
    try:
        from sc2.position import Point2
        from sc2.unit import Unit
        from sc2.units import Units
    except ImportError:
        Units = object
        Unit = object
        Point2 = tuple

from utils.logger import get_logger


class RallyPointManager:
    """
    랠리 포인트 관리자

    책임:
    - 병력 집결지 계산
    - 병력 집결 상태 추적
    - 공격 준비 여부 판단
    """

    # --- Tuning constants ----------------------------------------------------
    # 랠리 포인트를 본진→맵중앙 선분 위에서 어느 비율 지점에 잡을지 (0~1).
    RALLY_BIAS_FROM_BASE = 0.3
    # update_rally_point 호출 간 최소 간격 (초).
    DEFAULT_RALLY_UPDATE_INTERVAL = 30
    # 2 베이스 이상일 때 전진 랠리를 위해 앞마당에서 맵 중앙으로 더 밀어내는 거리.
    FORWARD_RALLY_PUSH_DISTANCE = 10
    # is_idle 유닛을 랠리로 보낼 거리 임계값.
    IDLE_RALLY_DISTANCE = 5
    # 멀리 떨어진(반드시 랠리로 복귀시켜야 하는) 거리 임계값.
    FAR_FROM_RALLY_DISTANCE = 20
    # is_army_gathered() 가 "근처"로 보는 거리.
    GATHERED_RADIUS = 15
    # is_army_gathered() 가 True 를 반환하기 위한 비율.
    GATHERED_RATIO = 0.7
    # gather_at_rally_point() 의 step 간격 (~1초).
    GATHER_STEP_PERIOD = 22
    # 게임 시간(초) 기준 "초반" 정의.
    EARLY_GAME_CUTOFF_SEC = 300
    # 일반 공격 진입 최소 병력 (자살 공격 방지).
    DEFAULT_MIN_ARMY_FOR_ATTACK = 20
    # 초반 공격 진입 최소 병력 (저글링 24기 가량).
    DEFAULT_EARLY_GAME_MIN_ATTACK = 12

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("RallyPoint")

        # Rally point state
        self._rally_point = None
        self._last_rally_update = 0
        self._rally_update_interval = self.DEFAULT_RALLY_UPDATE_INTERVAL

        # Attack thresholds (override per instance for tests / tuning)
        self._min_army_for_attack = self.DEFAULT_MIN_ARMY_FOR_ATTACK
        self._early_game_min_attack = self.DEFAULT_EARLY_GAME_MIN_ATTACK

    @property
    def rally_point(self) -> Optional["Point2"]:
        """현재 랠리 포인트 반환"""
        return self._rally_point

    @property
    def min_army_for_attack(self) -> int:
        """공격에 필요한 최소 병력 수"""
        game_time = getattr(self.bot, "time", 0)
        if game_time < self.EARLY_GAME_CUTOFF_SEC:
            return self._early_game_min_attack
        return self._min_army_for_attack

    def should_update_rally_point(self, game_time: float) -> bool:
        """랠리 포인트 업데이트가 필요한지 확인"""
        if self._rally_point is None:
            return True
        return game_time - self._last_rally_update >= self._rally_update_interval

    def update_rally_point(self):
        """
        랠리 포인트 업데이트

        위치 계산:
        - 본진과 맵 중앙 사이 30% 지점
        - 안전한 우리 진영 쪽
        - 적 공격 경로를 피함
        """
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return

        try:
            our_base = self.bot.townhalls.first.position
            map_center = (
                self.bot.game_info.map_center
                if hasattr(self.bot, "game_info")
                else our_base
            )

            # Rally point is `RALLY_BIAS_FROM_BASE` of the way from our base
            # toward the map center.
            bias = self.RALLY_BIAS_FROM_BASE
            rally_x = our_base.x + (map_center.x - our_base.x) * bias
            rally_y = our_base.y + (map_center.y - our_base.y) * bias

            if hasattr(self.bot, "Point2"):
                self._rally_point = self.bot.Point2((rally_x, rally_y))
            else:
                from sc2.position import Point2

                self._rally_point = Point2((rally_x, rally_y))

            self._last_rally_update = getattr(self.bot, "time", 0)

        except (AttributeError, TypeError, ImportError) as e:
            # Game info / townhalls / sc2.position not usable — fall back.
            self.logger.debug(f"Rally point update failed, using main base: {e}")
            if hasattr(self.bot, "start_location"):
                self._rally_point = self.bot.start_location

    def calculate_rally_point(self) -> Optional["Point2"]:
        """
        랠리 포인트 계산 (병력 집결지)

        로직:
        - 2베이스 이상: 앞마당 앞
        - 1베이스: 본진 입구
        """
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls:
            return None

        # 메인 기지
        main_base = self.bot.townhalls.first

        # 앞마당 찾기 - 맵 중앙에 가장 가까운 기지
        target_base = main_base
        if self.bot.townhalls.amount > 1 and hasattr(self.bot, "game_info"):
            try:
                target_base = self.bot.townhalls.closest_to(
                    self.bot.game_info.map_center
                )
            except (AttributeError, TypeError):
                pass

        # 기지와 맵 중앙 사이 (전진 배치)
        if hasattr(self.bot, "game_info"):
            map_center = self.bot.game_info.map_center
            rally = target_base.position.towards(
                map_center, self.FORWARD_RALLY_PUSH_DISTANCE
            )
            return rally

        return target_base.position

    async def gather_at_rally_point(self, army_units, iteration: int):
        """
        병력을 랠리 포인트로 집결시킴

        유휴 상태이거나 멀리 떨어진 유닛만 이동
        """
        if not self._rally_point:
            return

        if iteration % self.GATHER_STEP_PERIOD != 0:  # ~1 second cadence
            return

        for unit in army_units:
            try:
                # Only send idle units or units far from rally point
                is_idle = getattr(unit, "is_idle", False)
                distance_to_rally = unit.distance_to(self._rally_point)

                if is_idle and distance_to_rally > self.IDLE_RALLY_DISTANCE:
                    self.bot.do(unit.move(self._rally_point))
                elif distance_to_rally > self.FAR_FROM_RALLY_DISTANCE:
                    self.bot.do(unit.move(self._rally_point))
            except (AttributeError, TypeError) as e:
                self.logger.debug(f"Rally gather move failed: {e}")
                continue

    def is_army_gathered(self, army_units) -> bool:
        """
        병력이 집결했는지 확인

        Returns:
            70% 이상의 유닛이 랠리 포인트 근처에 있으면 True
        """
        if not self._rally_point or not army_units:
            return True  # No rally point = consider gathered

        near_count = 0
        total = 0

        for unit in army_units:
            total += 1
            try:
                if unit.distance_to(self._rally_point) < self.GATHERED_RADIUS:
                    near_count += 1
            except (AttributeError, TypeError):
                continue

        if total == 0:
            return True

        return (near_count / total) >= self.GATHERED_RATIO

    def has_minimum_army(self, army_units) -> bool:
        """공격에 필요한 최소 병력이 있는지 확인"""
        return len(army_units) >= self.min_army_for_attack
