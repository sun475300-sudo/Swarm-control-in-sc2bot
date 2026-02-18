# -*- coding: utf-8 -*-
"""
Feature #94: Doom Drop 전술 매니저

오버로드에 대량의 유닛을 탑승시켜 적 본진에 투하하는 전술:
1. 오버로드(수송)에 유닛 탑승
2. 적 방어가 약한 곳 탐색
3. 적 본진/확장 기지에 유닛 투하
4. 다중 오버로드 조율
5. 대공 방어 회피 경로 계산

기존 OverlordTransport와의 차이:
- OverlordTransport: 소규모 견제 드롭 (2기)
- DoomDropManager: 대규모 올인 드롭 (4기+, 유닛 전부 투입)
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


class DoomDropPhase(Enum):
    """둠 드롭 단계"""
    IDLE = "idle"
    PREPARING = "preparing"        # Ventral Sacs 연구 대기
    LOADING = "loading"            # 유닛 탑승 중
    EN_ROUTE = "en_route"          # 이동 중
    DROPPING = "dropping"          # 투하 중
    ATTACKING = "attacking"        # 투하 후 공격 중
    RETREATING = "retreating"      # 오버로드 회수


class DoomDropManager:
    """
    Doom Drop 전술 매니저

    대규모 유닛을 오버로드에 탑승시켜 적 본진에 투하하는 올인 전술입니다.

    전술 흐름:
    1. Ventral Sacs 업그레이드 확인
    2. 오버로드 4기+ 확보
    3. 지상 유닛 탑승 (저글링/바퀴/히드라)
    4. 대공 위협 회피 경로로 이동
    5. 적 방어가 약한 위치에 투하
    6. 투하 후 유닛들 적 시설 공격
    """

    def __init__(self, bot):
        """
        Doom Drop 매니저 초기화

        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot
        self.logger = get_logger("DoomDrop")

        # 전술 상태
        self.phase = DoomDropPhase.IDLE
        self.drop_active: bool = False

        # 오버로드 관리
        self.transport_overlords: Dict[int, List[int]] = {}  # overlord_tag -> [unit_tags]
        self.drop_target: Optional[Point2] = None
        self.waypoints: List[Point2] = []  # 대공 회피 경로
        self.current_waypoint_idx: int = 0

        # 전술 파라미터
        self.min_overlords: int = 4           # 최소 오버로드 수
        self.min_supply_for_drop: int = 30    # 최소 투하 서플라이
        self.safe_distance_from_aa: float = 12.0  # 대공 위협 회피 거리
        self.drop_distance: float = 5.0       # 투하 시작 거리
        self.overlord_retreat_hp: float = 0.3  # 오버로드 후퇴 체력

        # 유닛 탑승 우선순위 (공격력 높은 유닛 우선)
        self.load_priority = [
            UnitTypeId.HYDRALISK if UnitTypeId else "HYDRALISK",
            UnitTypeId.ROACH if UnitTypeId else "ROACH",
            UnitTypeId.RAVAGER if UnitTypeId else "RAVAGER",
            UnitTypeId.ZERGLING if UnitTypeId else "ZERGLING",
            UnitTypeId.BANELING if UnitTypeId else "BANELING",
        ]

        # 쿨다운
        self.last_drop_time: float = 0.0
        self.drop_cooldown: float = 120.0  # 2분 쿨다운

        # Ventral Sacs 상태
        self.ventral_sacs_complete: bool = False

        # 통계
        self.drops_executed: int = 0
        self.units_dropped: int = 0

    async def on_step(self, iteration: int):
        """
        매 프레임 둠 드롭 전술 업데이트

        Args:
            iteration: 현재 게임 반복 횟수
        """
        try:
            if not UnitTypeId:
                return

            game_time = getattr(self.bot, "time", 0.0)

            # 업그레이드 확인 (매 5초)
            if iteration % 110 == 0:
                self._check_ventral_sacs()

            if self.phase == DoomDropPhase.IDLE:
                if iteration % 66 == 0:
                    self._evaluate_doom_drop(game_time)

            elif self.phase == DoomDropPhase.LOADING:
                if iteration % 8 == 0:
                    await self._load_units(game_time)

            elif self.phase == DoomDropPhase.EN_ROUTE:
                if iteration % 8 == 0:
                    await self._move_to_target(game_time)

            elif self.phase == DoomDropPhase.DROPPING:
                if iteration % 4 == 0:
                    await self._execute_drop(game_time)

            elif self.phase == DoomDropPhase.ATTACKING:
                if iteration % 22 == 0:
                    await self._manage_dropped_units(game_time)

            elif self.phase == DoomDropPhase.RETREATING:
                if iteration % 11 == 0:
                    await self._retreat_overlords(game_time)

            # 오버로드 안전 체크 (이동 중)
            if self.drop_active and iteration % 11 == 0:
                await self._check_overlord_safety()

        except Exception as e:
            if iteration % 100 == 0:
                self.logger.error(f"[DOOM_DROP] Error: {e}")

    def _check_ventral_sacs(self):
        """Ventral Sacs 업그레이드 확인"""
        if self.ventral_sacs_complete:
            return

        if not hasattr(self.bot, "state") or not UpgradeId:
            return

        if UpgradeId.OVERLORDTRANSPORT in self.bot.state.upgrades:
            self.ventral_sacs_complete = True
            self.logger.info("[DOOM_DROP] Ventral Sacs 완료! 둠 드롭 가능.")

    def _evaluate_doom_drop(self, game_time: float):
        """
        둠 드롭 실행 여부 평가

        조건:
        1. Ventral Sacs 완료
        2. 충분한 오버로드 (4기+)
        3. 충분한 지상 유닛
        4. 쿨다운 경과
        """
        if not self.ventral_sacs_complete:
            return

        if self.drop_active:
            return

        if game_time - self.last_drop_time < self.drop_cooldown:
            return

        if not hasattr(self.bot, "units"):
            return

        # 오버로드 수 확인 (수송 가능한 오버로드만)
        overlords = self.bot.units(UnitTypeId.OVERLORDTRANSPORT)
        if not overlords.exists:
            # 일반 오버로드도 확인 (Ventral Sacs 완료 시)
            overlords = self.bot.units(UnitTypeId.OVERLORD)

        if overlords.amount < self.min_overlords:
            return

        # 투하 가능 유닛 서플라이 확인
        available_supply = self._calculate_available_supply()
        if available_supply < self.min_supply_for_drop:
            return

        # 드롭 타겟 선정
        target = self._find_drop_target()
        if not target:
            return

        self.drop_target = target
        self.phase = DoomDropPhase.LOADING
        self.drop_active = True

        # 오버로드 선택
        idle_overlords = overlords.idle if hasattr(overlords, "idle") else overlords
        selected = list(idle_overlords)[:min(idle_overlords.amount, 6)]
        self.transport_overlords = {ol.tag: [] for ol in selected}

        # 회피 경로 계산
        self.waypoints = self._calculate_safe_route(target)
        self.current_waypoint_idx = 0

        self.logger.info(
            f"[{int(game_time)}s] [DOOM_DROP] 둠 드롭 개시! "
            f"오버로드 {len(self.transport_overlords)}기, 목표: {target}"
        )

    def _calculate_available_supply(self) -> int:
        """투하 가능 유닛 서플라이 계산"""
        total = 0
        for unit_type in self.load_priority:
            try:
                units = self.bot.units(unit_type).idle
                for unit in units:
                    # 저글링은 0.5 서플라이
                    if unit.type_id == UnitTypeId.ZERGLING:
                        total += 1  # 0.5 * 2 (pair)
                    else:
                        supply = getattr(unit, "supply_cost", 2)
                        total += supply if supply > 0 else 2
            except Exception:
                continue
        return total

    def _find_drop_target(self) -> Optional[Point2]:
        """
        드롭 타겟 선정

        우선순위:
        1. 적 확장 기지 (방어 약한 곳)
        2. 적 본진 미네랄 라인
        3. 적 테크 건물

        Returns:
            드롭 목표 위치 또는 None
        """
        if not Point2:
            return None

        candidates: List[Tuple[Point2, float]] = []

        # 적 기지 정보
        enemy_structures = getattr(self.bot, "enemy_structures", None)
        enemy_units = getattr(self.bot, "enemy_units", None)

        if enemy_structures and enemy_structures.exists:
            enemy_bases = enemy_structures.filter(
                lambda s: s.type_id in {
                    UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE,
                    UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND,
                    UnitTypeId.PLANETARYFORTRESS, UnitTypeId.NEXUS,
                }
            )

            for base in enemy_bases:
                # 방어력 평가 (주변 방어 건물 + 유닛 수)
                defense_score = 0

                # 방어 건물 확인
                nearby_defense = enemy_structures.closer_than(15, base).filter(
                    lambda s: s.type_id in {
                        UnitTypeId.MISSILETURRET, UnitTypeId.PHOTONCANNON,
                        UnitTypeId.SPORECRAWLER, UnitTypeId.SPINECRAWLER,
                        UnitTypeId.BUNKER,
                    }
                )
                defense_score += nearby_defense.amount * 3

                # 주변 유닛 확인
                if enemy_units and enemy_units.exists:
                    nearby_army = enemy_units.closer_than(15, base).filter(
                        lambda u: u.can_attack
                    )
                    defense_score += nearby_army.amount

                # 점수가 낮을수록 방어가 약한 곳
                candidates.append((base.position, defense_score))

        if candidates:
            # 방어가 가장 약한 곳 선택
            candidates.sort(key=lambda c: c[1])
            return candidates[0][0]

        # 폴백: 적 시작 위치
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            return self.bot.enemy_start_locations[0]

        return None

    def _calculate_safe_route(self, target: Point2) -> List[Point2]:
        """
        대공 위협 회피 경로 계산

        Args:
            target: 최종 목표 위치

        Returns:
            경유 지점 리스트
        """
        waypoints = []

        if not hasattr(self.bot, "start_location"):
            return [target]

        start = self.bot.start_location

        # 맵 가장자리를 경유하는 경로 (대공 회피)
        if hasattr(self.bot, "game_info"):
            map_size = self.bot.game_info.map_size

            # 맵 가장자리 경유 지점 계산
            # 시작에서 맵 가장자리로, 가장자리를 따라, 목표로
            edge_x = map_size.x - 5 if target.x > start.x else 5
            edge_y = map_size.y - 5 if target.y > start.y else 5

            waypoint1 = Point2((edge_x, start.y))
            waypoint2 = Point2((edge_x, edge_y))
            waypoint3 = Point2((target.x, edge_y))

            waypoints = [waypoint1, waypoint2, waypoint3, target]
        else:
            waypoints = [target]

        return waypoints

    async def _load_units(self, game_time: float):
        """유닛 탑승"""
        if not self.transport_overlords:
            self.phase = DoomDropPhase.IDLE
            self.drop_active = False
            return

        all_loaded = True
        overlord_list = list(self.transport_overlords.keys())

        for ol_tag in overlord_list:
            overlord = self._find_unit(ol_tag)
            if not overlord:
                del self.transport_overlords[ol_tag]
                continue

            # 이미 탑승 완료된 오버로드 스킵
            passengers = getattr(overlord, "passengers", [])
            cargo_used = sum(getattr(p, "cargo_size", 1) for p in passengers)
            cargo_max = getattr(overlord, "cargo_max", 8)

            if cargo_used >= cargo_max:
                continue

            all_loaded = False

            # 근처 유닛 탑승
            for unit_type in self.load_priority:
                try:
                    units = self.bot.units(unit_type)
                    nearby_units = units.closer_than(8, overlord)
                    for unit in nearby_units:
                        if cargo_used >= cargo_max:
                            break
                        self.bot.do(unit(AbilityId.SMART, overlord))
                        if ol_tag not in self.transport_overlords:
                            self.transport_overlords[ol_tag] = []
                        self.transport_overlords[ol_tag].append(unit.tag)
                        unit_cargo = getattr(unit, "cargo_size", 1)
                        cargo_used += unit_cargo
                except Exception:
                    continue

            # 유닛이 멀리 있으면 오버로드로 이동
            for unit_type in self.load_priority:
                try:
                    idle_units = self.bot.units(unit_type).idle
                    for unit in idle_units[:4]:
                        if unit.distance_to(overlord) > 8:
                            self.bot.do(unit.move(overlord.position))
                except Exception:
                    continue

        # 탑승 완료 또는 20초 경과 시 이동 개시
        if all_loaded or (game_time - self.last_drop_time > 20 and any(
            len(v) > 0 for v in self.transport_overlords.values()
        )):
            total_loaded = sum(len(v) for v in self.transport_overlords.values())
            self.phase = DoomDropPhase.EN_ROUTE
            self.logger.info(
                f"[{int(game_time)}s] [DOOM_DROP] 탑승 완료! "
                f"총 {total_loaded}기 탑승, 이동 개시"
            )

    async def _move_to_target(self, game_time: float):
        """목표를 향해 이동 (경유 지점 경유)"""
        if not self.waypoints:
            self.phase = DoomDropPhase.DROPPING
            return

        current_wp = self.waypoints[self.current_waypoint_idx]

        all_arrived = True
        for ol_tag in self.transport_overlords:
            overlord = self._find_unit(ol_tag)
            if not overlord:
                continue

            if overlord.distance_to(current_wp) > 8:
                self.bot.do(overlord.move(current_wp))
                all_arrived = False
            else:
                # 다음 경유 지점으로
                if self.current_waypoint_idx < len(self.waypoints) - 1:
                    all_arrived = False

        if all_arrived:
            self.current_waypoint_idx += 1
            if self.current_waypoint_idx >= len(self.waypoints):
                self.phase = DoomDropPhase.DROPPING

    async def _execute_drop(self, game_time: float):
        """유닛 투하 실행"""
        if not self.drop_target:
            self.phase = DoomDropPhase.IDLE
            self.drop_active = False
            return

        for ol_tag in list(self.transport_overlords.keys()):
            overlord = self._find_unit(ol_tag)
            if not overlord:
                continue

            if overlord.distance_to(self.drop_target) < self.drop_distance:
                # 투하!
                try:
                    self.bot.do(overlord(AbilityId.UNLOADALLAT, self.drop_target))
                    units_count = len(self.transport_overlords.get(ol_tag, []))
                    self.units_dropped += units_count
                except Exception as e:
                    self.logger.warning(f"[DOOM_DROP] 투하 실패: {e}")
            else:
                # 목표로 이동
                self.bot.do(overlord.move(self.drop_target))

        self.drops_executed += 1
        self.last_drop_time = game_time
        self.phase = DoomDropPhase.ATTACKING

        self.logger.info(
            f"[{int(game_time)}s] [DOOM_DROP] 둠 드롭 투하! "
            f"총 {self.units_dropped}기 투하 (#{self.drops_executed})"
        )

    async def _manage_dropped_units(self, game_time: float):
        """투하된 유닛 공격 관리"""
        # 오버로드 후퇴
        self.phase = DoomDropPhase.RETREATING

    async def _retreat_overlords(self, game_time: float):
        """오버로드 안전지대로 후퇴"""
        retreat_pos = getattr(self.bot, "start_location", None)
        if not retreat_pos:
            self._end_doom_drop()
            return

        all_safe = True
        for ol_tag in list(self.transport_overlords.keys()):
            overlord = self._find_unit(ol_tag)
            if overlord:
                if overlord.distance_to(retreat_pos) > 20:
                    self.bot.do(overlord.move(retreat_pos))
                    all_safe = False

        if all_safe:
            self._end_doom_drop()

    async def _check_overlord_safety(self):
        """오버로드 안전 체크 (대공 위협)"""
        enemy_units = getattr(self.bot, "enemy_units", None)
        if not enemy_units:
            return

        for ol_tag in list(self.transport_overlords.keys()):
            overlord = self._find_unit(ol_tag)
            if not overlord:
                continue

            # 대공 유닛 감지
            aa_threats = enemy_units.filter(
                lambda u: u.can_attack_air and u.distance_to(overlord) < self.safe_distance_from_aa
            )

            if aa_threats.exists and aa_threats.amount > 3:
                # 체력이 낮으면 즉시 투하 후 후퇴
                if overlord.health_percentage < self.overlord_retreat_hp:
                    try:
                        self.bot.do(overlord(AbilityId.UNLOADALLAT, overlord.position))
                        self.logger.warning(
                            f"[{int(self.bot.time)}s] [DOOM_DROP] "
                            f"오버로드 위험! 긴급 투하"
                        )
                    except Exception:
                        pass

    def _find_unit(self, tag: int) -> Optional[Unit]:
        """태그로 유닛 찾기"""
        if not hasattr(self.bot, "units"):
            return None
        unit = self.bot.units.find_by_tag(tag)
        if unit:
            return unit
        # 구조물에서도 찾기
        if hasattr(self.bot, "structures"):
            return self.bot.structures.find_by_tag(tag)
        return None

    def _end_doom_drop(self):
        """둠 드롭 종료"""
        game_time = getattr(self.bot, "time", 0.0)
        self.logger.info(
            f"[{int(game_time)}s] [DOOM_DROP] 둠 드롭 작전 완료 "
            f"(총 {self.drops_executed}회, {self.units_dropped}기 투하)"
        )
        self.phase = DoomDropPhase.IDLE
        self.drop_active = False
        self.transport_overlords.clear()
        self.drop_target = None
        self.waypoints.clear()
        self.current_waypoint_idx = 0

    def get_doom_drop_stats(self) -> Dict:
        """
        둠 드롭 통계 반환

        Returns:
            통계 딕셔너리
        """
        return {
            "phase": self.phase.value,
            "drop_active": self.drop_active,
            "overlords_assigned": len(self.transport_overlords),
            "drops_executed": self.drops_executed,
            "units_dropped": self.units_dropped,
            "ventral_sacs": self.ventral_sacs_complete,
        }
