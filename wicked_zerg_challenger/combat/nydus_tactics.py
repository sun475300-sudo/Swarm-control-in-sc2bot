# -*- coding: utf-8 -*-
"""
Feature #91: Nydus Worm 전술 매니저

나이더스 웜을 활용한 기습 전술:
1. 적 자원 지역 뒤에 나이더스 웜 배치
2. 나이더스에서 유닛 투입/철수 관리
3. 나이더스 네트워크 건설 타이밍 관리
4. 다중 나이더스 출구 조율
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


class NydusPhase(Enum):
    """나이더스 전술 단계"""
    IDLE = "idle"
    BUILDING_NETWORK = "building_network"
    PLACING_WORM = "placing_worm"
    LOADING_UNITS = "loading_units"
    UNLOADING_UNITS = "unloading_units"
    RETREATING = "retreating"


class NydusTacticsManager:
    """
    나이더스 웜 전술 매니저

    적 자원 지역 후방에 나이더스 웜을 배치하여 기습 공격을 수행합니다.

    전술 흐름:
    1. 나이더스 네트워크 건설 (레어 이상 필요)
    2. 적 방어가 약한 위치 탐색
    3. 나이더스 웜 배치
    4. 유닛 투입 (저글링, 바퀴, 히드라 등)
    5. 상황에 따라 철수 또는 계속 투입
    """

    def __init__(self, bot):
        """
        나이더스 전술 매니저 초기화

        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot
        self.logger = get_logger("NydusTactics")

        # 전술 상태
        self.phase = NydusPhase.IDLE
        self.nydus_network_tag: Optional[int] = None
        self.active_worms: Dict[int, Point2] = {}  # worm_tag -> position
        self.units_in_nydus: Set[int] = set()  # 나이더스 안에 있는 유닛 태그

        # 타이밍 관리
        self.last_worm_attempt_time: float = 0.0
        self.worm_cooldown: float = 60.0  # 나이더스 웜 배치 쿨다운 (초)
        self.last_load_time: float = 0.0
        self.load_cooldown: float = 0.5  # 유닛 투입 간격

        # 전술 설정
        self.min_units_for_attack: int = 8  # 최소 투입 유닛 수
        self.retreat_hp_threshold: float = 0.3  # 나이더스 체력 30% 이하 시 철수
        self.max_worms: int = 3  # 최대 동시 나이더스 웜 수

        # 우선 투입 유닛 타입
        self.priority_unit_types = [
            UnitTypeId.ROACH if UnitTypeId else "ROACH",
            UnitTypeId.RAVAGER if UnitTypeId else "RAVAGER",
            UnitTypeId.HYDRALISK if UnitTypeId else "HYDRALISK",
            UnitTypeId.ZERGLING if UnitTypeId else "ZERGLING",
        ]

        # 통계
        self.worms_placed: int = 0
        self.units_deployed: int = 0
        self.successful_raids: int = 0

    async def on_step(self, iteration: int):
        """
        매 프레임 나이더스 전술 업데이트

        Args:
            iteration: 현재 게임 반복 횟수
        """
        try:
            if not UnitTypeId:
                return

            game_time = getattr(self.bot, "time", 0.0)

            # 나이더스 네트워크 존재 확인 (매 2초)
            if iteration % 44 == 0:
                self._check_nydus_network()

            # 나이더스 웜 상태 관리
            if iteration % 11 == 0:
                self._clean_dead_worms()

            # 단계별 실행
            if self.phase == NydusPhase.IDLE:
                if iteration % 66 == 0:  # 3초마다 확인
                    await self._evaluate_nydus_opportunity(game_time)

            elif self.phase == NydusPhase.PLACING_WORM:
                if iteration % 22 == 0:
                    await self._attempt_place_worm(game_time)

            elif self.phase == NydusPhase.LOADING_UNITS:
                if iteration % 5 == 0:
                    await self._load_units_into_nydus(game_time)

            elif self.phase == NydusPhase.UNLOADING_UNITS:
                if iteration % 5 == 0:
                    await self._manage_unloading(game_time)

            elif self.phase == NydusPhase.RETREATING:
                if iteration % 11 == 0:
                    await self._manage_retreat(game_time)

            # 활성 나이더스 웜 방어 체크
            if iteration % 22 == 0 and self.active_worms:
                await self._check_worm_safety()

        except Exception as e:
            if iteration % 100 == 0:
                self.logger.error(f"[NYDUS] Error: {e}")

    def _check_nydus_network(self):
        """나이더스 네트워크 존재 확인"""
        if not hasattr(self.bot, "structures"):
            return

        networks = self.bot.structures(UnitTypeId.NYDUSNETWORK)
        if networks.exists:
            self.nydus_network_tag = networks.first.tag
        else:
            self.nydus_network_tag = None
            # 네트워크가 없으면 유휴 상태로
            if self.phase != NydusPhase.IDLE:
                self.phase = NydusPhase.IDLE

    def _clean_dead_worms(self):
        """파괴된 나이더스 웜 정리"""
        if not hasattr(self.bot, "structures"):
            return

        alive_worm_tags = set()
        nydus_canals = self.bot.structures(UnitTypeId.NYDUSCANAL)
        for worm in nydus_canals:
            alive_worm_tags.add(worm.tag)

        dead_worms = set(self.active_worms.keys()) - alive_worm_tags
        for tag in dead_worms:
            pos = self.active_worms.pop(tag, None)
            if pos:
                self.logger.info(f"[NYDUS] 나이더스 웜 파괴됨 at {pos}")

    async def _evaluate_nydus_opportunity(self, game_time: float):
        """
        나이더스 기습 기회 평가

        조건:
        1. 나이더스 네트워크가 있어야 함
        2. 쿨다운이 지났어야 함
        3. 투입할 유닛이 충분해야 함
        4. 적 방어가 약한 위치가 있어야 함
        """
        if not self.nydus_network_tag:
            return

        if game_time - self.last_worm_attempt_time < self.worm_cooldown:
            return

        if len(self.active_worms) >= self.max_worms:
            return

        # 투입 가능 유닛 수 확인
        available_units = self._count_available_units()
        if available_units < self.min_units_for_attack:
            return

        # 배치 위치 선정
        target_pos = self._find_worm_placement()
        if target_pos:
            self.phase = NydusPhase.PLACING_WORM
            self._pending_worm_target = target_pos
            self.logger.info(
                f"[{int(game_time)}s] [NYDUS] 나이더스 웜 배치 시도: {target_pos}"
            )

    def _count_available_units(self) -> int:
        """투입 가능한 유닛 수 계산"""
        if not hasattr(self.bot, "units"):
            return 0

        count = 0
        for unit_type in self.priority_unit_types:
            try:
                units = self.bot.units(unit_type)
                idle_units = units.idle if hasattr(units, "idle") else units
                count += idle_units.amount
            except Exception:
                continue
        return count

    def _find_worm_placement(self) -> Optional[Point2]:
        """
        나이더스 웜 배치 최적 위치 탐색

        우선순위:
        1. 적 자원 지역 뒤 (미네랄 라인)
        2. 적 확장 기지 근처
        3. 적 본진 후방

        Returns:
            최적 배치 위치 또는 None
        """
        if not Point2:
            return None

        candidates: List[Tuple[Point2, float]] = []  # (position, priority_score)

        # 1. 적 기지 자원 지역 뒤
        enemy_structures = getattr(self.bot, "enemy_structures", None)
        if enemy_structures and enemy_structures.exists:
            enemy_bases = enemy_structures.filter(
                lambda s: s.type_id in {
                    UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE,
                    UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND,
                    UnitTypeId.PLANETARYFORTRESS, UnitTypeId.NEXUS,
                }
            )
            for base in enemy_bases:
                behind_pos = self._calculate_behind_mineral_line(base)
                if behind_pos:
                    # 우리 본진에서 멀수록 = 적 확장기지 = 방어 약함
                    dist_from_enemy_main = 0
                    if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
                        dist_from_enemy_main = base.distance_to(
                            self.bot.enemy_start_locations[0]
                        )
                    score = dist_from_enemy_main  # 멀수록 높은 점수 (방어 약한 곳)
                    candidates.append((behind_pos, score))

        # 2. 적 시작 위치 후방 (기본 폴백)
        if not candidates:
            if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
                enemy_start = self.bot.enemy_start_locations[0]
                if hasattr(self.bot, "start_location"):
                    our_start = self.bot.start_location
                    # 적 본진 뒤쪽 (우리 방향 반대)
                    dx = enemy_start.x - our_start.x
                    dy = enemy_start.y - our_start.y
                    length = (dx ** 2 + dy ** 2) ** 0.5
                    if length > 0:
                        nx, ny = dx / length, dy / length
                        behind_pos = Point2((
                            enemy_start.x + nx * 8,
                            enemy_start.y + ny * 8,
                        ))
                        candidates.append((behind_pos, 0))

        if not candidates:
            return None

        # 기존 나이더스 웜과 겹치지 않는 위치 선택
        best_pos = None
        best_score = -1
        for pos, score in candidates:
            too_close = False
            for worm_pos in self.active_worms.values():
                if pos.distance_to(worm_pos) < 15:
                    too_close = True
                    break
            if not too_close and score > best_score:
                best_score = score
                best_pos = pos

        return best_pos if best_pos else (candidates[0][0] if candidates else None)

    def _calculate_behind_mineral_line(self, base) -> Optional[Point2]:
        """
        기지 미네랄 라인 뒤쪽 위치 계산

        Args:
            base: 적 기지 유닛

        Returns:
            미네랄 라인 뒤 위치
        """
        if not hasattr(self.bot, "mineral_field"):
            return None

        nearby_minerals = self.bot.mineral_field.closer_than(10, base)
        if not nearby_minerals or nearby_minerals.amount == 0:
            return None

        # 미네랄 중심점 계산
        mineral_center = nearby_minerals.center
        # 기지에서 미네랄 방향의 반대쪽으로 6 거리
        dx = mineral_center.x - base.position.x
        dy = mineral_center.y - base.position.y
        length = (dx ** 2 + dy ** 2) ** 0.5
        if length == 0:
            return None

        nx, ny = dx / length, dy / length
        behind_pos = Point2((
            mineral_center.x + nx * 6,
            mineral_center.y + ny * 6,
        ))
        return behind_pos

    async def _attempt_place_worm(self, game_time: float):
        """나이더스 웜 배치 시도"""
        target_pos = getattr(self, "_pending_worm_target", None)
        if not target_pos:
            self.phase = NydusPhase.IDLE
            return

        # 나이더스 네트워크 찾기
        if not hasattr(self.bot, "structures"):
            self.phase = NydusPhase.IDLE
            return

        networks = self.bot.structures(UnitTypeId.NYDUSNETWORK)
        if not networks.exists:
            self.phase = NydusPhase.IDLE
            return

        network = networks.first

        # 나이더스 웜 생성 능력 사용
        try:
            abilities = await self.bot.get_available_abilities(network)
            if AbilityId.BUILD_NYDUSWORM in abilities:
                self.bot.do(network(AbilityId.BUILD_NYDUSWORM, target_pos))
                self.last_worm_attempt_time = game_time
                self.worms_placed += 1
                self.phase = NydusPhase.LOADING_UNITS
                self.logger.info(
                    f"[{int(game_time)}s] [NYDUS] 나이더스 웜 건설 시작! 위치: {target_pos}"
                )
            else:
                # 쿨다운 또는 자원 부족
                self.phase = NydusPhase.IDLE
        except Exception as e:
            self.logger.warning(f"[NYDUS] 나이더스 웜 배치 실패: {e}")
            self.phase = NydusPhase.IDLE

        self._pending_worm_target = None

    async def _load_units_into_nydus(self, game_time: float):
        """나이더스 네트워크에 유닛 투입"""
        if game_time - self.last_load_time < self.load_cooldown:
            return

        if not hasattr(self.bot, "structures") or not hasattr(self.bot, "units"):
            return

        networks = self.bot.structures(UnitTypeId.NYDUSNETWORK)
        if not networks.exists:
            self.phase = NydusPhase.IDLE
            return

        network = networks.first

        # 투입할 유닛 선택
        for unit_type in self.priority_unit_types:
            try:
                units = self.bot.units(unit_type).idle
                for unit in units:
                    if unit.tag not in self.units_in_nydus:
                        if unit.distance_to(network) < 5:
                            # 나이더스에 탑승
                            self.bot.do(unit(AbilityId.LOAD_NYDUSNETWORK, network))
                            self.units_in_nydus.add(unit.tag)
                            self.units_deployed += 1
                            self.last_load_time = game_time
                            return  # 한 번에 하나씩
                        else:
                            # 나이더스 네트워크로 이동
                            self.bot.do(unit.move(network.position))
            except Exception:
                continue

        # 충분한 유닛이 탑승했으면 언로딩 단계로 전환
        if len(self.units_in_nydus) >= self.min_units_for_attack:
            # 나이더스 웜 확인
            canals = self.bot.structures(UnitTypeId.NYDUSCANAL)
            if canals.exists:
                for canal in canals:
                    if canal.tag not in self.active_worms:
                        self.active_worms[canal.tag] = canal.position
                self.phase = NydusPhase.UNLOADING_UNITS
                self.logger.info(
                    f"[{int(game_time)}s] [NYDUS] {len(self.units_in_nydus)}기 투입 완료, "
                    f"언로딩 개시!"
                )

    async def _manage_unloading(self, game_time: float):
        """나이더스 웜에서 유닛 언로딩 관리"""
        if not hasattr(self.bot, "structures"):
            return

        canals = self.bot.structures(UnitTypeId.NYDUSCANAL)
        if not canals.exists:
            self.phase = NydusPhase.IDLE
            self.units_in_nydus.clear()
            return

        # 나이더스 웜에서 모든 유닛 하차
        for canal in canals:
            try:
                abilities = await self.bot.get_available_abilities(canal)
                if AbilityId.UNLOADALL_NYDUSWORM in abilities:
                    self.bot.do(canal(AbilityId.UNLOADALL_NYDUSWORM))
            except Exception:
                continue

        # 하차된 유닛은 주변 적 공격
        self.units_in_nydus.clear()
        self.phase = NydusPhase.IDLE
        self.successful_raids += 1
        self.logger.info(
            f"[{int(game_time)}s] [NYDUS] 기습 완료! (총 {self.successful_raids}회)"
        )

    async def _manage_retreat(self, game_time: float):
        """나이더스를 통한 철수 관리"""
        if not hasattr(self.bot, "structures"):
            self.phase = NydusPhase.IDLE
            return

        canals = self.bot.structures(UnitTypeId.NYDUSCANAL)
        if not canals.exists:
            self.phase = NydusPhase.IDLE
            return

        # 나이더스 근처 아군 유닛을 안으로 대피
        for canal in canals:
            if not hasattr(self.bot, "units"):
                continue
            nearby_units = self.bot.units.closer_than(10, canal)
            for unit in nearby_units:
                if unit.type_id in {
                    UnitTypeId.ZERGLING, UnitTypeId.ROACH,
                    UnitTypeId.HYDRALISK, UnitTypeId.RAVAGER,
                }:
                    if unit.health_percentage < 0.5:
                        self.bot.do(unit(AbilityId.LOAD_NYDUSNETWORK, canal))

        self.phase = NydusPhase.IDLE

    async def _check_worm_safety(self):
        """활성 나이더스 웜 안전 체크"""
        if not hasattr(self.bot, "structures"):
            return

        canals = self.bot.structures(UnitTypeId.NYDUSCANAL)
        for canal in canals:
            if canal.tag in self.active_worms:
                # 체력이 낮으면 철수 모드
                if canal.health_percentage < self.retreat_hp_threshold:
                    self.phase = NydusPhase.RETREATING
                    self.logger.info(
                        f"[{int(self.bot.time)}s] [NYDUS] 나이더스 웜 위험! "
                        f"체력: {canal.health_percentage * 100:.0f}% - 철수 개시"
                    )
                    break

    def get_nydus_stats(self) -> Dict:
        """
        나이더스 전술 통계 반환

        Returns:
            전술 통계 딕셔너리
        """
        return {
            "phase": self.phase.value,
            "active_worms": len(self.active_worms),
            "worms_placed": self.worms_placed,
            "units_deployed": self.units_deployed,
            "successful_raids": self.successful_raids,
            "has_network": self.nydus_network_tag is not None,
        }
