# -*- coding: utf-8 -*-
"""
Rally Point Manager - 랠리 포인트 관리

기능:
1. 병력 집결지 계산 및 업데이트
2. 병력 집결 관리
3. 공격 타이밍 판단
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.units import Units
    from sc2.unit import Unit
    from sc2.position import Point2
else:
    try:
        from sc2.units import Units
        from sc2.unit import Unit
        from sc2.position import Point2
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

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("RallyPoint")

        # Rally point state
        self._rally_point = None
        self._last_rally_update = 0
        self._rally_update_interval = 30  # Update every 30 seconds

        # Attack thresholds
        self._min_army_for_attack = 6  # Minimum army size for attack
        self._early_game_min_attack = 3  # Early game threshold

    @property
    def rally_point(self) -> Optional['Point2']:
        """현재 랠리 포인트 반환"""
        return self._rally_point

    @property
    def min_army_for_attack(self) -> int:
        """공격에 필요한 최소 병력 수"""
        game_time = getattr(self.bot, "time", 0)
        # 초반(5분 이전)에는 더 낮은 임계값 사용
        if game_time < 300:
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
            map_center = self.bot.game_info.map_center if hasattr(self.bot, "game_info") else our_base

            # Rally point is 30% of the way from our base to map center
            rally_x = our_base.x + (map_center.x - our_base.x) * 0.3
            rally_y = our_base.y + (map_center.y - our_base.y) * 0.3

            if hasattr(self.bot, "Point2"):
                self._rally_point = self.bot.Point2((rally_x, rally_y))
            else:
                from sc2.position import Point2
                self._rally_point = Point2((rally_x, rally_y))

            self._last_rally_update = getattr(self.bot, "time", 0)

        except Exception:
            # Fallback to main base position
            if hasattr(self.bot, "start_location"):
                self._rally_point = self.bot.start_location

    def calculate_rally_point(self) -> Optional['Point2']:
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
                target_base = self.bot.townhalls.closest_to(self.bot.game_info.map_center)
            except Exception:
                pass

        # 기지와 맵 중앙 사이 (전진 배치)
        if hasattr(self.bot, "game_info"):
            map_center = self.bot.game_info.map_center
            rally = target_base.position.towards(map_center, 10)
            return rally

        return target_base.position

    async def gather_at_rally_point(self, army_units, iteration: int):
        """
        병력을 랠리 포인트로 집결시킴

        유휴 상태이거나 멀리 떨어진 유닛만 이동
        """
        if not self._rally_point:
            return

        if iteration % 22 != 0:  # Only update every ~1 second
            return

        for unit in army_units:
            try:
                # Only send idle units or units far from rally point
                is_idle = getattr(unit, "is_idle", False)
                distance_to_rally = unit.distance_to(self._rally_point)

                if is_idle and distance_to_rally > 5:
                    self.bot.do(unit.move(self._rally_point))
                elif distance_to_rally > 20:  # Very far from rally
                    self.bot.do(unit.move(self._rally_point))
            except Exception:
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
                if unit.distance_to(self._rally_point) < 15:
                    near_count += 1
            except Exception:
                continue

        if total == 0:
            return True

        return (near_count / total) >= 0.7

    def has_minimum_army(self, army_units) -> bool:
        """공격에 필요한 최소 병력이 있는지 확인"""
        return len(army_units) >= self.min_army_for_attack
