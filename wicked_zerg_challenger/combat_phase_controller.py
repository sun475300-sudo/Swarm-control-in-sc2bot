# -*- coding: utf-8 -*-
"""
Combat Phase Controller - 전투 단계별 컨트롤 시스템

전투를 단계별로 관리하여 병력 손실 최소화:
1. Pre-Combat Phase (전투 전): 집결, 포지셔닝, 진형 형성
2. Engagement Phase (교전 단계): 전투 시작, 초기 포커스 파이어
3. Active Combat Phase (전투 중): 마이크로 컨트롤, 키팅, 스플릿
4. Retreat Phase (후퇴 단계): 손실 최소화 후퇴
"""

from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass

try:
    from sc2.units import Units
    from sc2.unit import Unit
    from sc2.position import Point2
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    Units = object
    Unit = object
    Point2 = tuple
    UnitTypeId = None

from utils.logger import get_logger


class CombatPhase(Enum):
    """전투 단계"""
    IDLE = 0           # 대기 (전투 없음)
    GATHERING = 1      # 집결 중
    POSITIONING = 2    # 포지셔닝 (전투 전 진형)
    ENGAGEMENT = 3     # 교전 시작
    ACTIVE_COMBAT = 4  # 활발한 전투 중
    RETREAT = 5        # 후퇴 중
    REGROUPING = 6     # 재집결 중


@dataclass
class CombatGroup:
    """전투 그룹"""
    units: Set[int]  # 유닛 태그 집합
    phase: CombatPhase
    rally_point: Optional[Point2]
    target_position: Optional[Point2]
    formation_type: str  # "concave", "line", "ball"
    engagement_time: float  # 교전 시작 시간
    last_phase_change: float  # 마지막 단계 변경 시간

    # 전투 통계
    initial_unit_count: int
    initial_total_hp: float
    enemies_killed: int
    damage_taken: float


class CombatPhaseController:
    """
    전투 단계별 컨트롤 시스템

    목표:
    - 병력 손실 최소화
    - 전투 효율 극대화
    - 단계별 최적 행동 선택

    학습 목표:
    - 언제 공격하고 언제 후퇴할지 학습
    - 최적 진형 및 포지션 학습
    - 병력 수 대비 교전 성공률 학습
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("CombatPhaseController")

        # 전투 그룹 관리
        self.combat_groups: Dict[str, CombatGroup] = {}  # group_id -> CombatGroup

        # 전투 설정
        self.min_army_for_attack = 8  # 최소 공격 병력
        self.retreat_hp_threshold = 0.3  # 후퇴 HP 임계값
        self.regroup_distance = 15  # 재집결 거리

        # 학습 데이터
        self.combat_history = []  # [(phase, unit_count, enemy_count, outcome)]
        self.phase_transitions = []  # [(from_phase, to_phase, time, success)]

        # 전투 메트릭
        self.total_engagements = 0
        self.successful_engagements = 0
        self.total_units_lost = 0
        self.total_enemies_killed = 0

    async def on_step(self, iteration: int) -> None:
        """매 프레임 호출"""
        game_time = getattr(self.bot, "time", 0)

        # 전투 그룹 업데이트
        self._update_combat_groups(game_time)

        # 각 그룹별 단계 관리
        for group_id, group in list(self.combat_groups.items()):
            await self._manage_group_phase(group_id, group, game_time, iteration)

        # 학습 데이터 수집 (5초마다)
        if iteration % 110 == 0:
            self._collect_learning_data(game_time)

    def _update_combat_groups(self, game_time: float) -> None:
        """전투 그룹 상태 업데이트"""
        # 기존 그룹의 유닛들이 존재하는지 확인
        for group_id, group in list(self.combat_groups.items()):
            # 유닛이 모두 죽었거나 사라진 그룹 제거
            alive_units = [tag for tag in group.units if self._is_unit_alive(tag)]

            if not alive_units:
                self.logger.info(f"[PHASE] Group {group_id} disbanded (no units)")
                del self.combat_groups[group_id]
                continue

            # 그룹 유닛 목록 업데이트
            group.units = set(alive_units)

        # 미할당 전투 유닛들을 자동으로 그룹에 추가
        if not hasattr(self.bot, "units"):
            return

        combat_units = self._get_combat_units()
        unassigned_units = []

        for unit in combat_units:
            assigned = False
            for group in self.combat_groups.values():
                if unit.tag in group.units:
                    assigned = True
                    break
            if not assigned:
                unassigned_units.append(unit)

        # 미할당 유닛이 충분하면 새 그룹 생성
        if len(unassigned_units) >= 5:
            self._create_new_group(unassigned_units, game_time)

    async def _manage_group_phase(self, group_id: str, group: CombatGroup, game_time: float, iteration: int) -> None:
        """그룹의 전투 단계 관리"""
        # 그룹의 현재 상태 평가
        group_units = self._get_group_units(group)
        if not group_units:
            return

        nearby_enemies = self._get_nearby_enemies(group_units)
        group_center = self._get_group_center(group_units)
        group_health_ratio = self._get_group_health_ratio(group_units)

        # === 단계별 행동 ===
        if group.phase == CombatPhase.IDLE:
            await self._handle_idle_phase(group_id, group, group_units, nearby_enemies, game_time)

        elif group.phase == CombatPhase.GATHERING:
            await self._handle_gathering_phase(group_id, group, group_units, game_time)

        elif group.phase == CombatPhase.POSITIONING:
            await self._handle_positioning_phase(group_id, group, group_units, nearby_enemies, game_time)

        elif group.phase == CombatPhase.ENGAGEMENT:
            await self._handle_engagement_phase(group_id, group, group_units, nearby_enemies, game_time)

        elif group.phase == CombatPhase.ACTIVE_COMBAT:
            await self._handle_active_combat_phase(group_id, group, group_units, nearby_enemies, game_time, iteration)

        elif group.phase == CombatPhase.RETREAT:
            await self._handle_retreat_phase(group_id, group, group_units, nearby_enemies, game_time)

        elif group.phase == CombatPhase.REGROUPING:
            await self._handle_regrouping_phase(group_id, group, group_units, game_time)

        # === 단계 전환 조건 체크 ===
        self._check_phase_transitions(group_id, group, group_units, nearby_enemies, group_health_ratio, game_time)

    async def _handle_idle_phase(self, group_id: str, group: CombatGroup, group_units: Units,
                                  nearby_enemies: Units, game_time: float) -> None:
        """대기 단계 처리"""
        # 적이 발견되면 집결 단계로
        if nearby_enemies:
            self._transition_phase(group_id, group, CombatPhase.GATHERING, game_time)
            return

        # 병력이 충분하고 타겟이 있으면 집결 시작
        if len(group_units) >= self.min_army_for_attack:
            if group.target_position:
                self._transition_phase(group_id, group, CombatPhase.GATHERING, game_time)

    async def _handle_gathering_phase(self, group_id: str, group: CombatGroup,
                                      group_units: Units, game_time: float) -> None:
        """집결 단계 처리 - 병력을 한 곳에 모음"""
        if not group.rally_point:
            # 집결 지점 설정 (그룹 중심에서 적 방향)
            group_center = self._get_group_center(group_units)
            if group.target_position:
                direction = (group.target_position - group_center).normalized
                group.rally_point = group_center + direction * 5
            else:
                group.rally_point = group_center

        # 모든 유닛을 집결 지점으로 이동
        for unit in group_units:
            if unit.distance_to(group.rally_point) > 3:
                self.bot.do(unit.move(group.rally_point))

        # 병력이 충분히 모였으면 포지셔닝 단계로
        units_at_rally = sum(1 for u in group_units if u.distance_to(group.rally_point) < 4)
        if units_at_rally >= len(group_units) * 0.7:  # 70% 이상 도착
            self._transition_phase(group_id, group, CombatPhase.POSITIONING, game_time)

    async def _handle_positioning_phase(self, group_id: str, group: CombatGroup, group_units: Units,
                                        nearby_enemies: Units, game_time: float) -> None:
        """포지셔닝 단계 처리 - 전투 전 진형 형성"""
        if not group.target_position:
            return

        # 진형 형성
        formation_positions = self._calculate_formation_positions(
            group_units,
            group.target_position,
            group.formation_type
        )

        # 유닛들을 진형 위치로 이동
        for unit, target_pos in zip(group_units, formation_positions):
            if unit.distance_to(target_pos) > 2:
                self.bot.do(unit.move(target_pos))

        # 적이 가까우면 즉시 교전 단계로
        if nearby_enemies and nearby_enemies.closest_distance_to(self._get_group_center(group_units)) < 10:
            self._transition_phase(group_id, group, CombatPhase.ENGAGEMENT, game_time)

    async def _handle_engagement_phase(self, group_id: str, group: CombatGroup, group_units: Units,
                                       nearby_enemies: Units, game_time: float) -> None:
        """교전 단계 처리 - 전투 시작, 포커스 파이어"""
        if not nearby_enemies:
            self._transition_phase(group_id, group, CombatPhase.POSITIONING, game_time)
            return

        # 교전 시작 시간 기록
        if group.engagement_time == 0:
            group.engagement_time = game_time
            group.initial_unit_count = len(group_units)
            group.initial_total_hp = sum(u.health + u.shield for u in group_units)
            self.total_engagements += 1

        # 포커스 파이어 - 가장 약한 적을 집중 공격
        priority_target = self._get_priority_target(nearby_enemies, group_units)

        if priority_target:
            for unit in group_units:
                if unit.weapon_cooldown == 0:
                    self.bot.do(unit.attack(priority_target))

        # 교전 2초 후 활발한 전투 단계로
        if game_time - group.engagement_time > 2:
            self._transition_phase(group_id, group, CombatPhase.ACTIVE_COMBAT, game_time)

    async def _handle_active_combat_phase(self, group_id: str, group: CombatGroup, group_units: Units,
                                          nearby_enemies: Units, game_time: float, iteration: int) -> None:
        """활발한 전투 단계 처리 - 마이크로 컨트롤"""
        if not nearby_enemies:
            self._transition_phase(group_id, group, CombatPhase.REGROUPING, game_time)
            return

        # 마이크로 컨트롤 (키팅, 스플릿)
        for unit in group_units:
            await self._micro_control_unit(unit, nearby_enemies, iteration)

    async def _handle_retreat_phase(self, group_id: str, group: CombatGroup, group_units: Units,
                                    nearby_enemies: Units, game_time: float) -> None:
        """후퇴 단계 처리"""
        # 본진 방향으로 후퇴
        if hasattr(self.bot, "start_location"):
            retreat_target = self.bot.start_location
        else:
            return

        for unit in group_units:
            # 체력이 낮은 유닛 우선 후퇴
            if unit.health_percentage < 0.5:
                self.bot.do(unit.move(retreat_target))
            else:
                # 후위 유닛은 적을 견제하면서 후퇴
                if nearby_enemies:
                    closest_enemy = nearby_enemies.closest_to(unit)
                    if unit.weapon_cooldown == 0:
                        self.bot.do(unit.attack(closest_enemy))
                    else:
                        self.bot.do(unit.move(retreat_target))

        # 안전 거리 확보 시 재집결 단계로
        if not nearby_enemies or nearby_enemies.closest_distance_to(self._get_group_center(group_units)) > 15:
            self._transition_phase(group_id, group, CombatPhase.REGROUPING, game_time)

    async def _handle_regrouping_phase(self, group_id: str, group: CombatGroup,
                                       group_units: Units, game_time: float) -> None:
        """재집결 단계 처리"""
        # 본진 근처로 재집결
        if hasattr(self.bot, "start_location"):
            regroup_point = self.bot.start_location.towards(
                self._get_group_center(group_units),
                self.regroup_distance
            )
        else:
            regroup_point = self._get_group_center(group_units)

        for unit in group_units:
            if unit.distance_to(regroup_point) > 5:
                self.bot.do(unit.move(regroup_point))

        # 재집결 완료 시 대기 단계로
        units_regrouped = sum(1 for u in group_units if u.distance_to(regroup_point) < 6)
        if units_regrouped >= len(group_units) * 0.8:
            self._transition_phase(group_id, group, CombatPhase.IDLE, game_time)

    def _check_phase_transitions(self, group_id: str, group: CombatGroup, group_units: Units,
                                  nearby_enemies: Units, health_ratio: float, game_time: float) -> None:
        """단계 전환 조건 체크"""
        # 후퇴 조건: HP가 임계값 이하이고 적이 우세
        if (health_ratio < self.retreat_hp_threshold and
            nearby_enemies and
            len(nearby_enemies) > len(group_units) * 1.5 and
            group.phase not in [CombatPhase.RETREAT, CombatPhase.REGROUPING]):

            self.logger.info(
                f"[PHASE] Group {group_id} retreating (HP: {health_ratio:.1%}, "
                f"enemies: {len(nearby_enemies)} vs us: {len(group_units)})"
            )
            self._transition_phase(group_id, group, CombatPhase.RETREAT, game_time)

    def _transition_phase(self, group_id: str, group: CombatGroup, new_phase: CombatPhase, game_time: float) -> None:
        """단계 전환"""
        old_phase = group.phase
        group.phase = new_phase
        group.last_phase_change = game_time

        self.phase_transitions.append((old_phase, new_phase, game_time, True))

        self.logger.info(f"[PHASE] Group {group_id}: {old_phase.name} -> {new_phase.name}")

    async def _micro_control_unit(self, unit: Unit, enemies: Units, iteration: int) -> None:
        """개별 유닛 마이크로 컨트롤"""
        if not enemies:
            return

        closest_enemy = enemies.closest_to(unit)

        # 저글링 - 서라운드
        if unit.type_id == UnitTypeId.ZERGLING:
            if unit.weapon_cooldown == 0:
                self.bot.do(unit.attack(closest_enemy))
            elif unit.health_percentage < 0.3:
                # 체력 낮으면 후퇴
                retreat_pos = unit.position.towards(closest_enemy, -2)
                self.bot.do(unit.move(retreat_pos))

        # 바퀴 - 키팅
        elif unit.type_id == UnitTypeId.ROACH:
            attack_range = 4
            if unit.weapon_cooldown == 0:
                self.bot.do(unit.attack(closest_enemy))
            elif unit.distance_to(closest_enemy) < attack_range - 1:
                # 적과 거리 유지
                retreat_pos = unit.position.towards(closest_enemy, -2)
                self.bot.do(unit.move(retreat_pos))

        # 히드라 - 사거리 활용
        elif unit.type_id == UnitTypeId.HYDRALISK:
            attack_range = 5  # 기본 사거리
            if unit.weapon_cooldown == 0:
                self.bot.do(unit.attack(closest_enemy))
            elif unit.distance_to(closest_enemy) < 3:
                # 근접 시 후퇴
                retreat_pos = unit.position.towards(closest_enemy, -2)
                self.bot.do(unit.move(retreat_pos))

        # 기본 - 공격
        else:
            if unit.weapon_cooldown == 0:
                self.bot.do(unit.attack(closest_enemy))

    def _create_new_group(self, units: List[Unit], game_time: float) -> str:
        """새 전투 그룹 생성"""
        group_id = f"group_{len(self.combat_groups)}"

        group = CombatGroup(
            units=set(u.tag for u in units),
            phase=CombatPhase.IDLE,
            rally_point=None,
            target_position=None,
            formation_type="concave",
            engagement_time=0,
            last_phase_change=game_time,
            initial_unit_count=len(units),
            initial_total_hp=sum(u.health + u.shield for u in units),
            enemies_killed=0,
            damage_taken=0
        )

        self.combat_groups[group_id] = group
        self.logger.info(f"[PHASE] Created {group_id} with {len(units)} units")
        return group_id

    def _calculate_formation_positions(self, units: Units, target: Point2, formation_type: str) -> List[Point2]:
        """진형 계산"""
        if not units:
            return []

        center = self._get_group_center(units)
        direction = (target - center).normalized if target else Point2((1, 0))

        positions = []

        if formation_type == "concave":
            # 오목 진형 (적을 감싸는 형태)
            for i, unit in enumerate(units):
                angle = (i / len(units)) * 3.14 - 1.57  # -90도 ~ +90도
                offset = Point2((direction.x * 3, direction.y * 3))
                offset = offset.rotated(angle)
                positions.append(center + offset)

        elif formation_type == "line":
            # 일직선 진형
            perpendicular = Point2((-direction.y, direction.x))
            for i, unit in enumerate(units):
                offset = perpendicular * (i - len(units) / 2) * 2
                positions.append(center + offset)

        else:  # "ball"
            # 구형 진형 (기본)
            positions = [center for _ in units]

        return positions

    def _get_priority_target(self, enemies: Units, friendly_units: Units) -> Optional[Unit]:
        """우선 타겟 선정"""
        if not enemies:
            return None

        # 가장 약한 적 (HP 비율 기준)
        weakest = min(enemies, key=lambda e: e.health_percentage)

        # 일점사 가능한지 확인 (5기 이상이 사거리 안에)
        units_in_range = sum(1 for u in friendly_units if u.distance_to(weakest) < 6)

        if units_in_range >= 5:
            return weakest

        # 그렇지 않으면 가장 가까운 적
        center = self._get_group_center(friendly_units)
        return enemies.closest_to(center)

    def _get_combat_units(self) -> Units:
        """전투 유닛 가져오기"""
        if not hasattr(self.bot, "units"):
            return Units([], self.bot)

        combat_types = [
            UnitTypeId.ZERGLING, UnitTypeId.BANELING, UnitTypeId.ROACH,
            UnitTypeId.RAVAGER, UnitTypeId.HYDRALISK, UnitTypeId.LURKER,
            UnitTypeId.MUTALISK, UnitTypeId.CORRUPTOR, UnitTypeId.ULTRALISK
        ]

        return self.bot.units.filter(lambda u: u.type_id in combat_types)

    def _get_group_units(self, group: CombatGroup) -> Units:
        """그룹의 유닛들 가져오기"""
        if not hasattr(self.bot, "units"):
            return Units([], self.bot)

        return self.bot.units.filter(lambda u: u.tag in group.units)

    def _get_nearby_enemies(self, units: Units, radius: float = 15) -> Units:
        """주변 적 유닛 가져오기"""
        if not units or not hasattr(self.bot, "enemy_units"):
            return Units([], self.bot)

        center = self._get_group_center(units)
        return self.bot.enemy_units.closer_than(radius, center)

    def _get_group_center(self, units: Units) -> Point2:
        """그룹 중심점 계산"""
        if not units:
            return Point2((0, 0))
        return Point2((
            sum(u.position.x for u in units) / len(units),
            sum(u.position.y for u in units) / len(units)
        ))

    def _get_group_health_ratio(self, units: Units) -> float:
        """그룹 체력 비율"""
        if not units:
            return 0.0

        total_hp = sum(u.health + u.shield for u in units)
        max_hp = sum(u.health_max + u.shield_max for u in units)

        return total_hp / max_hp if max_hp > 0 else 0.0

    def _is_unit_alive(self, unit_tag: int) -> bool:
        """유닛이 살아있는지 확인"""
        if not hasattr(self.bot, "units"):
            return False
        return any(u.tag == unit_tag for u in self.bot.units)

    def _collect_learning_data(self, game_time: float) -> None:
        """학습 데이터 수집"""
        for group_id, group in self.combat_groups.items():
            group_units = self._get_group_units(group)
            nearby_enemies = self._get_nearby_enemies(group_units)

            self.combat_history.append((
                group.phase,
                len(group_units),
                len(nearby_enemies),
                self._get_group_health_ratio(group_units)
            ))

        # 최근 1000개 데이터만 유지
        if len(self.combat_history) > 1000:
            self.combat_history = self.combat_history[-1000:]

    def set_group_target(self, group_id: str, target: Point2) -> None:
        """그룹 목표 위치 설정"""
        if group_id in self.combat_groups:
            self.combat_groups[group_id].target_position = target

    def get_combat_report(self) -> str:
        """전투 보고서"""
        report = "[COMBAT PHASE CONTROLLER]\n"
        report += f"Active Groups: {len(self.combat_groups)}\n"
        report += f"Total Engagements: {self.total_engagements}\n"

        if self.total_engagements > 0:
            success_rate = self.successful_engagements / self.total_engagements * 100
            report += f"Success Rate: {success_rate:.1f}%\n"

        report += f"K/D Ratio: {self.total_enemies_killed}/{self.total_units_lost}\n"

        for group_id, group in self.combat_groups.items():
            report += f"  {group_id}: {group.phase.name} ({len(group.units)} units)\n"

        return report
