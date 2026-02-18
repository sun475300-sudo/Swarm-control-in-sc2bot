# -*- coding: utf-8 -*-
"""
Feature #93: 바네 폭탄 전술 매니저

바네링을 별도 그룹으로 관리하여 적 밀집 지역에서 폭발시키는 전술:
1. 일꾼 라인 바네 투하 (드롭 연계)
2. 적 밀집 지역 폭발 (최대 AOE 데미지)
3. 바네링 별도 컨트롤 그룹 관리
4. 저글링과 연계한 바네 돌진

기존 BanelingTacticsController는 '지뢰(Burrow) 모드'를 담당하고,
이 BanelingTacticsManager는 '폭탄(Bomb Rush) 모드'를 담당합니다.
"""

from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
    from sc2.unit import Unit
    from sc2.units import Units
except ImportError:
    AbilityId = None
    UnitTypeId = None
    Point2 = None
    Unit = None
    Units = None

from utils.logger import get_logger


class BanelingBombMode(Enum):
    """바네 폭탄 모드"""
    IDLE = "idle"
    GATHERING = "gathering"       # 바네링 그룹 집결
    WORKER_LINE_RUSH = "worker_line"  # 일꾼 라인 타겟
    ARMY_BOMB = "army_bomb"       # 적 군대 밀집 타겟
    SPEED_RUSH = "speed_rush"     # 고속 돌진


class BanelingTacticsManager:
    """
    바네 폭탄 전술 매니저

    바네링을 별도 컨트롤 그룹으로 관리하여
    적 일꾼 라인이나 밀집 군대에 최대 스플래시 데미지를 입힙니다.

    핵심 전술:
    - 일꾼 라인 폭격: 바네링 4~6기를 적 미네랄 라인으로 돌진
    - 군대 폭격: 적 밀집 시 바네링 그룹 돌진 (저글링 서라운드와 연계)
    - 고속 돌진: 이동속도 업그레이드 후 고속 돌진
    """

    def __init__(self, bot):
        """
        바네 폭탄 매니저 초기화

        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot
        self.logger = get_logger("BanelingBomb")

        # 전술 상태
        self.mode = BanelingBombMode.IDLE

        # 바네링 그룹 관리
        self.bomb_squad: Set[int] = set()        # 폭탄 임무 바네링 태그
        self.escort_zerglings: Set[int] = set()  # 호위 저글링 태그
        self.bomb_target: Optional[Point2] = None  # 폭탄 목표 위치

        # 전술 파라미터
        self.min_banelings_for_bomb: int = 4     # 최소 바네링 수
        self.max_banelings_per_squad: int = 10   # 그룹당 최대 바네링
        self.worker_line_priority: float = 0.7   # 일꾼 라인 우선도
        self.density_threshold: int = 5          # 적 밀집 판단 기준 (5기 이상)
        self.density_radius: float = 4.0         # 밀집 판단 반경
        self.explode_range: float = 2.5          # 자폭 사거리

        # 쿨다운
        self.last_bomb_time: float = 0.0
        self.bomb_cooldown: float = 30.0  # 폭탄 시도 쿨다운

        # 통계
        self.bombs_launched: int = 0
        self.worker_kills_estimated: int = 0
        self.army_kills_estimated: int = 0

    async def on_step(self, iteration: int):
        """
        매 프레임 바네 폭탄 전술 업데이트

        Args:
            iteration: 현재 게임 반복 횟수
        """
        try:
            if not UnitTypeId:
                return

            game_time = getattr(self.bot, "time", 0.0)

            # 죽은 바네링 정리
            if iteration % 22 == 0:
                self._clean_dead_units()

            if self.mode == BanelingBombMode.IDLE:
                if iteration % 44 == 0:
                    self._evaluate_bomb_opportunity(game_time)

            elif self.mode == BanelingBombMode.GATHERING:
                if iteration % 11 == 0:
                    await self._gather_bomb_squad(game_time)

            elif self.mode == BanelingBombMode.WORKER_LINE_RUSH:
                if iteration % 4 == 0:
                    await self._execute_worker_line_bomb(game_time)

            elif self.mode == BanelingBombMode.ARMY_BOMB:
                if iteration % 4 == 0:
                    await self._execute_army_bomb(game_time)

            elif self.mode == BanelingBombMode.SPEED_RUSH:
                if iteration % 4 == 0:
                    await self._execute_speed_rush(game_time)

        except Exception as e:
            if iteration % 100 == 0:
                self.logger.error(f"[BANE_BOMB] Error: {e}")

    def _clean_dead_units(self):
        """파괴된 유닛 정리"""
        if not hasattr(self.bot, "units"):
            return

        alive_tags = {u.tag for u in self.bot.units}
        self.bomb_squad = self.bomb_squad & alive_tags
        self.escort_zerglings = self.escort_zerglings & alive_tags

        # 바네링 모두 소진 시 리셋
        if self.mode != BanelingBombMode.IDLE and not self.bomb_squad:
            self.mode = BanelingBombMode.IDLE
            self.bomb_target = None

    def _evaluate_bomb_opportunity(self, game_time: float):
        """
        바네 폭탄 기회 평가

        평가 기준:
        1. 바네링 수 충분한지
        2. 적 일꾼 밀집 지역 존재하는지
        3. 적 군대 밀집 지역 존재하는지
        """
        if self.mode != BanelingBombMode.IDLE:
            return

        if game_time - self.last_bomb_time < self.bomb_cooldown:
            return

        if not hasattr(self.bot, "units"):
            return

        banelings = self.bot.units(UnitTypeId.BANELING)
        if banelings.amount < self.min_banelings_for_bomb:
            return

        # 적 일꾼 라인 밀집 확인
        worker_target = self._find_dense_worker_line()
        if worker_target:
            self._setup_bomb_squad(banelings, worker_target, BanelingBombMode.WORKER_LINE_RUSH)
            return

        # 적 군대 밀집 확인
        army_target = self._find_dense_enemy_army()
        if army_target:
            self._setup_bomb_squad(banelings, army_target, BanelingBombMode.ARMY_BOMB)
            return

    def _find_dense_worker_line(self) -> Optional[Point2]:
        """
        적 일꾼 밀집 지역 탐색

        Returns:
            밀집 일꾼 라인 위치 또는 None
        """
        enemy_units = getattr(self.bot, "enemy_units", None)
        if not enemy_units or not enemy_units.exists:
            return None

        # 적 일꾼 필터링
        workers = enemy_units.filter(
            lambda u: u.type_id in {
                UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV,
                UnitTypeId.MULE,
            }
        )

        if workers.amount < self.density_threshold:
            return None

        # 밀집 지역 탐색 (클러스터링)
        best_pos = None
        best_count = 0

        for worker in workers:
            nearby = workers.closer_than(self.density_radius, worker)
            if nearby.amount > best_count:
                best_count = nearby.amount
                best_pos = nearby.center

        if best_count >= self.density_threshold:
            return best_pos
        return None

    def _find_dense_enemy_army(self) -> Optional[Point2]:
        """
        적 군대 밀집 지역 탐색

        Returns:
            밀집 군대 위치 또는 None
        """
        enemy_units = getattr(self.bot, "enemy_units", None)
        if not enemy_units or not enemy_units.exists:
            return None

        # 전투 유닛 필터링 (지상 유닛만)
        ground_army = enemy_units.filter(
            lambda u: u.can_attack_ground and not u.is_flying and not u.is_structure
        )

        if ground_army.amount < self.density_threshold:
            return None

        # 밀집도가 가장 높은 위치 탐색
        best_pos = None
        best_count = 0

        for unit in ground_army:
            nearby = ground_army.closer_than(self.density_radius, unit)
            if nearby.amount > best_count:
                best_count = nearby.amount
                best_pos = nearby.center

        if best_count >= self.density_threshold:
            return best_pos
        return None

    def _setup_bomb_squad(self, banelings, target: Point2, mode: BanelingBombMode):
        """
        바네링 폭탄 그룹 설정

        Args:
            banelings: 사용 가능한 바네링
            target: 목표 위치
            mode: 작전 모드
        """
        # 목표에 가장 가까운 바네링부터 선택
        sorted_banes = sorted(
            banelings, key=lambda b: b.distance_to(target)
        )
        squad_size = min(len(sorted_banes), self.max_banelings_per_squad)
        self.bomb_squad = {b.tag for b in sorted_banes[:squad_size]}
        self.bomb_target = target
        self.mode = mode

        # 호위 저글링 할당
        if hasattr(self.bot, "units"):
            zerglings = self.bot.units(UnitTypeId.ZERGLING).idle
            escort_count = min(zerglings.amount, squad_size * 2)
            if escort_count > 0:
                closest_lings = zerglings.sorted(
                    key=lambda z: z.distance_to(target)
                )
                self.escort_zerglings = {z.tag for z in closest_lings[:escort_count]}

        self.logger.info(
            f"[{int(self.bot.time)}s] [BANE_BOMB] 폭탄 그룹 편성! "
            f"바네링 {len(self.bomb_squad)}기, 저글링 {len(self.escort_zerglings)}기 "
            f"모드: {mode.value}"
        )

    async def _gather_bomb_squad(self, game_time: float):
        """폭탄 그룹 집결"""
        if not self.bomb_target:
            self.mode = BanelingBombMode.IDLE
            return

        # 그룹 중심 계산
        positions = []
        for tag in self.bomb_squad:
            unit = self._find_unit(tag)
            if unit:
                positions.append(unit.position)

        if not positions:
            self.mode = BanelingBombMode.IDLE
            return

        center = Point2((
            sum(p.x for p in positions) / len(positions),
            sum(p.y for p in positions) / len(positions),
        ))

        # 집결 완료 판단
        all_close = all(
            p.distance_to(center) < 5 for p in positions
        )

        if all_close:
            # 원래 의도한 모드로 전환
            self.logger.info(f"[{int(game_time)}s] [BANE_BOMB] 집결 완료, 돌격 개시!")

    async def _execute_worker_line_bomb(self, game_time: float):
        """일꾼 라인 바네 폭탄 실행"""
        if not self.bomb_target:
            self.mode = BanelingBombMode.IDLE
            return

        # 바네링 돌진
        for tag in list(self.bomb_squad):
            bane = self._find_unit(tag)
            if not bane:
                self.bomb_squad.discard(tag)
                continue

            # 적 일꾼이 보이면 가장 밀집된 곳으로 돌진
            enemy_workers = self._get_nearby_workers(bane, 15)
            if enemy_workers:
                densest = self._find_densest_cluster(enemy_workers)
                if densest:
                    self.bot.do(bane.attack(densest))
                else:
                    self.bot.do(bane.attack(self.bomb_target))
            else:
                self.bot.do(bane.attack(self.bomb_target))

        # 호위 저글링도 따라감
        for tag in list(self.escort_zerglings):
            ling = self._find_unit(tag)
            if ling:
                self.bot.do(ling.attack(self.bomb_target))
            else:
                self.escort_zerglings.discard(tag)

        self.last_bomb_time = game_time
        self.bombs_launched += 1

    async def _execute_army_bomb(self, game_time: float):
        """적 군대 밀집 지역 바네 폭탄 실행"""
        if not self.bomb_target:
            self.mode = BanelingBombMode.IDLE
            return

        # 최신 밀집 위치 업데이트
        updated_target = self._find_dense_enemy_army()
        if updated_target:
            self.bomb_target = updated_target

        # 바네링 돌진 (스플래시 극대화)
        for tag in list(self.bomb_squad):
            bane = self._find_unit(tag)
            if not bane:
                self.bomb_squad.discard(tag)
                continue
            self.bot.do(bane.attack(self.bomb_target))

        # 저글링은 바네 뒤에서 따라가며 서라운드
        for tag in list(self.escort_zerglings):
            ling = self._find_unit(tag)
            if ling:
                self.bot.do(ling.attack(self.bomb_target))
            else:
                self.escort_zerglings.discard(tag)

        self.last_bomb_time = game_time
        self.bombs_launched += 1

    async def _execute_speed_rush(self, game_time: float):
        """고속 돌진 모드 (이동속도 업 이후)"""
        # army_bomb과 유사하지만 분산 돌진
        if not self.bomb_target:
            self.mode = BanelingBombMode.IDLE
            return

        # 바네링을 분산시켜 스플래시 회피 방지
        bane_list = []
        for tag in list(self.bomb_squad):
            bane = self._find_unit(tag)
            if bane:
                bane_list.append(bane)
            else:
                self.bomb_squad.discard(tag)

        if not bane_list:
            self.mode = BanelingBombMode.IDLE
            return

        # 부채꼴 형태로 돌진 (적이 분산 회피하기 어렵게)
        for i, bane in enumerate(bane_list):
            offset_x = (i - len(bane_list) / 2) * 1.5
            target = Point2((
                self.bomb_target.x + offset_x,
                self.bomb_target.y,
            ))
            self.bot.do(bane.attack(target))

        self.last_bomb_time = game_time
        self.bombs_launched += 1

    def _get_nearby_workers(self, unit, radius: float):
        """주변 적 일꾼 찾기"""
        enemy_units = getattr(self.bot, "enemy_units", None)
        if not enemy_units or not enemy_units.exists:
            return None

        workers = enemy_units.filter(
            lambda u: u.type_id in {
                UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV,
            }
        )
        nearby = workers.closer_than(radius, unit)
        return nearby if nearby.exists else None

    def _find_densest_cluster(self, units) -> Optional[Point2]:
        """유닛 그룹에서 가장 밀집된 위치 찾기"""
        if not units or units.amount == 0:
            return None

        best_pos = None
        best_count = 0

        for u in units:
            nearby = units.closer_than(3, u)
            if nearby.amount > best_count:
                best_count = nearby.amount
                best_pos = nearby.center

        return best_pos

    def _find_unit(self, tag: int) -> Optional[Unit]:
        """태그로 유닛 찾기"""
        if not hasattr(self.bot, "units"):
            return None
        return self.bot.units.find_by_tag(tag)

    def get_bomb_stats(self) -> Dict:
        """
        바네 폭탄 통계 반환

        Returns:
            통계 딕셔너리
        """
        return {
            "mode": self.mode.value,
            "squad_size": len(self.bomb_squad),
            "escort_size": len(self.escort_zerglings),
            "bombs_launched": self.bombs_launched,
            "worker_kills_est": self.worker_kills_estimated,
            "army_kills_est": self.army_kills_estimated,
        }
