# -*- coding: utf-8 -*-
"""
Upgrade Resource Planner - 업그레이드 자원 계획 및 예약 시스템

미네랄/가스를 전략적으로 축적하여 중요한 업그레이드에 사용
앞으로 필요한 업그레이드를 예측하고 자원을 미리 예약
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
except ImportError:
    UnitTypeId = None
    UpgradeId = None

from utils.logger import get_logger


class UpgradePriority(Enum):
    """업그레이드 우선순위"""
    CRITICAL = 0    # 생명줄 (저글링 발업, 대군주 속업)
    HIGH = 1        # 고우선순위 (공1, 방1)
    MEDIUM = 2      # 중우선순위 (공2, 방2)
    LOW = 3         # 저우선순위 (공3, 방3, 특수 업그레이드)


@dataclass
class UpgradePlan:
    """업그레이드 계획"""
    upgrade_id: object
    name: str
    mineral_cost: int
    gas_cost: int
    priority: UpgradePriority
    tech_requirement: str  # "Spawning Pool", "Lair", "Hive", etc.
    estimated_timing: float  # 예상 연구 타이밍 (초)
    prerequisite: Optional[str] = None  # 선행 업그레이드 이름


class UpgradeResourcePlanner:
    """
    업그레이드 자원 계획 시스템

    기능:
    1. 앞으로 필요한 업그레이드를 예측하고 타임라인 생성
    2. 업그레이드를 위한 자원 예약 (미네랄/가스 뱅킹)
    3. 자원 축적 우선순위 관리
    4. 업그레이드 완료 시간 예측

    학습 목표:
    - 자원을 낭비하지 않고 효율적으로 축적
    - 중요한 업그레이드를 적시에 완료
    - 유닛 생산과 업그레이드 밸런스 조정
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("UpgradeResourcePlanner")

        # 업그레이드 타임라인
        self.upgrade_timeline: List[UpgradePlan] = []

        # 자원 예약
        self.reserved_minerals = 0
        self.reserved_gas = 0
        self.reservation_until = 0.0  # 예약 만료 시간

        # 업그레이드 비용 데이터베이스
        self.upgrade_costs = self._initialize_upgrade_costs()

        # 학습 데이터
        self.resource_banking_history = []  # [(time, minerals, gas, reserved_minerals, reserved_gas)]
        self.upgrade_completion_times = {}  # upgrade_name -> completion_time

        # 설정
        self.planning_horizon = 180  # 3분 앞을 내다봄
        self.min_bank_buffer = 200  # 최소 자원 버퍼 (유닛 생산용)
        self.max_bank_threshold = 2000  # 최대 뱅킹 임계값

    def _initialize_upgrade_costs(self) -> Dict[str, Tuple[int, int]]:
        """업그레이드 비용 데이터베이스 초기화"""
        return {
            # 0순위 - CRITICAL
            "ZERGLINGMOVEMENTSPEED": (100, 100),  # 저글링 발업
            "OVERLORDSPEED": (100, 100),  # 대군주 속업
            "OVERLORDTRANSPORT": (25, 25),  # 배주머니

            # 1순위 - HIGH (공방 1단계)
            "ZERGMELEEWEAPONSLEVEL1": (100, 100),  # 근접 공1
            "ZERGMISSILEWEAPONSLEVEL1": (100, 100),  # 원거리 공1
            "ZERGGROUNDARMORSLEVEL1": (100, 100),  # 방어 1
            "ZERGFLYERWEAPONSLEVEL1": (100, 100),  # 공중 공1

            # 2순위 - MEDIUM (공방 2단계)
            "ZERGMELEEWEAPONSLEVEL2": (150, 150),  # 근접 공2
            "ZERGMISSILEWEAPONSLEVEL2": (150, 150),  # 원거리 공2
            "ZERGGROUNDARMORSLEVEL2": (150, 150),  # 방어 2
            "ZERGFLYERWEAPONSLEVEL2": (175, 175),  # 공중 공2

            # 3순위 - LOW (공방 3단계)
            "ZERGMELEEWEAPONSLEVEL3": (200, 200),  # 근접 공3
            "ZERGMISSILEWEAPONSLEVEL3": (200, 200),  # 원거리 공3
            "ZERGGROUNDARMORSLEVEL3": (200, 200),  # 방어 3
            "ZERGFLYERWEAPONSLEVEL3": (250, 250),  # 공중 공3

            # 유닛별 업그레이드
            "CENTRIFICALHOOKS": (150, 150),  # 맹독충 발업
            "GLIALRECONSTITUTION": (100, 100),  # 바퀴 발업
            "EVOLVEMUSCULARAUGMENTS": (100, 100),  # 히드라 속업
            "EVOLVEGROOVEDSPINES": (100, 150),  # 히드라 사거리
            "ZERGLINGATTACKSPEED": (200, 200),  # 아드레날린 (Crackling)
            "BURROW": (100, 100),  # 잠복
        }

    async def on_step(self, iteration: int) -> None:
        """매 프레임 호출"""
        game_time = getattr(self.bot, "time", 0)

        # 타임라인 업데이트 (3초마다)
        if iteration % 66 == 0:
            self._update_upgrade_timeline(game_time)

        # 자원 예약 관리 (1초마다)
        if iteration % 22 == 0:
            self._manage_resource_reservations(game_time)

        # 학습 데이터 수집 (5초마다)
        if iteration % 110 == 0:
            self._collect_learning_data(game_time)

    def _update_upgrade_timeline(self, game_time: float) -> None:
        """업그레이드 타임라인 업데이트"""
        self.upgrade_timeline.clear()

        # 현재 유닛 구성 분석
        composition = self._analyze_unit_composition()

        # 현재 테크 레벨 확인
        has_lair = self._has_tech("Lair")
        has_hive = self._has_tech("Hive")
        has_spawning_pool = self._has_tech("Spawning Pool")
        has_evo_chamber = self._has_tech("Evolution Chamber")

        # === 0순위: 생명줄 업그레이드 ===
        if has_spawning_pool and not self._is_upgrade_done("ZERGLINGMOVEMENTSPEED"):
            self.upgrade_timeline.append(UpgradePlan(
                upgrade_id=getattr(UpgradeId, "ZERGLINGMOVEMENTSPEED", None),
                name="ZERGLINGMOVEMENTSPEED",
                mineral_cost=100,
                gas_cost=100,
                priority=UpgradePriority.CRITICAL,
                tech_requirement="Spawning Pool",
                estimated_timing=game_time + 10
            ))

        if game_time >= 180 and not self._is_upgrade_done("OVERLORDSPEED"):
            self.upgrade_timeline.append(UpgradePlan(
                upgrade_id=getattr(UpgradeId, "OVERLORDSPEED", None),
                name="OVERLORDSPEED",
                mineral_cost=100,
                gas_cost=100,
                priority=UpgradePriority.CRITICAL,
                tech_requirement="Hatchery",
                estimated_timing=game_time + 20
            ))

        # === 1순위: 공방 1단계 ===
        if has_evo_chamber:
            if composition["melee"] > composition["ranged"]:
                # 저글링/맹독충 중심
                if not self._is_upgrade_done("ZERGMELEEWEAPONSLEVEL1"):
                    self.upgrade_timeline.append(UpgradePlan(
                        upgrade_id=getattr(UpgradeId, "ZERGMELEEWEAPONSLEVEL1", None),
                        name="ZERGMELEEWEAPONSLEVEL1",
                        mineral_cost=100,
                        gas_cost=100,
                        priority=UpgradePriority.HIGH,
                        tech_requirement="Evolution Chamber",
                        estimated_timing=game_time + 30
                    ))
            else:
                # 바퀴/히드라 중심
                if not self._is_upgrade_done("ZERGMISSILEWEAPONSLEVEL1"):
                    self.upgrade_timeline.append(UpgradePlan(
                        upgrade_id=getattr(UpgradeId, "ZERGMISSILEWEAPONSLEVEL1", None),
                        name="ZERGMISSILEWEAPONSLEVEL1",
                        mineral_cost=100,
                        gas_cost=100,
                        priority=UpgradePriority.HIGH,
                        tech_requirement="Evolution Chamber",
                        estimated_timing=game_time + 30
                    ))

            # 방어 업그레이드
            if not self._is_upgrade_done("ZERGGROUNDARMORSLEVEL1"):
                self.upgrade_timeline.append(UpgradePlan(
                    upgrade_id=getattr(UpgradeId, "ZERGGROUNDARMORSLEVEL1", None),
                    name="ZERGGROUNDARMORSLEVEL1",
                    mineral_cost=100,
                    gas_cost=100,
                    priority=UpgradePriority.HIGH,
                    tech_requirement="Evolution Chamber",
                    estimated_timing=game_time + 60
                ))

        # === 2순위: 공방 2단계 (Lair 필요) ===
        if has_lair and has_evo_chamber:
            if composition["melee"] > composition["ranged"]:
                if self._is_upgrade_done("ZERGMELEEWEAPONSLEVEL1") and not self._is_upgrade_done("ZERGMELEEWEAPONSLEVEL2"):
                    self.upgrade_timeline.append(UpgradePlan(
                        upgrade_id=getattr(UpgradeId, "ZERGMELEEWEAPONSLEVEL2", None),
                        name="ZERGMELEEWEAPONSLEVEL2",
                        mineral_cost=150,
                        gas_cost=150,
                        priority=UpgradePriority.MEDIUM,
                        tech_requirement="Lair",
                        estimated_timing=game_time + 90,
                        prerequisite="ZERGMELEEWEAPONSLEVEL1"
                    ))
            else:
                if self._is_upgrade_done("ZERGMISSILEWEAPONSLEVEL1") and not self._is_upgrade_done("ZERGMISSILEWEAPONSLEVEL2"):
                    self.upgrade_timeline.append(UpgradePlan(
                        upgrade_id=getattr(UpgradeId, "ZERGMISSILEWEAPONSLEVEL2", None),
                        name="ZERGMISSILEWEAPONSLEVEL2",
                        mineral_cost=150,
                        gas_cost=150,
                        priority=UpgradePriority.MEDIUM,
                        tech_requirement="Lair",
                        estimated_timing=game_time + 90,
                        prerequisite="ZERGMISSILEWEAPONSLEVEL1"
                    ))

        # === 3순위: 공방 3단계 (Hive 필요) ===
        if has_hive and has_evo_chamber:
            if composition["melee"] > composition["ranged"]:
                if self._is_upgrade_done("ZERGMELEEWEAPONSLEVEL2") and not self._is_upgrade_done("ZERGMELEEWEAPONSLEVEL3"):
                    self.upgrade_timeline.append(UpgradePlan(
                        upgrade_id=getattr(UpgradeId, "ZERGMELEEWEAPONSLEVEL3", None),
                        name="ZERGMELEEWEAPONSLEVEL3",
                        mineral_cost=200,
                        gas_cost=200,
                        priority=UpgradePriority.LOW,
                        tech_requirement="Hive",
                        estimated_timing=game_time + 120,
                        prerequisite="ZERGMELEEWEAPONSLEVEL2"
                    ))

        # 우선순위 정렬
        self.upgrade_timeline.sort(key=lambda x: (x.priority.value, x.estimated_timing))

    def _manage_resource_reservations(self, game_time: float) -> None:
        """자원 예약 관리"""
        # 예약 만료 체크
        if game_time > self.reservation_until:
            self.reserved_minerals = 0
            self.reserved_gas = 0
            self.reservation_until = 0.0
            return

        # 타임라인에서 다음 업그레이드 찾기
        next_upgrade = self._get_next_upgrade()
        if not next_upgrade:
            return

        current_minerals = getattr(self.bot, "minerals", 0)
        current_gas = getattr(self.bot, "vespene", 0)

        # 업그레이드가 임박한 경우 (30초 이내)
        if next_upgrade.estimated_timing - game_time <= 30:
            # 자원 예약
            minerals_needed = max(0, next_upgrade.mineral_cost - current_minerals)
            gas_needed = max(0, next_upgrade.gas_cost - current_gas)

            # 예약 설정
            self.reserved_minerals = minerals_needed
            self.reserved_gas = gas_needed
            self.reservation_until = next_upgrade.estimated_timing

            if minerals_needed > 0 or gas_needed > 0:
                self.logger.info(
                    f"[PLANNER] Reserving {minerals_needed}m/{gas_needed}g for {next_upgrade.name} "
                    f"(ETA: {int(next_upgrade.estimated_timing - game_time)}s)"
                )

        # 자원 과다 축적 경고 (업그레이드를 못하고 있는 경우)
        if current_minerals > self.max_bank_threshold and not self.reserved_minerals:
            self.logger.warning(
                f"[PLANNER] ⚠️ Excessive mineral banking: {current_minerals} "
                "(Consider increasing unit production)"
            )

    def _get_next_upgrade(self) -> Optional[UpgradePlan]:
        """다음 업그레이드 가져오기"""
        for upgrade_plan in self.upgrade_timeline:
            # 이미 완료되었거나 진행 중인 업그레이드는 스킵
            if self._is_upgrade_done(upgrade_plan.name):
                continue
            if self._is_upgrade_pending(upgrade_plan.name):
                continue
            # 선행 업그레이드가 필요한 경우 체크
            if upgrade_plan.prerequisite and not self._is_upgrade_done(upgrade_plan.prerequisite):
                continue
            return upgrade_plan
        return None

    def get_available_resources(self) -> Tuple[int, int]:
        """
        예약 후 사용 가능한 자원 반환

        Returns:
            (available_minerals, available_gas)
        """
        current_minerals = getattr(self.bot, "minerals", 0)
        current_gas = getattr(self.bot, "vespene", 0)

        available_minerals = max(0, current_minerals - self.reserved_minerals)
        available_gas = max(0, current_gas - self.reserved_gas)

        return available_minerals, available_gas

    def should_delay_production(self, mineral_cost: int, gas_cost: int) -> bool:
        """
        유닛 생산을 지연해야 하는지 판단

        Args:
            mineral_cost: 유닛의 미네랄 비용
            gas_cost: 유닛의 가스 비용

        Returns:
            True if production should be delayed
        """
        next_upgrade = self._get_next_upgrade()
        if not next_upgrade:
            return False

        game_time = getattr(self.bot, "time", 0)
        time_until_upgrade = next_upgrade.estimated_timing - game_time

        # 업그레이드가 20초 이내이고 CRITICAL 우선순위인 경우
        if time_until_upgrade <= 20 and next_upgrade.priority == UpgradePriority.CRITICAL:
            current_minerals = getattr(self.bot, "minerals", 0)
            current_gas = getattr(self.bot, "vespene", 0)

            # 유닛 생산 시 업그레이드 자원이 부족해지는 경우
            if (current_minerals - mineral_cost < next_upgrade.mineral_cost or
                current_gas - gas_cost < next_upgrade.gas_cost):
                self.logger.info(
                    f"[PLANNER] Delaying unit production for critical upgrade: {next_upgrade.name}"
                )
                return True

        return False

    def _collect_learning_data(self, game_time: float) -> None:
        """학습 데이터 수집"""
        current_minerals = getattr(self.bot, "minerals", 0)
        current_gas = getattr(self.bot, "vespene", 0)

        self.resource_banking_history.append((
            game_time,
            current_minerals,
            current_gas,
            self.reserved_minerals,
            self.reserved_gas
        ))

        # 최근 300개 데이터만 유지 (메모리 관리)
        if len(self.resource_banking_history) > 300:
            self.resource_banking_history = self.resource_banking_history[-300:]

    def _analyze_unit_composition(self) -> Dict[str, int]:
        """현재 유닛 구성 분석"""
        composition = {
            "melee": 0,
            "ranged": 0,
            "air": 0
        }

        if not hasattr(self.bot, "units"):
            return composition

        for unit in self.bot.units:
            if unit.type_id in [UnitTypeId.ZERGLING, UnitTypeId.BANELING, UnitTypeId.ULTRALISK]:
                composition["melee"] += 1
            elif unit.type_id in [UnitTypeId.ROACH, UnitTypeId.HYDRALISK, UnitTypeId.RAVAGER, UnitTypeId.LURKER]:
                composition["ranged"] += 1
            elif unit.type_id in [UnitTypeId.MUTALISK, UnitTypeId.CORRUPTOR, UnitTypeId.BROODLORD]:
                composition["air"] += 1

        return composition

    def _has_tech(self, tech_name: str) -> bool:
        """테크 건물 보유 여부 확인"""
        if not hasattr(self.bot, "structures"):
            return False

        tech_map = {
            "Spawning Pool": UnitTypeId.SPAWNINGPOOL,
            "Evolution Chamber": UnitTypeId.EVOLUTIONCHAMBER,
            "Lair": UnitTypeId.LAIR,
            "Hive": UnitTypeId.HIVE,
        }

        tech_id = tech_map.get(tech_name)
        if not tech_id:
            return False

        structures = self.bot.structures(tech_id).ready
        if tech_name == "Lair":
            # Lair는 Hive도 포함
            structures = structures | self.bot.structures(UnitTypeId.HIVE).ready

        return structures.exists

    def _is_upgrade_done(self, upgrade_name: str) -> bool:
        """업그레이드 완료 여부 확인"""
        upgrade_id = getattr(UpgradeId, upgrade_name, None)
        if not upgrade_id:
            return False

        upgrades = getattr(self.bot, "state", None)
        if upgrades and hasattr(self.bot.state, "upgrades"):
            return upgrade_id in self.bot.state.upgrades
        return False

    def _is_upgrade_pending(self, upgrade_name: str) -> bool:
        """업그레이드 진행 중 여부 확인"""
        upgrade_id = getattr(UpgradeId, upgrade_name, None)
        if not upgrade_id:
            return False

        return self.bot.already_pending_upgrade(upgrade_id) > 0

    def get_upgrade_progress_report(self) -> str:
        """업그레이드 진행 상황 보고서"""
        report = "[UPGRADE PLANNER]\n"
        report += f"Reserved: {self.reserved_minerals}m / {self.reserved_gas}g\n"
        report += f"Timeline ({len(self.upgrade_timeline)} upgrades):\n"

        for i, upgrade_plan in enumerate(self.upgrade_timeline[:5]):  # 상위 5개만
            game_time = getattr(self.bot, "time", 0)
            eta = int(upgrade_plan.estimated_timing - game_time)
            report += f"  {i+1}. {upgrade_plan.name} - ETA: {eta}s ({upgrade_plan.mineral_cost}m/{upgrade_plan.gas_cost}g)\n"

        return report
