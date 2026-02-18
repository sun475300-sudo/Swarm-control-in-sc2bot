# -*- coding: utf-8 -*-
"""
Feature #92: Queen Walk 러시 매니저

퀸 + 저글링 조합을 활용한 초반 러시 전술:
1. 퀸 트랜스퓨전으로 체력 관리하며 전진
2. 저글링과 연계한 협공
3. 퀸 체력 기반 후퇴 판단
4. 크립 종양 설치하며 전진 (시야 확보)
"""

from typing import Dict, List, Optional, Set
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


class QueenWalkPhase(Enum):
    """퀸 워크 전술 단계"""
    IDLE = "idle"
    PREPARING = "preparing"  # 퀸 + 저글링 집결
    ADVANCING = "advancing"  # 전진 중
    ENGAGING = "engaging"    # 교전 중
    RETREATING = "retreating"  # 후퇴 중


class QueenWalkManager:
    """
    퀸 워크 러시 매니저

    초반(3~5분)에 퀸 2~3기와 저글링 8~16기를 조합하여
    적 내추럴 확장을 압박하는 전술입니다.

    핵심 메커니즘:
    - 퀸의 트랜스퓨전으로 탱킹하며 전진
    - 저글링이 주변 유닛을 처리
    - 퀸 체력이 40% 이하 시 후퇴 판단
    - 크립 종양을 설치하며 시야 확보
    """

    def __init__(self, bot):
        """
        퀸 워크 매니저 초기화

        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot
        self.logger = get_logger("QueenWalk")

        # 전술 상태
        self.phase = QueenWalkPhase.IDLE
        self.walk_active: bool = False

        # 할당된 유닛
        self.queen_tags: Set[int] = set()      # 퀸 워크에 참여하는 퀸
        self.zergling_tags: Set[int] = set()   # 호위 저글링
        self.rally_point: Optional[Point2] = None  # 집결 지점
        self.target_point: Optional[Point2] = None  # 공격 목표

        # 전술 파라미터
        self.min_queens: int = 2            # 최소 퀸 수
        self.min_zerglings: int = 8         # 최소 저글링 수
        self.queen_retreat_hp: float = 0.4  # 퀸 후퇴 체력 비율
        self.queen_heal_hp: float = 0.7     # 트랜스퓨전 시작 체력
        self.transfusion_energy: int = 50   # 트랜스퓨전 필요 에너지
        self.max_game_time: float = 360.0   # 최대 실행 시간 (6분)
        self.creep_tumor_interval: float = 15.0  # 크립 종양 설치 간격

        # 타이밍
        self.walk_start_time: float = 0.0
        self.last_transfusion_time: float = 0.0
        self.last_creep_tumor_time: float = 0.0

        # 통계
        self.walks_attempted: int = 0
        self.walks_successful: int = 0  # 적 기지 파괴 성공
        self.total_damage_dealt: float = 0.0

    async def on_step(self, iteration: int):
        """
        매 프레임 퀸 워크 전술 업데이트

        Args:
            iteration: 현재 게임 반복 횟수
        """
        try:
            if not UnitTypeId:
                return

            game_time = getattr(self.bot, "time", 0.0)

            if self.phase == QueenWalkPhase.IDLE:
                if iteration % 66 == 0:
                    self._evaluate_queen_walk(game_time)

            elif self.phase == QueenWalkPhase.PREPARING:
                if iteration % 22 == 0:
                    await self._gather_forces(game_time)

            elif self.phase == QueenWalkPhase.ADVANCING:
                if iteration % 8 == 0:
                    await self._advance(game_time)

            elif self.phase == QueenWalkPhase.ENGAGING:
                if iteration % 4 == 0:
                    await self._manage_engagement(game_time)

            elif self.phase == QueenWalkPhase.RETREATING:
                if iteration % 8 == 0:
                    await self._execute_retreat(game_time)

            # 시간 초과 체크
            if self.walk_active and game_time > self.max_game_time:
                self._end_queen_walk("시간 초과")

        except Exception as e:
            if iteration % 100 == 0:
                self.logger.error(f"[QUEEN_WALK] Error: {e}")

    def _evaluate_queen_walk(self, game_time: float):
        """
        퀸 워크 실행 여부 평가

        조건:
        1. 게임 시간 2~5분
        2. 퀸 2기 이상
        3. 저글링 8기 이상
        4. 이미 진행 중이 아닐 때
        """
        if self.walk_active:
            return

        # 시간 조건: 2분~5분
        if game_time < 120 or game_time > 300:
            return

        if not hasattr(self.bot, "units"):
            return

        queens = self.bot.units(UnitTypeId.QUEEN)
        zerglings = self.bot.units(UnitTypeId.ZERGLING)

        if queens.amount < self.min_queens:
            return
        if zerglings.amount < self.min_zerglings:
            return

        # 목표 지점 설정 (적 내추럴)
        target = self._find_attack_target()
        if not target:
            return

        self.target_point = target
        self.phase = QueenWalkPhase.PREPARING
        self.walk_active = True
        self.walk_start_time = game_time
        self.walks_attempted += 1

        # 퀸 할당 (인젝트용 퀸 1기는 남기기)
        queens_for_walk = list(queens)[:min(queens.amount - 1, 3)]
        self.queen_tags = {q.tag for q in queens_for_walk}

        # 저글링 할당
        lings_for_walk = list(zerglings)[:16]
        self.zergling_tags = {z.tag for z in lings_for_walk}

        # 집결 지점 (아군 내추럴 앞)
        if hasattr(self.bot, "start_location"):
            direction = target - self.bot.start_location
            length = (direction.x ** 2 + direction.y ** 2) ** 0.5
            if length > 0:
                nx, ny = direction.x / length, direction.y / length
                self.rally_point = Point2((
                    self.bot.start_location.x + nx * 20,
                    self.bot.start_location.y + ny * 20,
                ))

        self.logger.info(
            f"[{int(game_time)}s] [QUEEN_WALK] 퀸 워크 개시! "
            f"퀸 {len(self.queen_tags)}기, 저글링 {len(self.zergling_tags)}기"
        )

    def _find_attack_target(self) -> Optional[Point2]:
        """공격 목표 찾기 (적 내추럴 우선)"""
        if not hasattr(self.bot, "enemy_start_locations") or not self.bot.enemy_start_locations:
            return None

        enemy_start = self.bot.enemy_start_locations[0]

        # 적 내추럴 확장 위치 추정
        expansions = getattr(self.bot, "expansion_locations_list", [])
        if expansions:
            # 적 본진에서 가장 가까운 확장 위치 = 적 내추럴
            enemy_natural = min(
                [exp for exp in expansions if exp.distance_to(enemy_start) > 5],
                key=lambda exp: exp.distance_to(enemy_start),
                default=None,
            )
            if enemy_natural:
                return enemy_natural

        return enemy_start

    async def _gather_forces(self, game_time: float):
        """유닛 집결"""
        if not self.rally_point:
            self.phase = QueenWalkPhase.ADVANCING
            return

        all_gathered = True

        # 퀸 집결
        for tag in list(self.queen_tags):
            queen = self._find_unit(tag)
            if queen:
                if queen.distance_to(self.rally_point) > 5:
                    self.bot.do(queen.move(self.rally_point))
                    all_gathered = False
            else:
                self.queen_tags.discard(tag)

        # 저글링 집결
        for tag in list(self.zergling_tags):
            ling = self._find_unit(tag)
            if ling:
                if ling.distance_to(self.rally_point) > 5:
                    self.bot.do(ling.move(self.rally_point))
                    all_gathered = False
            else:
                self.zergling_tags.discard(tag)

        # 모두 집결 완료 또는 10초 경과
        if all_gathered or (game_time - self.walk_start_time > 10):
            self.phase = QueenWalkPhase.ADVANCING
            self.logger.info(
                f"[{int(game_time)}s] [QUEEN_WALK] 집결 완료, 전진 개시!"
            )

    async def _advance(self, game_time: float):
        """목표를 향해 전진"""
        if not self.target_point:
            self._end_queen_walk("목표 없음")
            return

        # 퀸 생존 확인
        if not self.queen_tags:
            self._end_queen_walk("퀸 전멸")
            return

        # 적 유닛 감지 시 교전 모드로 전환
        enemy_nearby = self._detect_nearby_enemies()
        if enemy_nearby:
            self.phase = QueenWalkPhase.ENGAGING
            return

        # 퀸을 선두로 전진
        for tag in self.queen_tags:
            queen = self._find_unit(tag)
            if queen:
                self.bot.do(queen.attack(self.target_point))

                # 크립 종양 설치 (에너지 충분하고 쿨다운 지남)
                if (queen.energy >= self.transfusion_energy + 25 and
                        game_time - self.last_creep_tumor_time > self.creep_tumor_interval):
                    await self._place_creep_tumor(queen, game_time)

        # 저글링은 퀸 주변에서 호위
        queen_center = self._get_queen_center()
        if queen_center:
            for tag in self.zergling_tags:
                ling = self._find_unit(tag)
                if ling:
                    # 퀸보다 약간 앞에서 정찰
                    if self.target_point:
                        forward_pos = queen_center.towards(self.target_point, 3)
                        self.bot.do(ling.attack(forward_pos))

    async def _manage_engagement(self, game_time: float):
        """
        교전 관리

        핵심:
        - 퀸 트랜스퓨전으로 탱킹
        - 저글링으로 서라운드
        - 퀸 체력 임계값 시 후퇴
        """
        # 퀸 체력 확인 및 트랜스퓨전
        queens_alive = []
        should_retreat = False

        for tag in list(self.queen_tags):
            queen = self._find_unit(tag)
            if not queen:
                self.queen_tags.discard(tag)
                continue
            queens_alive.append(queen)

            # 후퇴 판단
            if queen.health_percentage < self.queen_retreat_hp:
                should_retreat = True

        if should_retreat or not queens_alive:
            self.phase = QueenWalkPhase.RETREATING
            self.logger.info(
                f"[{int(game_time)}s] [QUEEN_WALK] 퀸 체력 위험! 후퇴 시작"
            )
            return

        # 트랜스퓨전 실행 (체력 낮은 퀸에게)
        for queen in queens_alive:
            if queen.energy >= self.transfusion_energy:
                # 체력이 가장 낮은 퀸 찾기
                lowest_hp_queen = min(
                    queens_alive,
                    key=lambda q: q.health_percentage,
                )
                if lowest_hp_queen.health_percentage < self.queen_heal_hp:
                    try:
                        self.bot.do(queen(AbilityId.TRANSFUSION_TRANSFUSION, lowest_hp_queen))
                        self.last_transfusion_time = game_time
                    except Exception:
                        pass
                    break  # 한 프레임에 하나만

        # 저글링은 적 유닛 공격
        enemy_units = getattr(self.bot, "enemy_units", None)
        if enemy_units and enemy_units.exists:
            for tag in list(self.zergling_tags):
                ling = self._find_unit(tag)
                if ling:
                    closest_enemy = enemy_units.closest_to(ling)
                    self.bot.do(ling.attack(closest_enemy))
                else:
                    self.zergling_tags.discard(tag)

        # 퀸도 공격 (적 유닛이 가까이 있으면)
        for queen in queens_alive:
            if enemy_units and enemy_units.exists:
                closest = enemy_units.closest_to(queen)
                if closest.distance_to(queen) < 8:
                    self.bot.do(queen.attack(closest))

        # 적이 사라지면 다시 전진
        if not self._detect_nearby_enemies():
            self.phase = QueenWalkPhase.ADVANCING

    async def _execute_retreat(self, game_time: float):
        """퀸 워크 후퇴 실행"""
        retreat_pos = getattr(self.bot, "start_location", None)
        if not retreat_pos:
            self._end_queen_walk("후퇴 위치 없음")
            return

        all_retreated = True

        # 퀸 후퇴 (트랜스퓨전하며)
        queens_alive = []
        for tag in list(self.queen_tags):
            queen = self._find_unit(tag)
            if queen:
                queens_alive.append(queen)
                self.bot.do(queen.move(retreat_pos))
                if queen.distance_to(retreat_pos) > 15:
                    all_retreated = False
            else:
                self.queen_tags.discard(tag)

        # 후퇴 중 트랜스퓨전
        for queen in queens_alive:
            if queen.energy >= self.transfusion_energy:
                low_hp_queen = min(queens_alive, key=lambda q: q.health_percentage)
                if low_hp_queen.health_percentage < 0.6:
                    try:
                        self.bot.do(queen(AbilityId.TRANSFUSION_TRANSFUSION, low_hp_queen))
                    except Exception:
                        pass
                    break

        # 저글링은 퀸 호위하며 후퇴
        for tag in list(self.zergling_tags):
            ling = self._find_unit(tag)
            if ling:
                self.bot.do(ling.move(retreat_pos))
            else:
                self.zergling_tags.discard(tag)

        if all_retreated:
            self._end_queen_walk("후퇴 완료")

    async def _place_creep_tumor(self, queen, game_time: float):
        """퀸으로 크립 종양 설치"""
        try:
            abilities = await self.bot.get_available_abilities(queen)
            if AbilityId.BUILD_CREEPTUMOR_QUEEN in abilities:
                # 퀸 앞쪽에 설치
                if self.target_point:
                    tumor_pos = queen.position.towards(self.target_point, 3)
                    self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, tumor_pos))
                    self.last_creep_tumor_time = game_time
        except Exception:
            pass

    def _detect_nearby_enemies(self) -> bool:
        """퀸 주변 적 유닛 감지"""
        queen_center = self._get_queen_center()
        if not queen_center:
            return False

        enemy_units = getattr(self.bot, "enemy_units", None)
        if not enemy_units or not enemy_units.exists:
            return False

        nearby = enemy_units.closer_than(12, queen_center)
        return nearby.exists and nearby.amount > 0

    def _get_queen_center(self) -> Optional[Point2]:
        """할당된 퀸들의 중심 위치"""
        positions = []
        for tag in self.queen_tags:
            queen = self._find_unit(tag)
            if queen:
                positions.append(queen.position)

        if not positions:
            return None

        avg_x = sum(p.x for p in positions) / len(positions)
        avg_y = sum(p.y for p in positions) / len(positions)
        return Point2((avg_x, avg_y))

    def _find_unit(self, tag: int) -> Optional[Unit]:
        """태그로 유닛 찾기"""
        if not hasattr(self.bot, "units"):
            return None
        return self.bot.units.find_by_tag(tag)

    def _end_queen_walk(self, reason: str):
        """퀸 워크 종료"""
        game_time = getattr(self.bot, "time", 0.0)
        self.logger.info(
            f"[{int(game_time)}s] [QUEEN_WALK] 퀸 워크 종료: {reason} "
            f"(퀸 {len(self.queen_tags)}기, 저글링 {len(self.zergling_tags)}기 생존)"
        )
        self.phase = QueenWalkPhase.IDLE
        self.walk_active = False
        self.queen_tags.clear()
        self.zergling_tags.clear()
        self.rally_point = None
        self.target_point = None

    def get_queen_walk_stats(self) -> Dict:
        """
        퀸 워크 통계 반환

        Returns:
            통계 딕셔너리
        """
        return {
            "phase": self.phase.value,
            "walk_active": self.walk_active,
            "queens_assigned": len(self.queen_tags),
            "zerglings_assigned": len(self.zergling_tags),
            "walks_attempted": self.walks_attempted,
            "walks_successful": self.walks_successful,
        }
