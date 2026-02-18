# -*- coding: utf-8 -*-
"""
Feature #95: 럴커 포지셔닝 매니저

초크포인트 및 좁은 길목에 럴커를 전략적으로 배치하는 시스템:
1. 맵의 초크포인트/좁은 길목 탐지
2. 럴커 최적 배치 위치 계산
3. 버로우/언버로우 타이밍 관리
4. 디텍터 대응 (감지기 회피)

기존 LurkerAmbushSystem과의 차이:
- LurkerAmbushSystem: 매복 + 기습 공격 (공격적)
- LurkerPositionManager: 초크 포인트 방어 배치 (방어적/전략적)
"""

from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
    from sc2.unit import Unit
    from sc2.units import Units
except ImportError:
    AbilityId = None
    UnitTypeId = None
    UpgradeId = None
    Point2 = None
    Unit = None
    Units = None

from utils.logger import get_logger


class LurkerRole(Enum):
    """럴커 역할"""
    UNASSIGNED = "unassigned"
    CHOKE_GUARD = "choke_guard"      # 초크포인트 방어
    EXPANSION_GUARD = "expansion_guard"  # 확장 기지 방어
    FORWARD_POSITION = "forward"     # 전진 배치
    RETREATING = "retreating"        # 후퇴 중


class LurkerPositionManager:
    """
    럴커 포지셔닝 매니저

    맵의 전략적 위치에 럴커를 배치하여 효과적인 지역 통제를 합니다.

    핵심 기능:
    - 초크포인트 자동 탐지 및 럴커 배치
    - 확장 기지 입구 방어 배치
    - 적 디텍터 감지 시 언버로우 + 재배치
    - 사거리 업그레이드 반영
    """

    def __init__(self, bot):
        """
        럴커 포지셔닝 매니저 초기화

        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot
        self.logger = get_logger("LurkerPosition")

        # 럴커 할당 상태
        self.lurker_assignments: Dict[int, LurkerRole] = {}  # tag -> role
        self.lurker_positions: Dict[int, Point2] = {}  # tag -> assigned_position
        self.lurker_burrowed: Dict[int, bool] = {}  # tag -> is_burrowed

        # 초크포인트 캐시
        self._choke_points: List[Point2] = []
        self._choke_cache_time: float = 0.0
        self._choke_cache_duration: float = 60.0  # 1분마다 갱신

        # 전략적 위치
        self._expansion_guard_positions: List[Point2] = []
        self._forward_positions: List[Point2] = []

        # 파라미터
        self.lurker_range: float = 9.0  # 기본 사거리
        self.burrow_safe_distance: float = 13.0  # 적이 이 거리 이내에 오면 버로우
        self.unburrow_detector_range: float = 11.0  # 감지기 이 거리 내 시 언버로우
        self.reposition_distance: float = 5.0  # 재배치 최소 거리
        self.max_lurkers_per_choke: int = 3  # 초크당 최대 럴커

        # 디텍터 유닛 타입
        self.detector_types = set()
        if UnitTypeId:
            self.detector_types = {
                UnitTypeId.OBSERVER, UnitTypeId.OBSERVERSIEGEMODE,
                UnitTypeId.RAVEN, UnitTypeId.OVERSEER,
                UnitTypeId.MISSILETURRET, UnitTypeId.PHOTONCANNON,
                UnitTypeId.SPORECRAWLER,
            }

        # 통계
        self.positions_held: int = 0
        self.repositions: int = 0

    async def on_step(self, iteration: int):
        """
        매 프레임 럴커 포지셔닝 업데이트

        Args:
            iteration: 현재 게임 반복 횟수
        """
        try:
            if not UnitTypeId:
                return

            game_time = getattr(self.bot, "time", 0.0)

            # 초크포인트 갱신 (1분마다)
            if game_time - self._choke_cache_time > self._choke_cache_duration:
                self._update_choke_points()
                self._choke_cache_time = game_time

            # 사거리 업그레이드 확인
            if iteration % 220 == 0:
                self._check_range_upgrade()

            # 죽은 럴커 정리
            if iteration % 22 == 0:
                self._clean_dead_lurkers()

            # 럴커 관리
            if iteration % 11 == 0:
                await self._manage_lurkers(game_time)

            # 디텍터 대응
            if iteration % 8 == 0:
                await self._handle_detectors(game_time)

            # 통계 출력
            if iteration % 1100 == 0:
                self._print_report(game_time)

        except Exception as e:
            if iteration % 100 == 0:
                self.logger.error(f"[LURKER_POS] Error: {e}")

    def _update_choke_points(self):
        """맵 초크포인트 업데이트"""
        self._choke_points.clear()
        self._expansion_guard_positions.clear()

        if not hasattr(self.bot, "game_info"):
            return

        # 1. 아군 기지 사이의 초크포인트
        if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
            for th in self.bot.townhalls:
                # 기지 앞 초크포인트 (기지와 맵 중앙 사이)
                if hasattr(self.bot, "game_info"):
                    map_center = self.bot.game_info.map_center
                    choke = th.position.towards(map_center, 10)
                    self._choke_points.append(choke)

                    # 확장 기지 입구 방어 위치
                    guard_pos = th.position.towards(map_center, 6)
                    self._expansion_guard_positions.append(guard_pos)

        # 2. 램프(경사로) 위치 활용
        if hasattr(self.bot.game_info, "map_ramps"):
            for ramp in self.bot.game_info.map_ramps:
                if hasattr(ramp, "top_center"):
                    ramp_pos = ramp.top_center
                    # 아군 본진 근처 램프만 선택
                    if hasattr(self.bot, "start_location"):
                        if ramp_pos.distance_to(self.bot.start_location) < 40:
                            self._choke_points.append(ramp_pos)

        # 3. 전진 배치 위치 (맵 중앙 쪽)
        if hasattr(self.bot, "start_location") and hasattr(self.bot, "game_info"):
            start = self.bot.start_location
            center = self.bot.game_info.map_center
            forward = start.towards(center, start.distance_to(center) * 0.5)
            self._forward_positions.append(forward)

    def _check_range_upgrade(self):
        """럴커 사거리 업그레이드 확인"""
        if not hasattr(self.bot, "state") or not UpgradeId:
            return

        try:
            if UpgradeId.LURKERRANGE in self.bot.state.upgrades:
                if self.lurker_range < 10:
                    self.lurker_range = 10.0
                    self.logger.info("[LURKER_POS] 럴커 사거리 업그레이드 완료! (10)")
        except (AttributeError, TypeError):
            pass

    def _clean_dead_lurkers(self):
        """파괴된 럴커 정리"""
        if not hasattr(self.bot, "units"):
            return

        alive_tags = {u.tag for u in self.bot.units(UnitTypeId.LURKERMP)}

        dead = set(self.lurker_assignments.keys()) - alive_tags
        for tag in dead:
            self.lurker_assignments.pop(tag, None)
            self.lurker_positions.pop(tag, None)
            self.lurker_burrowed.pop(tag, None)

    async def _manage_lurkers(self, game_time: float):
        """모든 럴커 관리"""
        if not hasattr(self.bot, "units"):
            return

        lurkers = self.bot.units(UnitTypeId.LURKERMP)
        if not lurkers.exists:
            return

        for lurker in lurkers:
            role = self.lurker_assignments.get(lurker.tag, LurkerRole.UNASSIGNED)

            if role == LurkerRole.UNASSIGNED:
                await self._assign_lurker(lurker, game_time)

            elif role == LurkerRole.CHOKE_GUARD:
                await self._manage_choke_guard(lurker, game_time)

            elif role == LurkerRole.EXPANSION_GUARD:
                await self._manage_expansion_guard(lurker, game_time)

            elif role == LurkerRole.FORWARD_POSITION:
                await self._manage_forward_position(lurker, game_time)

            elif role == LurkerRole.RETREATING:
                await self._manage_retreat(lurker, game_time)

    async def _assign_lurker(self, lurker: Unit, game_time: float):
        """
        럴커에 역할 할당

        우선순위:
        1. 초크포인트 방어 (부족한 경우)
        2. 확장 기지 방어
        3. 전진 배치
        """
        # 초크포인트 방어 필요 확인
        for choke in self._choke_points:
            lurkers_at_choke = sum(
                1 for t, r in self.lurker_assignments.items()
                if r == LurkerRole.CHOKE_GUARD
                and t in self.lurker_positions
                and self.lurker_positions[t].distance_to(choke) < 8
            )
            if lurkers_at_choke < self.max_lurkers_per_choke:
                self.lurker_assignments[lurker.tag] = LurkerRole.CHOKE_GUARD
                self.lurker_positions[lurker.tag] = choke
                self.bot.do(lurker.move(choke))
                self.logger.info(
                    f"[{int(game_time)}s] [LURKER_POS] 럴커 초크 방어 할당: {choke}"
                )
                return

        # 확장 기지 방어
        for guard_pos in self._expansion_guard_positions:
            lurkers_at_guard = sum(
                1 for t, r in self.lurker_assignments.items()
                if r == LurkerRole.EXPANSION_GUARD
                and t in self.lurker_positions
                and self.lurker_positions[t].distance_to(guard_pos) < 8
            )
            if lurkers_at_guard < 2:
                self.lurker_assignments[lurker.tag] = LurkerRole.EXPANSION_GUARD
                self.lurker_positions[lurker.tag] = guard_pos
                self.bot.do(lurker.move(guard_pos))
                return

        # 전진 배치
        for fwd_pos in self._forward_positions:
            self.lurker_assignments[lurker.tag] = LurkerRole.FORWARD_POSITION
            self.lurker_positions[lurker.tag] = fwd_pos
            self.bot.do(lurker.move(fwd_pos))
            return

    async def _manage_choke_guard(self, lurker: Unit, game_time: float):
        """초크포인트 방어 럴커 관리"""
        target_pos = self.lurker_positions.get(lurker.tag)
        if not target_pos:
            self.lurker_assignments[lurker.tag] = LurkerRole.UNASSIGNED
            return

        # 위치에 도달하면 버로우
        if lurker.distance_to(target_pos) < 2:
            if not lurker.is_burrowed:
                await self._burrow_lurker(lurker)
                self.positions_held += 1
        else:
            # 위치로 이동
            if not lurker.is_burrowed:
                self.bot.do(lurker.move(target_pos))

    async def _manage_expansion_guard(self, lurker: Unit, game_time: float):
        """확장 기지 방어 럴커 관리"""
        target_pos = self.lurker_positions.get(lurker.tag)
        if not target_pos:
            self.lurker_assignments[lurker.tag] = LurkerRole.UNASSIGNED
            return

        if lurker.distance_to(target_pos) < 2:
            if not lurker.is_burrowed:
                await self._burrow_lurker(lurker)
        else:
            if not lurker.is_burrowed:
                self.bot.do(lurker.move(target_pos))

    async def _manage_forward_position(self, lurker: Unit, game_time: float):
        """전진 배치 럴커 관리"""
        target_pos = self.lurker_positions.get(lurker.tag)
        if not target_pos:
            self.lurker_assignments[lurker.tag] = LurkerRole.UNASSIGNED
            return

        # 적이 접근하면 버로우
        enemy_nearby = self._check_enemies_nearby(lurker, self.burrow_safe_distance)

        if enemy_nearby:
            if not lurker.is_burrowed:
                await self._burrow_lurker(lurker)
        else:
            # 위치에 없으면 이동
            if lurker.distance_to(target_pos) > 3 and not lurker.is_burrowed:
                self.bot.do(lurker.move(target_pos))

    async def _manage_retreat(self, lurker: Unit, game_time: float):
        """럴커 후퇴 관리"""
        retreat_pos = getattr(self.bot, "start_location", None)
        if not retreat_pos:
            self.lurker_assignments[lurker.tag] = LurkerRole.UNASSIGNED
            return

        if lurker.is_burrowed:
            await self._unburrow_lurker(lurker)
        else:
            self.bot.do(lurker.move(retreat_pos))
            if lurker.distance_to(retreat_pos) < 15:
                self.lurker_assignments[lurker.tag] = LurkerRole.UNASSIGNED

    async def _handle_detectors(self, game_time: float):
        """
        적 디텍터 대응

        디텍터가 감지되면:
        1. 언버로우
        2. 안전한 위치로 재배치
        3. 디텍터가 사라지면 다시 버로우
        """
        if not hasattr(self.bot, "enemy_units"):
            return

        enemy_units = self.bot.enemy_units
        if not enemy_units.exists:
            return

        for lurker_tag in list(self.lurker_assignments.keys()):
            lurker = self._find_unit(lurker_tag)
            if not lurker or not lurker.is_burrowed:
                continue

            # 적 디텍터 확인
            detectors_nearby = enemy_units.filter(
                lambda u: u.type_id in self.detector_types
                and u.distance_to(lurker) < self.unburrow_detector_range
            )

            if detectors_nearby.exists:
                # 디텍터 발견! 언버로우 + 재배치
                await self._unburrow_lurker(lurker)
                self.lurker_assignments[lurker_tag] = LurkerRole.RETREATING
                self.repositions += 1
                self.logger.info(
                    f"[{int(game_time)}s] [LURKER_POS] "
                    f"디텍터 감지! 럴커 재배치 (#{self.repositions})"
                )

    async def _burrow_lurker(self, lurker: Unit):
        """럴커 버로우"""
        if lurker.is_burrowed:
            return

        try:
            abilities = await self.bot.get_available_abilities(lurker)
            if AbilityId.BURROWDOWN_LURKER in abilities:
                self.bot.do(lurker(AbilityId.BURROWDOWN_LURKER))
                self.lurker_burrowed[lurker.tag] = True
        except Exception:
            pass

    async def _unburrow_lurker(self, lurker: Unit):
        """럴커 언버로우"""
        if not lurker.is_burrowed:
            return

        try:
            abilities = await self.bot.get_available_abilities(lurker)
            if AbilityId.BURROWUP_LURKER in abilities:
                self.bot.do(lurker(AbilityId.BURROWUP_LURKER))
                self.lurker_burrowed[lurker.tag] = False
        except Exception:
            pass

    def _check_enemies_nearby(self, lurker: Unit, distance: float) -> bool:
        """주변 적 유닛 확인"""
        enemy_units = getattr(self.bot, "enemy_units", None)
        if not enemy_units or not enemy_units.exists:
            return False

        nearby = enemy_units.closer_than(distance, lurker)
        ground = nearby.filter(lambda u: not u.is_flying)
        return ground.exists and ground.amount > 0

    def _find_unit(self, tag: int) -> Optional[Unit]:
        """태그로 유닛 찾기"""
        if not hasattr(self.bot, "units"):
            return None
        return self.bot.units.find_by_tag(tag)

    def _print_report(self, game_time: float):
        """럴커 포지셔닝 보고"""
        role_counts = {}
        for role in self.lurker_assignments.values():
            role_counts[role.value] = role_counts.get(role.value, 0) + 1

        self.logger.info(
            f"[{int(game_time)}s] [LURKER_POS] 보고: "
            f"배치 {len(self.lurker_assignments)}기 | "
            f"역할: {role_counts} | "
            f"방어 {self.positions_held} | 재배치 {self.repositions}"
        )

    def get_position_stats(self) -> Dict:
        """
        럴커 포지셔닝 통계 반환

        Returns:
            통계 딕셔너리
        """
        role_counts = {}
        for role in self.lurker_assignments.values():
            role_counts[role.value] = role_counts.get(role.value, 0) + 1

        return {
            "total_lurkers": len(self.lurker_assignments),
            "roles": role_counts,
            "choke_points": len(self._choke_points),
            "range": self.lurker_range,
            "positions_held": self.positions_held,
            "repositions": self.repositions,
        }
