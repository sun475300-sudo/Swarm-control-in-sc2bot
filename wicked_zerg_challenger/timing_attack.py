# -*- coding: utf-8 -*-
"""
Timing Attack Planner - 타이밍 공격 플래너 (#107)

특정 유닛 구성이 완성되면 타이밍 공격을 개시하는 시스템입니다.

주요 기능:
1. 타이밍 공격 윈도우 감지 (유닛 수, 업그레이드 완료)
2. 공격 조건 충족 시 자동 개시
3. 공격 성공/실패 판단
4. 타이밍별 공격 계획 관리
5. 공격 중단/철수 판단
"""

from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
except ImportError:
    UnitTypeId = None
    UpgradeId = None


class AttackPhase(Enum):
    """공격 페이즈"""
    PREPARING = "preparing"      # 준비 중
    LAUNCHING = "launching"      # 개시
    ATTACKING = "attacking"      # 공격 중
    RETREATING = "retreating"    # 철수 중
    COMPLETED = "completed"      # 완료
    FAILED = "failed"            # 실패


class TimingWindow:
    """타이밍 공격 윈도우"""

    def __init__(self, name: str, min_supply: int, required_units: Dict[str, int],
                 required_upgrades: Optional[List[str]] = None,
                 max_time: float = 0.0, priority: int = 5):
        """
        Args:
            name: 타이밍 이름
            min_supply: 최소 군대 서플라이
            required_units: 필요 유닛 조합 {"roach": 10, "ravager": 4}
            required_upgrades: 필요 업그레이드 리스트
            max_time: 최대 시간 (0이면 무제한)
            priority: 우선순위 (1=최고, 10=최저)
        """
        self.name = name
        self.min_supply = min_supply
        self.required_units = required_units
        self.required_upgrades = required_upgrades or []
        self.max_time = max_time
        self.priority = priority

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "name": self.name,
            "min_supply": self.min_supply,
            "required_units": self.required_units,
            "required_upgrades": self.required_upgrades,
            "max_time": self.max_time,
            "priority": self.priority,
        }


class AttackPlan:
    """실행 중인 공격 계획"""

    def __init__(self, timing: TimingWindow, start_time: float):
        """
        Args:
            timing: 타이밍 윈도우
            start_time: 공격 개시 시간
        """
        self.timing = timing
        self.start_time = start_time
        self.phase = AttackPhase.LAUNCHING
        self.army_supply_at_start: int = 0
        self.current_army_supply: int = 0
        self.enemies_killed: int = 0
        self.units_lost: int = 0
        self.damage_dealt: float = 0.0
        self.target_position: Optional[Tuple[float, float]] = None

    @property
    def duration(self) -> float:
        """공격 경과 시간"""
        return 0.0  # 실제 구현에서는 현재 시간 - 시작 시간

    def is_successful(self) -> bool:
        """공격 성공 여부 판단"""
        # 아군 손실률 30% 미만이면서 적 킬이 있으면 성공
        if self.army_supply_at_start == 0:
            return False
        loss_ratio = self.units_lost / max(self.army_supply_at_start, 1)
        return loss_ratio < 0.3 and self.enemies_killed > 0


# 사전 정의된 타이밍 공격 윈도우
PREDEFINED_TIMINGS = {
    "roach_timing": TimingWindow(
        name="바퀴 타이밍",
        min_supply=40,
        required_units={"roach": 8, "ravager": 2},
        max_time=360.0,  # 6분
        priority=3,
    ),
    "roach_hydra_push": TimingWindow(
        name="바퀴+히드라 푸시",
        min_supply=60,
        required_units={"roach": 10, "hydralisk": 6},
        required_upgrades=["ZERGGROUNDARMORSLEVEL1"],
        max_time=480.0,  # 8분
        priority=2,
    ),
    "ling_bane_allin": TimingWindow(
        name="저글링+맹독충 올인",
        min_supply=44,
        required_units={"zergling": 20, "baneling": 8},
        required_upgrades=["ZERGLINGMOVEMENTSPEED"],
        max_time=300.0,  # 5분
        priority=1,
    ),
    "hydra_timing": TimingWindow(
        name="히드라 타이밍",
        min_supply=55,
        required_units={"hydralisk": 12},
        max_time=420.0,  # 7분
        priority=3,
    ),
    "muta_harass": TimingWindow(
        name="뮤탈 견제",
        min_supply=30,
        required_units={"mutalisk": 7},
        max_time=480.0,  # 8분
        priority=4,
    ),
    "maxout_push": TimingWindow(
        name="맥스아웃 푸시",
        min_supply=180,
        required_units={},  # 서플라이만 체크
        max_time=900.0,  # 15분
        priority=1,
    ),
}


class TimingAttackPlanner:
    """
    타이밍 공격 플래너

    유닛 구성과 업그레이드 완료를 모니터링하여
    최적의 타이밍에 공격을 개시합니다.

    사용 예:
        planner = TimingAttackPlanner(bot)
        planner.update()  # 매 스텝 호출
        if planner.should_attack():
            plan = planner.get_active_plan()
            # 공격 실행
    """

    def __init__(self, bot):
        """
        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot

        # 등록된 타이밍 윈도우
        self.timings: Dict[str, TimingWindow] = dict(PREDEFINED_TIMINGS)

        # 활성 공격 계획
        self.active_plan: Optional[AttackPlan] = None

        # 공격 이력
        self.attack_history: List[Dict[str, Any]] = []

        # 상태
        self.attack_ready: bool = False
        self.last_check_time: float = 0.0
        self.check_interval: float = 2.0  # 2초마다 체크

        # 연속 실패 카운터
        self.consecutive_failures: int = 0
        self.max_failures_before_pause: int = 3

        print("[TIMING_ATTACK] 타이밍 공격 플래너 초기화 완료")

    def update(self) -> None:
        """매 스텝 업데이트"""
        game_time = getattr(self.bot, "time", 0.0)

        # 체크 간격 확인
        if game_time - self.last_check_time < self.check_interval:
            return
        self.last_check_time = game_time

        # 활성 공격이 있으면 상태 업데이트
        if self.active_plan:
            self._update_attack_status(game_time)
            return

        # 연속 실패 시 잠시 공격 자제
        if self.consecutive_failures >= self.max_failures_before_pause:
            if game_time < self.last_check_time + 120:  # 2분 대기
                return
            self.consecutive_failures = 0

        # 타이밍 윈도우 체크
        self._check_timing_windows(game_time)

    def should_attack(self) -> bool:
        """공격해야 하는지 여부"""
        return self.attack_ready and self.active_plan is not None

    def get_active_plan(self) -> Optional[AttackPlan]:
        """현재 활성 공격 계획 반환"""
        return self.active_plan

    def launch_attack(self, timing_name: str = "") -> Optional[AttackPlan]:
        """
        공격 개시

        Args:
            timing_name: 타이밍 이름 (비어있으면 자동 선택)

        Returns:
            공격 계획 (또는 None)
        """
        game_time = getattr(self.bot, "time", 0.0)

        if timing_name and timing_name in self.timings:
            timing = self.timings[timing_name]
        elif self.attack_ready and self._best_timing:
            timing = self._best_timing
        else:
            return None

        plan = AttackPlan(timing, game_time)
        plan.army_supply_at_start = getattr(self.bot, "supply_army", 0)
        plan.phase = AttackPhase.LAUNCHING

        self.active_plan = plan
        self.attack_ready = False

        print(f"[TIMING_ATTACK] 공격 개시: {timing.name} "
              f"(supply={plan.army_supply_at_start})")
        return plan

    def retreat(self) -> None:
        """공격 철수"""
        if self.active_plan:
            self.active_plan.phase = AttackPhase.RETREATING
            print(f"[TIMING_ATTACK] 철수: {self.active_plan.timing.name}")

    def _check_timing_windows(self, game_time: float) -> None:
        """타이밍 윈도우 조건 체크"""
        self._best_timing = None
        best_priority = 999

        army_supply = getattr(self.bot, "supply_army", 0)

        for name, timing in self.timings.items():
            # 시간 제한 체크
            if timing.max_time > 0 and game_time > timing.max_time:
                continue

            # 서플라이 체크
            if army_supply < timing.min_supply:
                continue

            # 필요 유닛 체크
            if not self._check_required_units(timing):
                continue

            # 필요 업그레이드 체크
            if not self._check_required_upgrades(timing):
                continue

            # 우선순위 비교
            if timing.priority < best_priority:
                best_priority = timing.priority
                self._best_timing = timing

        if self._best_timing:
            self.attack_ready = True

    def _check_required_units(self, timing: TimingWindow) -> bool:
        """필요 유닛 보유 여부 체크"""
        if not timing.required_units:
            return True

        if not hasattr(self.bot, "units"):
            return False

        for unit_name, required_count in timing.required_units.items():
            current_count = 0
            for unit in self.bot.units:
                try:
                    if getattr(unit.type_id, "name", "").upper() == unit_name.upper():
                        current_count += 1
                except Exception:
                    continue
            if current_count < required_count:
                return False

        return True

    def _check_required_upgrades(self, timing: TimingWindow) -> bool:
        """필요 업그레이드 완료 여부 체크"""
        if not timing.required_upgrades:
            return True

        if not hasattr(self.bot, "state") or not hasattr(self.bot.state, "upgrades"):
            return False

        completed_upgrades = set()
        for upgrade in self.bot.state.upgrades:
            try:
                completed_upgrades.add(getattr(upgrade, "name", str(upgrade)).upper())
            except Exception:
                continue

        for required in timing.required_upgrades:
            if required.upper() not in completed_upgrades:
                return False

        return True

    def _update_attack_status(self, game_time: float) -> None:
        """진행 중인 공격 상태 업데이트"""
        if not self.active_plan:
            return

        plan = self.active_plan
        plan.current_army_supply = getattr(self.bot, "supply_army", 0)

        # 공격 지속 시간 체크 (최대 3분)
        elapsed = game_time - plan.start_time
        if elapsed > 180:
            self._end_attack("시간 초과")
            return

        # 아군 손실률 체크
        if plan.army_supply_at_start > 0:
            supply_lost = plan.army_supply_at_start - plan.current_army_supply
            loss_ratio = supply_lost / plan.army_supply_at_start

            if loss_ratio > 0.5:
                # 50% 이상 손실 -> 실패로 판정
                plan.phase = AttackPhase.FAILED
                self._end_attack("과도한 손실")
                return

        # 적 기지 근처 도달 시 ATTACKING 페이즈로 전환
        if plan.phase == AttackPhase.LAUNCHING:
            plan.phase = AttackPhase.ATTACKING

    def _end_attack(self, reason: str) -> None:
        """공격 종료 처리"""
        if not self.active_plan:
            return

        plan = self.active_plan
        success = plan.is_successful()

        if not success:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0

        # 이력 기록
        self.attack_history.append({
            "timing": plan.timing.name,
            "start_time": plan.start_time,
            "supply_at_start": plan.army_supply_at_start,
            "supply_at_end": plan.current_army_supply,
            "success": success,
            "reason": reason,
        })

        result_str = "성공" if success else "실패"
        print(f"[TIMING_ATTACK] 공격 종료 ({result_str}): {plan.timing.name} - {reason}")

        self.active_plan = None
        self.attack_ready = False

    def register_timing(self, name: str, timing: TimingWindow) -> None:
        """새 타이밍 윈도우 등록"""
        self.timings[name] = timing

    def get_status(self) -> Dict[str, Any]:
        """타이밍 공격 상태 반환"""
        return {
            "attack_ready": self.attack_ready,
            "active_plan": self.active_plan.timing.name if self.active_plan else None,
            "consecutive_failures": self.consecutive_failures,
            "total_attacks": len(self.attack_history),
            "registered_timings": list(self.timings.keys()),
        }
