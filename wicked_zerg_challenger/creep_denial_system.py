# -*- coding: utf-8 -*-
"""
Creep Denial System - 적 점막 제거 시스템

적의 크립 종양(Creep Tumor)을 탐지하고 제거하여 적의 점막 확장을 차단합니다.
ZvZ 대전에서 특히 중요한 시스템입니다.

주요 기능:
1. 적 크립 종양 탐지 (감시군주, 대군주, 정찰 유닛 활용)
2. 감시군주 자동 생산 및 배치
3. 크립 종양 우선순위 타겟팅
4. 크립 종양 파괴 유닛 자동 파견
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict

try:
    from sc2.unit import Unit
    from sc2.units import Units
    from sc2.position import Point2
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
except ImportError:
    Unit = object
    Units = object
    Point2 = tuple
    UnitTypeId = None
    AbilityId = None

from utils.logger import get_logger
from game_config import GameConfig


@dataclass
class DetectedTumor:
    """탐지된 크립 종양"""
    position: Point2
    detection_time: float
    last_seen: float
    unit_tag: Optional[int] = None  # 종양 유닛 태그 (보이면)
    assigned_units: Set[int] = None  # 파괴 임무에 할당된 유닛 태그
    is_burrowed: bool = True

    def __post_init__(self):
        if self.assigned_units is None:
            self.assigned_units = set()


class CreepDenialSystem:
    """
    적 점막 제거 시스템

    목표:
    - 적의 점막 확장 차단
    - 중요 지점의 크립 종양 우선 제거
    - 감시군주 자동 생산 및 배치

    학습 목표:
    - 크립 종양 우선순위 학습
    - 감시군주 배치 최적화
    - 제거 효율성 극대화
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("CreepDenial")

        # 탐지된 크립 종양
        self.detected_tumors: Dict[int, DetectedTumor] = {}  # tumor_id -> DetectedTumor
        self._next_tumor_id = 0

        # 감시군주 관리
        self.overseer_patrol_positions: List[Point2] = []
        self.overseer_assignments: Dict[int, Point2] = {}  # overseer_tag -> patrol_position

        # 크립 종양 제거 통계
        self.tumors_destroyed = 0
        self.tumors_detected = 0
        self.detection_by_unit_type: Dict[str, int] = defaultdict(int)

        # ★ 설정 (GameConfig에서 로드) ★
        self.min_overseers = GameConfig.CREEP_DENIAL_MIN_OVERSEERS
        self.tumor_memory_duration = GameConfig.CREEP_DENIAL_TUMOR_MEMORY_DURATION
        self.detection_radius = GameConfig.CREEP_DENIAL_DETECTION_RADIUS

        # 크립 종양 우선순위 지점
        self.priority_areas: List[Point2] = []  # 확장 위치, 전략적 요충지

        # 마지막 작업 시간
        self.last_overseer_check = 0
        self.last_tumor_scan = 0
        self.last_attack_dispatch = 0

        # ★ UnitAuthorityManager 통합 ★
        self.unit_authority = None  # 초기화 시 설정됨
        self.managed_units: Set[int] = set()  # 현재 관리 중인 유닛 태그

    async def on_step(self, iteration: int) -> None:
        """매 프레임 호출"""
        game_time = getattr(self.bot, "time", 0)

        # ZvZ가 아니면 감시군주만 소량 생산 (다른 종족도 크립 종양 탐지 필요)
        is_zvz = self._is_zvz()

        # 1. 우선순위 지점 업데이트
        if iteration % GameConfig.CREEP_DENIAL_PRIORITY_UPDATE_INTERVAL == 0:
            self._update_priority_areas()

        # 2. 크립 종양 탐지
        if iteration % GameConfig.CREEP_DENIAL_TUMOR_SCAN_INTERVAL == 0:
            self._detect_enemy_tumors(game_time)

        # 3. 감시군주 생산 및 배치
        if iteration % GameConfig.CREEP_DENIAL_OVERSEER_MANAGE_INTERVAL == 0:
            await self._manage_overseers(game_time, is_zvz)

        # 4. 크립 종양 공격 유닛 파견
        if iteration % GameConfig.CREEP_DENIAL_ATTACK_DISPATCH_INTERVAL == 0:
            await self._dispatch_tumor_attackers(game_time)

        # 5. 오래된 종양 정보 정리
        if iteration % GameConfig.CREEP_DENIAL_CLEANUP_INTERVAL == 0:
            self._cleanup_old_tumor_data(game_time)

        # 6. ★ 관리 중인 유닛 정리 및 반환 ★
        if iteration % GameConfig.CREEP_DENIAL_ATTACK_DISPATCH_INTERVAL == 0:
            self._cleanup_managed_units()

        # 7. ★ 후퇴 로직 (위협 감지 및 안전한 철수) ★
        if iteration % GameConfig.CREEP_DENIAL_ATTACK_DISPATCH_INTERVAL == 0:
            await self._check_and_retreat_units(game_time)

    def _is_zvz(self) -> bool:
        """ZvZ 여부 확인"""
        enemy_race = getattr(self.bot, "enemy_race", None)
        if enemy_race:
            race_str = str(enemy_race).lower()
            return "zerg" in race_str
        return False

    def _update_priority_areas(self) -> None:
        """크립 종양 제거 우선순위 지점 업데이트"""
        self.priority_areas.clear()

        # 1. 모든 확장 위치
        if hasattr(self.bot, "expansion_locations_list"):
            for exp_loc in self.bot.expansion_locations_list:
                self.priority_areas.append(exp_loc)

        # 2. 아군 기지 주변 (반경 15 이내)
        if hasattr(self.bot, "townhalls"):
            for base in self.bot.townhalls:
                self.priority_areas.append(base.position)

        # 3. 맵 중앙 (Xel'Naga Tower 위치)
        if hasattr(self.bot, "game_info") and hasattr(self.bot.game_info, "map_center"):
            self.priority_areas.append(self.bot.game_info.map_center)

    def _detect_enemy_tumors(self, game_time: float) -> None:
        """적 크립 종양 탐지"""
        if not hasattr(self.bot, "enemy_structures"):
            return

        # 보이는 적 크립 종양
        visible_tumors = self.bot.enemy_structures.filter(
            lambda s: s.type_id in [UnitTypeId.CREEPTUMOR, UnitTypeId.CREEPTUMORBURROWED, UnitTypeId.CREEPTUMORQUEEN]
        )

        for tumor in visible_tumors:
            # 이미 추적 중인 종양인지 확인
            existing_tumor_id = self._find_tumor_by_position(tumor.position)

            if existing_tumor_id is not None:
                # 기존 종양 업데이트
                self.detected_tumors[existing_tumor_id].last_seen = game_time
                self.detected_tumors[existing_tumor_id].unit_tag = tumor.tag
                self.detected_tumors[existing_tumor_id].is_burrowed = tumor.type_id == UnitTypeId.CREEPTUMORBURROWED
            else:
                # 새 종양 추가
                tumor_id = self._next_tumor_id
                self._next_tumor_id += 1

                self.detected_tumors[tumor_id] = DetectedTumor(
                    position=tumor.position,
                    detection_time=game_time,
                    last_seen=game_time,
                    unit_tag=tumor.tag,
                    is_burrowed=tumor.type_id == UnitTypeId.CREEPTUMORBURROWED
                )

                self.tumors_detected += 1
                self.detection_by_unit_type["visible"] += 1
                self.logger.info(f"[CREEP_DENIAL] New enemy tumor detected at {tumor.position}")

        # 적 크립 위에서 종양 위치 추정 (보이지 않는 종양)
        self._estimate_hidden_tumors(game_time)

    def _estimate_hidden_tumors(self, game_time: float) -> None:
        """보이지 않는 크립 종양 위치 추정"""
        if not hasattr(self.bot, "state") or not hasattr(self.bot.state, "creep"):
            return

        # 적 크립 맵에서 확장되는 지점 탐지
        # (실제 구현은 복잡하므로 간단한 휴리스틱 사용)

        # 우선순위 지역에서 적 크립이 있는지 확인
        for priority_pos in self.priority_areas:
            if self.bot.state.creep.is_set(priority_pos.rounded):
                # 이 지점이 아군 크립이 아니면 적 크립
                if not self._is_friendly_creep_area(priority_pos):
                    # 종양이 근처에 있을 가능성이 높음
                    existing_tumor = self._find_tumor_by_position(priority_pos, radius=10)
                    if existing_tumor is None:
                        # 추정 종양 추가 (정확한 위치는 모르지만 대략적 위치)
                        tumor_id = self._next_tumor_id
                        self._next_tumor_id += 1

                        self.detected_tumors[tumor_id] = DetectedTumor(
                            position=priority_pos,
                            detection_time=game_time,
                            last_seen=game_time,
                            unit_tag=None,
                            is_burrowed=True
                        )

                        self.logger.debug(f"[CREEP_DENIAL] Estimated hidden tumor near {priority_pos}")

    def _is_friendly_creep_area(self, position: Point2) -> bool:
        """아군 크립 영역인지 확인"""
        if not hasattr(self.bot, "townhalls"):
            return False

        # 아군 기지 반경 이내면 아군 크립
        for base in self.bot.townhalls:
            if base.distance_to(position) < GameConfig.CREEP_DENIAL_ATTACK_UNIT_DISTANCE:
                return True

        return False

    async def _manage_overseers(self, game_time: float, is_zvz: bool) -> None:
        """감시군주 생산 및 배치 관리"""
        if not UnitTypeId:
            return

        # 현재 감시군주 수 확인
        overseers = self.bot.units(UnitTypeId.OVERSEER)
        overseer_count = overseers.amount

        # 목표 감시군주 수 결정
        target_overseers = self.min_overseers if is_zvz else 1

        # 감시군주 부족 시 생산
        if overseer_count < target_overseers:
            await self._morph_overseer()

        # 감시군주 배치
        for overseer in overseers:
            if overseer.tag not in self.overseer_assignments:
                # 새로운 감시군주에게 순찰 위치 할당
                patrol_pos = self._assign_overseer_patrol_position(overseer)
                self.overseer_assignments[overseer.tag] = patrol_pos

            # 순찰 위치로 이동
            patrol_pos = self.overseer_assignments[overseer.tag]
            if overseer.distance_to(patrol_pos) > GameConfig.CREEP_DENIAL_PATROL_DISTANCE:
                self.bot.do(overseer.move(patrol_pos))
            else:
                # 순찰 위치에 도착하면 다음 위치로
                new_patrol_pos = self._get_next_patrol_position(patrol_pos)
                self.overseer_assignments[overseer.tag] = new_patrol_pos
                self.bot.do(overseer.move(new_patrol_pos))

    async def _morph_overseer(self) -> None:
        """대군주를 감시군주로 변이"""
        if not UnitTypeId or not AbilityId:
            return

        # 사용 가능한 대군주 찾기
        overlords = self.bot.units(UnitTypeId.OVERLORD).idle
        if not overlords:
            return

        # 가스 확인 (감시군주 변이 비용)
        if (self.bot.vespene < GameConfig.CREEP_DENIAL_MIN_GAS or
            self.bot.minerals < GameConfig.CREEP_DENIAL_MIN_MINERALS):
            return

        # 레어 필요
        if not self._has_lair():
            return

        # 대군주 → 감시군주 변이
        overlord = overlords.first
        if overlord.is_idle:
            self.bot.do(overlord(AbilityId.MORPH_OVERSEER))
            self.logger.info("[CREEP_DENIAL] Morphing Overlord to Overseer")

    def _has_lair(self) -> bool:
        """레어/군락 보유 여부 확인"""
        if not hasattr(self.bot, "structures"):
            return False

        lairs = self.bot.structures(UnitTypeId.LAIR)
        hives = self.bot.structures(UnitTypeId.HIVE)
        return (lairs and lairs.ready) or (hives and hives.ready)

    def _assign_overseer_patrol_position(self, overseer: Unit) -> Point2:
        """감시군주에게 순찰 위치 할당"""
        # 우선순위 지점 중 가장 가까운 곳
        if self.priority_areas:
            return min(self.priority_areas, key=lambda p: overseer.distance_to(p))

        # 맵 중앙
        if hasattr(self.bot, "game_info"):
            return self.bot.game_info.map_center

        return overseer.position

    def _get_next_patrol_position(self, current_pos: Point2) -> Point2:
        """다음 순찰 위치 반환"""
        if not self.priority_areas:
            return current_pos

        # 현재 위치에서 가장 먼 우선순위 지점
        return max(self.priority_areas, key=lambda p: current_pos.distance_to(p))

    async def _dispatch_tumor_attackers(self, game_time: float) -> None:
        """크립 종양 공격 유닛 파견"""
        if not self.detected_tumors:
            return

        # 공격 가능한 유닛 (저글링, 바퀴, 히드라 등)
        attack_units = self._get_available_attack_units()
        if not attack_units:
            return

        # 우선순위 순으로 종양 처리
        sorted_tumors = self._get_prioritized_tumors()

        for tumor_id, tumor in sorted_tumors:
            # 이미 충분한 유닛이 할당되었으면 스킵
            if len(tumor.assigned_units) >= GameConfig.CREEP_DENIAL_MAX_UNITS_PER_TUMOR:
                continue

            # 가장 가까운 공격 유닛 찾기
            nearest_units = self._get_nearest_units(
                attack_units, tumor.position,
                count=GameConfig.CREEP_DENIAL_MAX_UNITS_PER_TUMOR
            )

            for unit in nearest_units:
                if unit.tag not in tumor.assigned_units:
                    tumor.assigned_units.add(unit.tag)

                    # 종양 위치로 공격 명령
                    if tumor.unit_tag:
                        # 종양이 보이면 직접 공격
                        target = self.bot.enemy_structures.find_by_tag(tumor.unit_tag)
                        if target:
                            self.bot.do(unit.attack(target))
                    else:
                        # 종양이 안 보이면 위치로 이동 (감시군주가 탐지할 때까지)
                        self.bot.do(unit.move(tumor.position))

                    self.logger.debug(
                        f"[CREEP_DENIAL] Dispatched {unit.type_id.name} to tumor at {tumor.position}"
                    )

            # 할당된 유닛을 사용 가능 목록에서 제거
            attack_units = [u for u in attack_units if u.tag not in tumor.assigned_units]
            if not attack_units:
                break

    def _get_available_attack_units(self) -> List[Unit]:
        """
        공격 가능한 유닛 가져오기 (UnitAuthorityManager 통합)

        UnitAuthorityManager를 통해 안전하게 유닛을 요청하여
        전투 중인 유닛이나 다른 시스템이 사용 중인 유닛을 뺏어오지 않습니다.
        """
        if not hasattr(self.bot, "units"):
            return []

        # UnitAuthorityManager가 없으면 fallback (하위 호환성)
        if not self.unit_authority:
            self.unit_authority = getattr(self.bot, "unit_authority", None)
            if not self.unit_authority:
                self.logger.warning("[CREEP_DENIAL] UnitAuthorityManager not available - using fallback mode")
                return self._get_available_attack_units_fallback()

        # 저글링, 바퀴, 히드라 등 지상 공격 유닛
        attack_types = [
            UnitTypeId.ZERGLING,
            UnitTypeId.ROACH,
            UnitTypeId.HYDRALISK,
            UnitTypeId.RAVAGER
        ]

        available_units = []

        from unit_authority_manager import AuthorityLevel

        for unit_type in attack_types:
            units = self.bot.units(unit_type)
            # 대기 중이거나 근처에 적이 없는 유닛만
            for unit in units:
                # 기본 가용성 체크
                if not self._is_unit_available_for_tumor_attack(unit):
                    continue

                # ★ UnitAuthorityManager를 통해 유닛 요청 ★
                if self.unit_authority.request_unit(
                    unit.tag,
                    "creep_denial",
                    AuthorityLevel.CREEP  # 낮은 우선순위 (20)
                ):
                    available_units.append(unit)
                    self.managed_units.add(unit.tag)

        return available_units

    def _get_available_attack_units_fallback(self) -> List[Unit]:
        """Fallback: UnitAuthorityManager 없이 유닛 가져오기 (legacy)"""
        attack_types = [
            UnitTypeId.ZERGLING,
            UnitTypeId.ROACH,
            UnitTypeId.HYDRALISK,
            UnitTypeId.RAVAGER
        ]

        available_units = []
        for unit_type in attack_types:
            units = self.bot.units(unit_type)
            for unit in units:
                if self._is_unit_available_for_tumor_attack(unit):
                    available_units.append(unit)

        return available_units

    def _is_unit_available_for_tumor_attack(self, unit: Unit) -> bool:
        """
        유닛이 종양 공격에 사용 가능한지 확인

        안전성 체크:
        1. 전투 중인 유닛은 사용하지 않음
        2. 근처에 적이 있으면 사용하지 않음
        3. 체력이 낮은 유닛은 사용하지 않음
        """
        # ★ 전투 중인 유닛 보호 ★
        # 근처에 적 유닛이 있으면 사용 불가
        if hasattr(self.bot, "enemy_units"):
            nearby_enemies = self.bot.enemy_units.closer_than(
                GameConfig.CREEP_DENIAL_ATTACK_UNIT_DISTANCE, unit
            )
            if nearby_enemies:
                return False

        # ★ 체력이 낮은 유닛 보호 ★
        # 체력이 최소 비율 미만이면 사용 불가
        if hasattr(unit, "health") and hasattr(unit, "health_max"):
            if unit.health < unit.health_max * GameConfig.CREEP_DENIAL_MIN_HEALTH_PERCENT:
                return False

        # ★ 대기 중이거나 이미 creep denial 임무 중인 유닛만 사용 ★
        if unit.is_idle:
            return True

        # 이미 관리 중인 유닛이면 사용 가능
        if unit.tag in self.managed_units:
            return True

        return False

    def _get_prioritized_tumors(self) -> List[Tuple[int, DetectedTumor]]:
        """우선순위 순으로 정렬된 종양 목록"""
        tumor_list = []

        for tumor_id, tumor in self.detected_tumors.items():
            priority_score = self._calculate_tumor_priority(tumor)
            tumor_list.append((priority_score, tumor_id, tumor))

        # 우선순위 높은 순으로 정렬
        tumor_list.sort(reverse=True, key=lambda x: x[0])

        return [(tid, t) for (_, tid, t) in tumor_list]

    def _calculate_tumor_priority(self, tumor: DetectedTumor) -> float:
        """종양 우선순위 계산"""
        priority = 0.0

        # 1. 우선순위 지역에 가까울수록 높은 우선순위
        if self.priority_areas:
            min_dist = min(tumor.position.distance_to(p) for p in self.priority_areas)
            priority += max(0, GameConfig.CREEP_DENIAL_PRIORITY_DISTANCE_BONUS - min_dist)

        # 2. 아군 기지에 가까울수록 높은 우선순위
        if hasattr(self.bot, "townhalls"):
            for base in self.bot.townhalls:
                dist = tumor.position.distance_to(base)
                if dist < GameConfig.CREEP_DENIAL_BASE_DISTANCE_THRESHOLD:
                    priority += (GameConfig.CREEP_DENIAL_BASE_DISTANCE_THRESHOLD - dist) * 2

        # 3. 보이는 종양이 더 높은 우선순위
        if tumor.unit_tag:
            priority += GameConfig.CREEP_DENIAL_VISIBLE_TUMOR_BONUS

        # 4. 최근에 본 종양이 더 높은 우선순위
        game_time = getattr(self.bot, "time", 0)
        time_since_seen = game_time - tumor.last_seen
        priority += max(0, GameConfig.CREEP_DENIAL_RECENT_SIGHTING_BONUS - time_since_seen)

        return priority

    def _get_nearest_units(self, units: List[Unit], position: Point2, count: int = 3) -> List[Unit]:
        """위치에서 가장 가까운 유닛들 반환"""
        sorted_units = sorted(units, key=lambda u: u.distance_to(position))
        return sorted_units[:count]

    def _find_tumor_by_position(self, position: Point2, radius: float = 2.0) -> Optional[int]:
        """위치로 종양 찾기"""
        for tumor_id, tumor in self.detected_tumors.items():
            if tumor.position.distance_to(position) < radius:
                return tumor_id
        return None

    def _cleanup_old_tumor_data(self, game_time: float) -> None:
        """오래된 종양 데이터 정리"""
        to_remove = []

        for tumor_id, tumor in self.detected_tumors.items():
            # 60초 동안 안 본 종양은 제거
            if game_time - tumor.last_seen > self.tumor_memory_duration:
                to_remove.append(tumor_id)

            # 종양이 파괴되었는지 확인
            if tumor.unit_tag:
                # 유닛 태그로 확인
                if not self._tumor_exists(tumor.unit_tag):
                    to_remove.append(tumor_id)
                    self.tumors_destroyed += 1
                    self.logger.info(f"[CREEP_DENIAL] ★ Tumor destroyed at {tumor.position}! ★")

                    # ★ 할당된 유닛들 반환 ★
                    self._release_tumor_units(tumor)

        for tumor_id in to_remove:
            tumor = self.detected_tumors[tumor_id]
            # 제거되는 종양의 유닛들도 반환
            self._release_tumor_units(tumor)
            del self.detected_tumors[tumor_id]

    def _release_tumor_units(self, tumor: DetectedTumor) -> None:
        """종양에 할당된 유닛들을 UnitAuthorityManager에 반환"""
        if not self.unit_authority:
            return

        for unit_tag in tumor.assigned_units:
            if self.unit_authority.release_unit(unit_tag, "creep_denial"):
                self.managed_units.discard(unit_tag)

        tumor.assigned_units.clear()

    def _cleanup_managed_units(self) -> None:
        """
        관리 중인 유닛 정리 및 반환

        다음 경우 유닛을 UnitAuthorityManager에 반환:
        1. 유닛이 죽었을 때
        2. 유닛이 종양 공격 임무를 완료했을 때
        3. 유닛이 더 이상 사용 가능하지 않을 때
        """
        if not self.unit_authority or not hasattr(self.bot, "units"):
            return

        units_to_release = []

        for unit_tag in self.managed_units:
            # 유닛이 존재하는지 확인
            unit = self.bot.units.find_by_tag(unit_tag)
            if not unit:
                # 유닛이 죽었으면 반환
                units_to_release.append(unit_tag)
                continue

            # 유닛이 idle이고 종양 할당도 없으면 반환
            if unit.is_idle:
                # 이 유닛이 어떤 종양에도 할당되어 있지 않으면 반환
                is_assigned = False
                for tumor in self.detected_tumors.values():
                    if unit_tag in tumor.assigned_units:
                        is_assigned = True
                        break

                if not is_assigned:
                    units_to_release.append(unit_tag)

        # 유닛 반환
        for unit_tag in units_to_release:
            if self.unit_authority.release_unit(unit_tag, "creep_denial"):
                self.managed_units.discard(unit_tag)
                self.logger.debug(f"[CREEP_DENIAL] Released unit {unit_tag} back to authority manager")

    async def _check_and_retreat_units(self, game_time: float) -> None:
        """
        ★ 위협 감지 및 후퇴 로직 ★

        관리 중인 유닛이 적 주력과 마주치면:
        1. 위협 감지 (IntelManager 활용)
        2. 후퇴 경로 계산 (가장 가까운 아군 기지로)
        3. 후퇴 명령 실행
        4. 유닛 권한 반환
        """
        if not self.managed_units or not hasattr(self.bot, "units"):
            return

        intel = getattr(self.bot, "intel", None)
        if not intel:
            return

        # ★ 1. 위협 감지 ★
        # IntelManager의 위협 정보 사용
        is_under_attack = getattr(intel, "is_under_attack", lambda: False)()
        threat_level = getattr(intel, "get_threat_level", lambda: "none")()
        has_high_threat = threat_level in ["heavy", "critical"]

        if not is_under_attack and not has_high_threat:
            # 위협이 없으면 추가 체크
            return

        # ★ 2. 관리 중인 유닛 중 위협에 노출된 유닛 찾기 ★
        units_to_retreat = []

        for unit_tag in self.managed_units:
            unit = self.bot.units.find_by_tag(unit_tag)
            if not unit:
                continue

            # 근처에 적이 있는지 확인
            if hasattr(self.bot, "enemy_units"):
                nearby_enemies = self.bot.enemy_units.closer_than(
                    GameConfig.CREEP_DENIAL_RETREAT_ENEMY_DISTANCE, unit
                )

                # 적이 있고, 적이 우리보다 강하면 후퇴
                if nearby_enemies:
                    # 적 전투력 추정
                    enemy_supply = sum(
                        getattr(enemy, "supply_cost", 1)
                        for enemy in nearby_enemies
                    )

                    # 우리 유닛이 1개뿐이고 적이 2보급 이상이면 후퇴
                    if enemy_supply >= 2:
                        units_to_retreat.append((unit_tag, unit))

        if not units_to_retreat:
            return

        # ★ 3. 후퇴 명령 실행 ★
        retreat_count = 0
        for unit_tag, unit in units_to_retreat:
            # 가장 가까운 아군 기지 찾기
            retreat_pos = self._get_retreat_position(unit)
            if retreat_pos:
                self.bot.do(unit.move(retreat_pos))
                retreat_count += 1

                # 종양 할당에서 제거
                for tumor in self.detected_tumors.values():
                    tumor.assigned_units.discard(unit_tag)

                # 유닛 권한 반환
                if self.unit_authority:
                    self.unit_authority.release_unit(unit_tag, "creep_denial")
                    self.managed_units.discard(unit_tag)

        if retreat_count > 0:
            self.logger.info(
                f"[CREEP_DENIAL] ★ {retreat_count} units retreating from threat! ★"
            )

    def _get_retreat_position(self, unit: Unit) -> Optional[Point2]:
        """
        후퇴 위치 계산

        Args:
            unit: 후퇴할 유닛

        Returns:
            가장 가까운 아군 기지 위치, 없으면 None
        """
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls:
            return None

        # 가장 가까운 아군 기지
        closest_base = min(
            self.bot.townhalls,
            key=lambda base: unit.distance_to(base)
        )

        return closest_base.position

    def _tumor_exists(self, tumor_tag: int) -> bool:
        """종양이 여전히 존재하는지 확인"""
        if not hasattr(self.bot, "enemy_structures"):
            return False

        for structure in self.bot.enemy_structures:
            if structure.tag == tumor_tag:
                return True

        return False

    def get_creep_denial_report(self) -> str:
        """크립 제거 보고서"""
        report = "[CREEP DENIAL SYSTEM]\n"

        overseer_count = self.bot.units(UnitTypeId.OVERSEER).amount if UnitTypeId else 0
        report += f"Overseers: {overseer_count}\n"
        report += f"Detected Tumors: {len(self.detected_tumors)}\n"
        report += f"Total Detected: {self.tumors_detected}\n"
        report += f"Total Destroyed: {self.tumors_destroyed}\n"

        if self.tumors_detected > 0:
            destruction_rate = self.tumors_destroyed / self.tumors_detected * 100
            report += f"Destruction Rate: {destruction_rate:.1f}%\n"

        # 활성 종양 목록
        if self.detected_tumors:
            report += "\nActive Tumors:\n"
            for tumor_id, tumor in list(self.detected_tumors.items())[:5]:  # 상위 5개만
                assigned = len(tumor.assigned_units)
                report += f"  Tumor {tumor_id}: {tumor.position} (Assigned: {assigned})\n"

        return report
