# -*- coding: utf-8 -*-
"""
Adaptive Build Order Manager - 적응형 빌드오더 시스템 (#104)

적 종족/전략에 따라 빌드오더를 자동으로 선택하고,
게임 내 정찰 정보를 기반으로 빌드를 실시간 수정합니다.

주요 기능:
1. 종족별 기본 빌드오더 라이브러리
2. 적 전략 감지에 따른 빌드오더 전환
3. 정찰 정보 기반 동적 빌드 수정
4. 빌드오더 우선순위 큐
5. 타이밍 기반 자동 전환
"""

from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
except ImportError:
    UnitTypeId = None
    UpgradeId = None


class BuildOrderType(Enum):
    """빌드오더 종류"""
    HATCH_FIRST = "hatch_first"           # 해처리 퍼스트 (경제)
    POOL_FIRST = "pool_first"             # 풀 퍼스트 (안전)
    TWELVE_POOL = "twelve_pool"           # 12풀 (공격적)
    ROACH_RUSH = "roach_rush"             # 바퀴 러시
    LING_BANE = "ling_bane"               # 저글링+맹독충
    HYDRA_TIMING = "hydra_timing"         # 히드라 타이밍
    MUTA_LING = "muta_ling"               # 뮤탈+저글링
    ROACH_HYDRA = "roach_hydra"           # 바퀴+히드라
    MACRO_HATCH = "macro_hatch"           # 매크로 해처리
    DEFENSIVE = "defensive"               # 수비적 빌드


class BuildStep:
    """빌드오더 단일 스텝"""

    def __init__(self, supply: int, action: str, unit_or_building: str,
                 priority: int = 5, condition: Optional[str] = None):
        """
        Args:
            supply: 실행 서플라이
            action: 행동 타입 ("build", "train", "upgrade", "morph")
            unit_or_building: 대상 유닛/건물 이름
            priority: 우선순위 (1=최고, 10=최저)
            condition: 조건부 실행 조건 (예: "enemy_air_detected")
        """
        self.supply = supply
        self.action = action
        self.unit_or_building = unit_or_building
        self.priority = priority
        self.condition = condition
        self.completed = False
        self.skipped = False

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "supply": self.supply,
            "action": self.action,
            "target": self.unit_or_building,
            "priority": self.priority,
            "condition": self.condition,
            "completed": self.completed,
        }


class AdaptiveBuildOrderManager:
    """
    적응형 빌드오더 관리자

    적 종족과 전략에 따라 빌드오더를 자동으로 선택하고,
    게임 진행 중 정찰 정보에 따라 빌드를 동적으로 수정합니다.

    사용 예:
        manager = AdaptiveBuildOrderManager(bot)
        manager.select_initial_build("Protoss")
        # 매 스텝:
        next_action = manager.get_next_build_step()
        manager.update(scout_info)
    """

    # 종족별 기본 빌드오더 라이브러리
    BUILD_LIBRARY = {
        "Terran": {
            "default": BuildOrderType.ROACH_HYDRA,
            "rush_detected": BuildOrderType.POOL_FIRST,
            "mech_detected": BuildOrderType.ROACH_HYDRA,
            "bio_detected": BuildOrderType.LING_BANE,
            "air_detected": BuildOrderType.HYDRA_TIMING,
        },
        "Protoss": {
            "default": BuildOrderType.ROACH_HYDRA,
            "rush_detected": BuildOrderType.POOL_FIRST,
            "stargate_detected": BuildOrderType.HYDRA_TIMING,
            "robo_detected": BuildOrderType.LING_BANE,
            "twilight_detected": BuildOrderType.ROACH_RUSH,
            "air_detected": BuildOrderType.HYDRA_TIMING,
        },
        "Zerg": {
            "default": BuildOrderType.HATCH_FIRST,
            "rush_detected": BuildOrderType.POOL_FIRST,
            "ling_flood": BuildOrderType.ROACH_RUSH,
            "muta_detected": BuildOrderType.HYDRA_TIMING,
            "roach_detected": BuildOrderType.ROACH_HYDRA,
        },
    }

    def __init__(self, bot):
        """
        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot

        # 현재 빌드 상태
        self.current_build_type: BuildOrderType = BuildOrderType.HATCH_FIRST
        self.build_steps: List[BuildStep] = []
        self.current_step_index: int = 0

        # 적 정보
        self.enemy_race: str = "Unknown"
        self.detected_strategy: str = "unknown"

        # 빌드 전환 이력
        self.build_history: List[Dict[str, Any]] = []
        self.transition_count: int = 0
        self.last_transition_time: float = 0.0

        # 빌드 전환 쿨다운 (초) - 너무 잦은 전환 방지
        self.transition_cooldown: float = 60.0

        # 동적 수정 플래그
        self.emergency_override: bool = False
        self.air_response_active: bool = False
        self.rush_defense_active: bool = False

        print("[ADAPTIVE_BUILD] 적응형 빌드오더 관리자 초기화 완료")

    def select_initial_build(self, enemy_race: str = "Unknown") -> BuildOrderType:
        """
        초기 빌드오더 선택

        Args:
            enemy_race: 적 종족 ("Terran", "Protoss", "Zerg", "Unknown")

        Returns:
            선택된 빌드오더 타입
        """
        self.enemy_race = enemy_race

        # 종족별 기본 빌드 선택
        race_builds = self.BUILD_LIBRARY.get(enemy_race, {})
        build_type = race_builds.get("default", BuildOrderType.HATCH_FIRST)

        self.current_build_type = build_type
        self.build_steps = self._create_build_steps(build_type)

        print(f"[ADAPTIVE_BUILD] 초기 빌드 선택: {build_type.value} (vs {enemy_race})")
        return build_type

    def update(self, scout_info: Optional[Dict[str, Any]] = None) -> None:
        """
        빌드오더 업데이트 (매 스텝 호출)

        Args:
            scout_info: 정찰 정보 딕셔너리
        """
        game_time = getattr(self.bot, "time", 0.0)

        # 적 종족 감지
        if self.enemy_race == "Unknown":
            self._detect_enemy_race()

        # 정찰 정보 기반 빌드 수정
        if scout_info:
            self._process_scout_info(scout_info, game_time)

        # 자동 전환 체크
        self._check_auto_transitions(game_time)

        # 빌드 스텝 완료 체크
        self._update_step_completion()

    def get_next_build_step(self) -> Optional[BuildStep]:
        """
        다음 실행할 빌드 스텝 반환

        Returns:
            다음 빌드 스텝 (또는 None)
        """
        current_supply = getattr(self.bot, "supply_used", 0)

        for step in self.build_steps[self.current_step_index:]:
            if step.completed or step.skipped:
                continue

            # 서플라이 조건 체크
            if current_supply >= step.supply:
                # 조건부 스텝 체크
                if step.condition and not self._check_condition(step.condition):
                    continue
                return step

        return None

    def transition_build(self, new_build_type: BuildOrderType, reason: str = "") -> bool:
        """
        빌드오더 전환

        Args:
            new_build_type: 새 빌드오더 타입
            reason: 전환 사유

        Returns:
            전환 성공 여부
        """
        game_time = getattr(self.bot, "time", 0.0)

        # 쿨다운 체크
        if game_time - self.last_transition_time < self.transition_cooldown:
            return False

        # 동일 빌드면 스킵
        if new_build_type == self.current_build_type:
            return False

        old_build = self.current_build_type
        self.current_build_type = new_build_type

        # 새 빌드 스텝 생성 (현재 서플라이 이후의 스텝만)
        current_supply = getattr(self.bot, "supply_used", 0)
        new_steps = self._create_build_steps(new_build_type)
        self.build_steps = [s for s in new_steps if s.supply >= current_supply]
        self.current_step_index = 0

        # 이력 기록
        self.transition_count += 1
        self.last_transition_time = game_time
        self.build_history.append({
            "time": game_time,
            "from": old_build.value,
            "to": new_build_type.value,
            "reason": reason,
        })

        print(f"[ADAPTIVE_BUILD] 빌드 전환: {old_build.value} -> {new_build_type.value} "
              f"(사유: {reason})")
        return True

    def _detect_enemy_race(self) -> None:
        """적 종족 감지"""
        enemy_race = getattr(self.bot, "enemy_race", None)
        if enemy_race is not None:
            race_str = str(enemy_race)
            if "Terran" in race_str:
                self.enemy_race = "Terran"
            elif "Protoss" in race_str:
                self.enemy_race = "Protoss"
            elif "Zerg" in race_str:
                self.enemy_race = "Zerg"

            if self.enemy_race != "Unknown":
                self.select_initial_build(self.enemy_race)

    def _process_scout_info(self, scout_info: Dict[str, Any], game_time: float) -> None:
        """
        정찰 정보 기반 빌드 수정

        Args:
            scout_info: 정찰 정보
            game_time: 현재 게임 시간
        """
        strategy = scout_info.get("detected_strategy", "unknown")
        if strategy == self.detected_strategy:
            return  # 이미 동일 전략 감지

        self.detected_strategy = strategy

        # 종족별 대응 빌드 선택
        race_builds = self.BUILD_LIBRARY.get(self.enemy_race, {})

        if "rush" in strategy.lower():
            new_build = race_builds.get("rush_detected", BuildOrderType.POOL_FIRST)
            self.transition_build(new_build, f"러시 감지: {strategy}")
            self.rush_defense_active = True

        elif "air" in strategy.lower() or "stargate" in strategy.lower():
            new_build = race_builds.get("air_detected", BuildOrderType.HYDRA_TIMING)
            self.transition_build(new_build, f"공중 위협 감지: {strategy}")
            self.air_response_active = True

        elif "mech" in strategy.lower():
            new_build = race_builds.get("mech_detected", BuildOrderType.ROACH_HYDRA)
            self.transition_build(new_build, f"기계 유닛 감지: {strategy}")

        elif "bio" in strategy.lower():
            new_build = race_builds.get("bio_detected", BuildOrderType.LING_BANE)
            self.transition_build(new_build, f"바이오닉 감지: {strategy}")

    def _check_auto_transitions(self, game_time: float) -> None:
        """시간 기반 자동 빌드 전환"""
        # 5분 이후 여전히 초기 빌드면 매크로 전환
        if game_time > 300 and self.transition_count == 0:
            if self.current_build_type in (BuildOrderType.POOL_FIRST,
                                           BuildOrderType.TWELVE_POOL):
                self.transition_build(BuildOrderType.ROACH_HYDRA, "5분 경과, 매크로 전환")

        # 10분 이후 후반 전환
        if game_time > 600 and self.current_build_type == BuildOrderType.ROACH_RUSH:
            self.transition_build(BuildOrderType.ROACH_HYDRA, "후반 전환")

    def _update_step_completion(self) -> None:
        """빌드 스텝 완료 상태 업데이트"""
        # 현재 서플라이보다 낮은 스텝은 완료 처리
        current_supply = getattr(self.bot, "supply_used", 0)

        for i, step in enumerate(self.build_steps):
            if not step.completed and step.supply < current_supply - 5:
                step.completed = True
                if i == self.current_step_index:
                    self.current_step_index += 1

    def _check_condition(self, condition: str) -> bool:
        """조건부 스텝의 조건 확인"""
        if condition == "enemy_air_detected":
            return self.air_response_active
        elif condition == "rush_detected":
            return self.rush_defense_active
        elif condition == "has_lair":
            if hasattr(self.bot, "structures") and UnitTypeId:
                return self.bot.structures(UnitTypeId.LAIR).exists
        return True

    def _create_build_steps(self, build_type: BuildOrderType) -> List[BuildStep]:
        """
        빌드오더 타입에 따른 빌드 스텝 생성

        Args:
            build_type: 빌드오더 종류

        Returns:
            빌드 스텝 리스트
        """
        if build_type == BuildOrderType.HATCH_FIRST:
            return self._build_hatch_first()
        elif build_type == BuildOrderType.POOL_FIRST:
            return self._build_pool_first()
        elif build_type == BuildOrderType.TWELVE_POOL:
            return self._build_twelve_pool()
        elif build_type == BuildOrderType.ROACH_RUSH:
            return self._build_roach_rush()
        elif build_type == BuildOrderType.LING_BANE:
            return self._build_ling_bane()
        elif build_type == BuildOrderType.HYDRA_TIMING:
            return self._build_hydra_timing()
        elif build_type == BuildOrderType.ROACH_HYDRA:
            return self._build_roach_hydra()
        elif build_type == BuildOrderType.MUTA_LING:
            return self._build_muta_ling()
        else:
            return self._build_hatch_first()

    def _build_hatch_first(self) -> List[BuildStep]:
        """해처리 퍼스트 빌드"""
        return [
            BuildStep(13, "train", "overlord", priority=1),
            BuildStep(16, "build", "hatchery", priority=1),
            BuildStep(18, "build", "extractor", priority=2),
            BuildStep(17, "build", "spawning_pool", priority=1),
            BuildStep(20, "train", "queen", priority=1),
            BuildStep(20, "train", "zergling", priority=3),
            BuildStep(24, "train", "queen", priority=2),
            BuildStep(30, "build", "roach_warren", priority=3),
            BuildStep(30, "train", "overlord", priority=2),
            BuildStep(36, "build", "hatchery", priority=2),
            BuildStep(36, "train", "roach", priority=3),
            BuildStep(44, "morph", "lair", priority=3),
        ]

    def _build_pool_first(self) -> List[BuildStep]:
        """풀 퍼스트 빌드 (안전형)"""
        return [
            BuildStep(13, "train", "overlord", priority=1),
            BuildStep(14, "build", "spawning_pool", priority=1),
            BuildStep(16, "build", "hatchery", priority=1),
            BuildStep(16, "train", "queen", priority=1),
            BuildStep(18, "train", "zergling", priority=2),
            BuildStep(19, "train", "zergling", priority=2),
            BuildStep(20, "build", "extractor", priority=2),
            BuildStep(22, "train", "queen", priority=2),
            BuildStep(24, "train", "overlord", priority=2),
            BuildStep(28, "build", "roach_warren", priority=3),
            BuildStep(30, "train", "roach", priority=3),
        ]

    def _build_twelve_pool(self) -> List[BuildStep]:
        """12풀 공격 빌드"""
        return [
            BuildStep(12, "build", "spawning_pool", priority=1),
            BuildStep(12, "train", "drone", priority=2),
            BuildStep(13, "train", "overlord", priority=1),
            BuildStep(14, "train", "zergling", priority=1),
            BuildStep(14, "train", "zergling", priority=1),
            BuildStep(16, "train", "queen", priority=2),
            BuildStep(16, "train", "zergling", priority=1),
            BuildStep(18, "build", "hatchery", priority=3),
        ]

    def _build_roach_rush(self) -> List[BuildStep]:
        """바퀴 러시 빌드"""
        return [
            BuildStep(13, "train", "overlord", priority=1),
            BuildStep(16, "build", "hatchery", priority=1),
            BuildStep(17, "build", "spawning_pool", priority=1),
            BuildStep(17, "build", "extractor", priority=2),
            BuildStep(19, "train", "queen", priority=1),
            BuildStep(20, "build", "roach_warren", priority=1),
            BuildStep(22, "train", "roach", priority=1),
            BuildStep(22, "train", "overlord", priority=2),
            BuildStep(26, "train", "roach", priority=1),
            BuildStep(30, "train", "roach", priority=1),
            BuildStep(34, "train", "overlord", priority=2),
        ]

    def _build_ling_bane(self) -> List[BuildStep]:
        """저글링+맹독충 빌드"""
        return [
            BuildStep(13, "train", "overlord", priority=1),
            BuildStep(16, "build", "hatchery", priority=1),
            BuildStep(17, "build", "spawning_pool", priority=1),
            BuildStep(18, "build", "extractor", priority=2),
            BuildStep(19, "train", "queen", priority=1),
            BuildStep(20, "train", "zergling", priority=1),
            BuildStep(22, "build", "baneling_nest", priority=1),
            BuildStep(24, "train", "zergling", priority=1),
            BuildStep(26, "train", "overlord", priority=2),
            BuildStep(28, "morph", "baneling", priority=1),
            BuildStep(30, "upgrade", "zergling_speed", priority=2),
        ]

    def _build_hydra_timing(self) -> List[BuildStep]:
        """히드라 타이밍 빌드"""
        return [
            BuildStep(13, "train", "overlord", priority=1),
            BuildStep(16, "build", "hatchery", priority=1),
            BuildStep(17, "build", "spawning_pool", priority=1),
            BuildStep(18, "build", "extractor", priority=2),
            BuildStep(19, "train", "queen", priority=1),
            BuildStep(22, "train", "queen", priority=2),
            BuildStep(26, "build", "roach_warren", priority=3),
            BuildStep(30, "morph", "lair", priority=1),
            BuildStep(36, "build", "hydralisk_den", priority=1),
            BuildStep(36, "build", "extractor", priority=2),
            BuildStep(40, "train", "hydralisk", priority=1),
            BuildStep(44, "train", "hydralisk", priority=1),
            BuildStep(48, "train", "overlord", priority=2),
        ]

    def _build_roach_hydra(self) -> List[BuildStep]:
        """바퀴+히드라 빌드"""
        return [
            BuildStep(13, "train", "overlord", priority=1),
            BuildStep(16, "build", "hatchery", priority=1),
            BuildStep(17, "build", "spawning_pool", priority=1),
            BuildStep(18, "build", "extractor", priority=2),
            BuildStep(19, "train", "queen", priority=1),
            BuildStep(20, "build", "roach_warren", priority=2),
            BuildStep(22, "train", "roach", priority=2),
            BuildStep(26, "morph", "lair", priority=2),
            BuildStep(30, "build", "hydralisk_den", priority=2),
            BuildStep(30, "build", "extractor", priority=3),
            BuildStep(36, "train", "hydralisk", priority=2),
            BuildStep(40, "train", "roach", priority=3),
            BuildStep(44, "build", "hatchery", priority=3),
        ]

    def _build_muta_ling(self) -> List[BuildStep]:
        """뮤탈+저글링 빌드"""
        return [
            BuildStep(13, "train", "overlord", priority=1),
            BuildStep(16, "build", "hatchery", priority=1),
            BuildStep(17, "build", "spawning_pool", priority=1),
            BuildStep(18, "build", "extractor", priority=2),
            BuildStep(19, "train", "queen", priority=1),
            BuildStep(20, "upgrade", "zergling_speed", priority=1),
            BuildStep(22, "train", "zergling", priority=2),
            BuildStep(26, "morph", "lair", priority=1),
            BuildStep(28, "build", "extractor", priority=2),
            BuildStep(30, "build", "spire", priority=1),
            BuildStep(36, "train", "mutalisk", priority=1),
            BuildStep(40, "train", "mutalisk", priority=1),
        ]

    def get_current_build_info(self) -> Dict[str, Any]:
        """현재 빌드 정보 반환"""
        return {
            "build_type": self.current_build_type.value,
            "enemy_race": self.enemy_race,
            "detected_strategy": self.detected_strategy,
            "step_index": self.current_step_index,
            "total_steps": len(self.build_steps),
            "transitions": self.transition_count,
            "air_response": self.air_response_active,
            "rush_defense": self.rush_defense_active,
        }
