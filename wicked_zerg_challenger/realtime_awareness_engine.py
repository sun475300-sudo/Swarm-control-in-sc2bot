# -*- coding: utf-8 -*-
"""
Real-time Awareness Engine — 실시간 상황 인식 + 자동 대응 시스템

봇이 매 프레임마다 상황을 이해하고, 문제를 감지하고,
즉각적으로 행동을 수정하는 자율 시스템.

핵심 기능:
1. 상황 진단 (Situation Diagnosis)
2. 문제 감지 (Problem Detection)
3. 자동 처방 (Auto Prescription)
4. 행동 오버라이드 (Action Override)
5. 학습 피드백 (Learning Feedback)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
except ImportError:
    UnitTypeId = None
    UpgradeId = None


@dataclass
class Situation:
    """현재 상황 스냅샷"""
    game_time: float = 0.0
    phase: str = "opening"  # opening, early, mid, late
    minerals: int = 0
    vespene: int = 0
    supply_used: int = 0
    supply_cap: int = 0
    supply_left: int = 0
    worker_count: int = 0
    army_supply: int = 0
    base_count: int = 0
    larva_count: int = 0
    enemy_visible_count: int = 0
    enemy_near_base: bool = False
    enemy_build_pattern: str = "unknown"
    threat_level: str = "none"
    gas_buildings: int = 0
    tech_level: str = "hatchery"  # hatchery, lair, hive


@dataclass
class Problem:
    """감지된 문제"""
    category: str
    severity: str  # critical, high, medium, low
    description: str
    prescription: str
    priority: int  # 1 = highest


@dataclass
class Override:
    """행동 오버라이드 명령"""
    action: str
    unit_type: str
    count: int
    reason: str
    priority: int
    expires_at: float  # game time


class RealtimeAwarenessEngine:
    """
    실시간 상황 인식 + 자동 대응 엔진

    매 프레임:
    1. 상황 스냅샷 생성
    2. 문제 감지 (14가지 패턴)
    3. 처방 생성 → 행동 오버라이드
    4. 봇에 직접 명령 전달
    """

    def __init__(self, bot):
        self.bot = bot
        self.last_update = 0.0
        self.update_interval = 1.0  # 1초마다 진단
        self.situation = Situation()
        self.active_problems: List[Problem] = []
        self.active_overrides: List[Override] = []
        self.problem_history: List[Dict] = []

        # 상황 추적
        self._last_army_supply = 0
        self._army_wipe_detected = False
        self._consecutive_mineral_overflow = 0
        self._consecutive_gas_overflow = 0
        self._last_base_count = 1
        self._emergency_mode = False
        self._force_army_mode = False
        self._force_army_until = 0.0

    def on_step(self, iteration: int) -> List[Override]:
        """
        매 프레임 호출 — 상황 진단 → 문제 감지 → 자동 대응

        Returns:
            List[Override]: 봇이 즉시 실행해야 할 오버라이드 명령들
        """
        game_time = getattr(self.bot, "time", 0.0)
        if game_time - self.last_update < self.update_interval:
            return self.active_overrides
        self.last_update = game_time

        try:
            # Step 1: 상황 스냅샷
            self._capture_situation(game_time)

            # Step 2: 문제 감지
            self.active_problems = self._detect_problems()

            # Step 3: 처방 → 오버라이드
            self.active_overrides = self._generate_overrides(game_time)

            # Step 4: 직접 행동 실행
            self._execute_emergency_actions(game_time)

            # Step 5: 로깅
            if self.active_problems and iteration % 100 == 0:
                self._log_problems()

        except Exception:
            pass

        return self.active_overrides

    # =========================================================================
    # Step 1: 상황 스냅샷
    # =========================================================================

    def _capture_situation(self, game_time: float) -> None:
        """현재 상황 캡처"""
        s = self.situation
        s.game_time = game_time

        # 게임 단계
        if game_time < 120:
            s.phase = "opening"
        elif game_time < 300:
            s.phase = "early"
        elif game_time < 600:
            s.phase = "mid"
        else:
            s.phase = "late"

        # 자원
        s.minerals = getattr(self.bot, "minerals", 0)
        s.vespene = getattr(self.bot, "vespene", 0)
        s.supply_used = getattr(self.bot, "supply_used", 0)
        s.supply_cap = getattr(self.bot, "supply_cap", 0)
        s.supply_left = getattr(self.bot, "supply_left", 0)

        # 유닛
        workers = getattr(self.bot, "workers", None)
        s.worker_count = workers.amount if workers and hasattr(workers, "amount") else 0

        larva = getattr(self.bot, "larva", None)
        s.larva_count = larva.amount if larva and hasattr(larva, "amount") else 0

        # 기지
        townhalls = getattr(self.bot, "townhalls", None)
        s.base_count = townhalls.amount if townhalls and hasattr(townhalls, "amount") else 0

        # 가스 건물
        gas = getattr(self.bot, "gas_buildings", None)
        s.gas_buildings = gas.amount if gas and hasattr(gas, "amount") else 0

        # 군대
        units = getattr(self.bot, "units", None)
        if units and hasattr(units, "__iter__"):
            s.army_supply = sum(
                getattr(u, "supply_cost", 1) for u in units
                if not getattr(u, "is_structure", False) and
                getattr(u.type_id, "name", "") not in ("DRONE", "OVERLORD", "LARVA", "EGG", "OVERSEERSIEGEMODE", "OVERLORDTRANSPORT")
            )
        else:
            s.army_supply = 0

        # 적군
        enemy_units = getattr(self.bot, "enemy_units", [])
        s.enemy_visible_count = len(enemy_units) if hasattr(enemy_units, "__len__") else 0

        # 기지 근접 적
        s.enemy_near_base = False
        if townhalls and s.enemy_visible_count > 0:
            try:
                for th in townhalls:
                    for eu in enemy_units:
                        if hasattr(eu, "distance_to") and eu.distance_to(th) < 25:
                            s.enemy_near_base = True
                            break
                    if s.enemy_near_base:
                        break
            except Exception:
                pass

        # Intel
        if hasattr(self.bot, "intel_manager"):
            intel = self.bot.intel_manager
            s.enemy_build_pattern = getattr(intel, "_enemy_build_pattern", "unknown")
            s.threat_level = getattr(intel, "_threat_level", "none")

        # 테크 레벨
        s.tech_level = "hatchery"
        if UnitTypeId:
            try:
                structures = self.bot.structures
                if structures(UnitTypeId.HIVE).exists:
                    s.tech_level = "hive"
                elif structures(UnitTypeId.LAIR).exists:
                    s.tech_level = "lair"
            except Exception:
                pass

    # =========================================================================
    # Step 2: 문제 감지 (14가지 패턴)
    # =========================================================================

    def _detect_problems(self) -> List[Problem]:
        """14가지 패턴으로 문제 감지"""
        problems = []
        s = self.situation

        # === P1: 군대 전멸 ===
        if s.army_supply <= 2 and self._last_army_supply > 15:
            problems.append(Problem(
                "combat", "critical",
                f"군대 전멸! (army {self._last_army_supply}→{s.army_supply})",
                "모든 라바로 군대 유닛 즉시 생산. 드론 생산 중지.",
                priority=1
            ))
            self._army_wipe_detected = True
            self._force_army_mode = True
            self._force_army_until = s.game_time + 30
        self._last_army_supply = s.army_supply

        # === P2: 가스 과잉 축적 ===
        if s.vespene > 1000 and s.game_time > 180:
            self._consecutive_gas_overflow += 1
            problems.append(Problem(
                "production", "critical" if s.vespene > 2000 else "high",
                f"가스 {s.vespene} 축적 (연속 {self._consecutive_gas_overflow}회)",
                "히드라/뮤탈/바퀴 등 가스 유닛 즉시 대량 생산",
                priority=2
            ))
        else:
            self._consecutive_gas_overflow = 0

        # === P3: 미네랄 과잉 축적 ===
        if s.minerals > 800 and s.game_time > 120:
            self._consecutive_mineral_overflow += 1
            problems.append(Problem(
                "production", "high",
                f"미네랄 {s.minerals} 축적 (연속 {self._consecutive_mineral_overflow}회)",
                "저글링/드론/확장/오버로드 즉시 생산",
                priority=3
            ))
        else:
            self._consecutive_mineral_overflow = 0

        # === P4: 서플라이 블록 ===
        if s.supply_left <= 0 and s.supply_cap < 200:
            problems.append(Problem(
                "production", "critical",
                f"서플라이 블록! (supply {s.supply_used}/{s.supply_cap})",
                "오버로드 3마리 즉시 생산",
                priority=1
            ))

        # === P5: 기지 공격받는 중 ===
        if s.enemy_near_base:
            problems.append(Problem(
                "defense", "critical",
                f"기지 공격받는 중! (적 {s.enemy_visible_count}기 근접)",
                "모든 군대 기지 방어 집결. 일꾼 대피 또는 전투 투입.",
                priority=1
            ))

        # === P6: 확장 부족 ===
        if s.game_time > 150 and s.base_count < 2:
            problems.append(Problem(
                "economy", "high",
                f"2분 30초인데 확장 미실시 (기지 {s.base_count}개)",
                "즉시 해처리 확장. 미네랄 300 확보 필요.",
                priority=4
            ))
        elif s.game_time > 360 and s.base_count < 3:
            problems.append(Problem(
                "economy", "medium",
                "6분인데 3확장 미실시",
                "3번째 해처리 건설 필요",
                priority=5
            ))

        # === P7: 과잉 드론 (군대 부족) ===
        if s.worker_count > 44 and s.army_supply < 15 and s.game_time > 240:
            problems.append(Problem(
                "economy", "high",
                f"과잉 드론: 일꾼 {s.worker_count} vs 군대 {s.army_supply}",
                "드론 생산 중지. 모든 라바 군대 유닛 전환.",
                priority=2
            ))

        # === P8: 라바 방치 ===
        if s.larva_count > 8 and s.game_time > 90:
            problems.append(Problem(
                "macro", "high",
                f"라바 {s.larva_count}마리 방치",
                "즉시 유닛 생산 (군대 또는 드론)",
                priority=3
            ))

        # === P9: 가스 미개발 ===
        if s.gas_buildings < 1 and s.game_time > 120:
            problems.append(Problem(
                "economy", "high",
                "가스 건물 0개 — 테크 불가",
                "즉시 익스트랙터 건설",
                priority=3
            ))
        elif s.gas_buildings < 2 and s.game_time > 240 and s.base_count >= 2:
            problems.append(Problem(
                "economy", "medium",
                f"가스 건물 {s.gas_buildings}개 (기지 {s.base_count}개)",
                "2번째 가스 개발 필요",
                priority=5
            ))

        # === P10: 저서플 후반 ===
        if s.phase == "mid" and s.supply_used < 80:
            problems.append(Problem(
                "production", "high",
                f"중반인데 서플 {s.supply_used} (목표 80+)",
                "생산 대폭 가속. 모든 해처리에서 유닛 생산.",
                priority=3
            ))
        elif s.phase == "late" and s.supply_used < 130:
            problems.append(Problem(
                "production", "critical",
                f"후반인데 서플 {s.supply_used} (목표 150+)",
                "즉시 200 서플 목표 생산 가속!",
                priority=2
            ))

        # === P11: 테크 지연 ===
        if s.game_time > 360 and s.tech_level == "hatchery":
            problems.append(Problem(
                "strategy", "high",
                "6분인데 아직 해처리 테크 — 레어 필요",
                "즉시 레어 변태 시작",
                priority=4
            ))

        # === P12: 기지 상실 ===
        if s.base_count < self._last_base_count and self._last_base_count > 0:
            problems.append(Problem(
                "defense", "critical",
                f"기지 상실! ({self._last_base_count}→{s.base_count})",
                "방어 강화 + 재확장 준비",
                priority=1
            ))
        self._last_base_count = s.base_count

        # === P13: 정찰 공백 ===
        if s.enemy_visible_count == 0 and s.game_time > 180:
            problems.append(Problem(
                "scouting", "medium",
                "적 시야 0 — 정찰 공백",
                "오버시어/저글링 정찰 파견",
                priority=6
            ))

        # === P14: vs Protoss 취약 구성 ===
        if "protoss" in s.enemy_build_pattern.lower() or (
            hasattr(self.bot, "enemy_race") and
            getattr(getattr(self.bot, "enemy_race", None), "name", "") == "Protoss"
        ):
            if s.army_supply > 0 and s.game_time > 300:
                # 프로토스전에서 바퀴/히드라 없으면 위험
                has_counter = False
                try:
                    units = self.bot.units
                    roach_count = units(UnitTypeId.ROACH).amount if UnitTypeId else 0
                    hydra_count = units(UnitTypeId.HYDRALISK).amount if UnitTypeId else 0
                    ravager_count = units(UnitTypeId.RAVAGER).amount if UnitTypeId else 0
                    if roach_count + hydra_count + ravager_count >= 5:
                        has_counter = True
                except Exception:
                    pass

                if not has_counter:
                    problems.append(Problem(
                        "adaptation", "high",
                        "vs Protoss인데 카운터 유닛(바퀴/히드라) 부족",
                        "바퀴굴/히드라굴 건설 후 가스 유닛 대량 생산",
                        priority=2
                    ))

        # 우선순위 정렬
        problems.sort(key=lambda p: p.priority)
        return problems

    # =========================================================================
    # Step 3: 오버라이드 생성
    # =========================================================================

    def _generate_overrides(self, game_time: float) -> List[Override]:
        """문제에 대한 행동 오버라이드 명령 생성"""
        overrides = []

        for problem in self.active_problems[:5]:  # 상위 5개만 처리
            if problem.category == "production" and "가스" in problem.description:
                overrides.append(Override(
                    action="train", unit_type="ROACH", count=5,
                    reason=problem.prescription,
                    priority=problem.priority,
                    expires_at=game_time + 15
                ))
            elif problem.category == "production" and "서플라이 블록" in problem.description:
                overrides.append(Override(
                    action="train", unit_type="OVERLORD", count=3,
                    reason=problem.prescription,
                    priority=problem.priority,
                    expires_at=game_time + 10
                ))
            elif problem.category == "combat" and "전멸" in problem.description:
                overrides.append(Override(
                    action="force_army", unit_type="ANY_ARMY", count=20,
                    reason=problem.prescription,
                    priority=1,
                    expires_at=game_time + 30
                ))
            elif problem.category == "economy" and "확장" in problem.description:
                overrides.append(Override(
                    action="expand", unit_type="HATCHERY", count=1,
                    reason=problem.prescription,
                    priority=problem.priority,
                    expires_at=game_time + 20
                ))

        # 만료된 오버라이드 제거
        overrides = [o for o in overrides if o.expires_at > game_time]
        return overrides

    # =========================================================================
    # Step 4: 긴급 행동 직접 실행
    # =========================================================================

    def _execute_emergency_actions(self, game_time: float) -> None:
        """가장 긴급한 행동을 봇에 직접 실행"""
        if not UnitTypeId:
            return

        s = self.situation

        # === 긴급 1: 가스 유닛 강제 생산 ===
        if s.vespene > 1200 and s.larva_count > 0:
            self._force_produce_gas_units()

        # === 긴급 2: 군대 전멸 후 재건 ===
        if self._force_army_mode and game_time < self._force_army_until:
            self._force_army_production()
        elif game_time >= self._force_army_until:
            self._force_army_mode = False

        # === 긴급 3: 서플라이 블록 해소 ===
        if s.supply_left <= 0 and s.supply_cap < 200:
            self._force_overlord_production()

        # === 긴급 4: 미네랄 플러시 ===
        if s.minerals > 1500 and s.larva_count > 3:
            self._flush_minerals()

    def _force_produce_gas_units(self) -> None:
        """가스 유닛 강제 생산"""
        try:
            larva = self.bot.larva
            if not larva.exists:
                return

            # 히드라굴 있으면 히드라
            if self.bot.structures(UnitTypeId.HYDRALISKDEN).ready.exists:
                if self.bot.can_afford(UnitTypeId.HYDRALISK):
                    l = larva.random
                    result = self.bot.do(l.train(UnitTypeId.HYDRALISK))
                    if hasattr(result, "__await__"):
                        import asyncio
                        asyncio.ensure_future(result)
                    return

            # 바퀴굴 있으면 바퀴
            if self.bot.structures(UnitTypeId.ROACHWARREN).ready.exists:
                if self.bot.can_afford(UnitTypeId.ROACH):
                    l = larva.random
                    result = self.bot.do(l.train(UnitTypeId.ROACH))
                    if hasattr(result, "__await__"):
                        import asyncio
                        asyncio.ensure_future(result)
                    return

            # 스파이어 있으면 뮤탈
            if self.bot.structures(UnitTypeId.SPIRE).ready.exists:
                if self.bot.can_afford(UnitTypeId.MUTALISK):
                    l = larva.random
                    result = self.bot.do(l.train(UnitTypeId.MUTALISK))
                    if hasattr(result, "__await__"):
                        import asyncio
                        asyncio.ensure_future(result)
                    return
        except Exception:
            pass

    def _force_army_production(self) -> None:
        """군대 강제 대량 생산"""
        try:
            larva = self.bot.larva
            if not larva.exists:
                return

            for _ in range(min(larva.amount, 5)):
                if not larva.exists:
                    break
                l = larva.first

                # 가스 유닛 우선
                if self.bot.vespene >= 100:
                    if (self.bot.structures(UnitTypeId.ROACHWARREN).ready.exists and
                            self.bot.can_afford(UnitTypeId.ROACH)):
                        result = self.bot.do(l.train(UnitTypeId.ROACH))
                        if hasattr(result, "__await__"):
                            import asyncio
                            asyncio.ensure_future(result)
                        continue

                # 저글링
                if (self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready.exists and
                        self.bot.can_afford(UnitTypeId.ZERGLING)):
                    result = self.bot.do(l.train(UnitTypeId.ZERGLING))
                    if hasattr(result, "__await__"):
                        import asyncio
                        asyncio.ensure_future(result)
        except Exception:
            pass

    def _force_overlord_production(self) -> None:
        """오버로드 강제 생산"""
        try:
            larva = self.bot.larva
            if larva.exists and self.bot.can_afford(UnitTypeId.OVERLORD):
                l = larva.first
                result = self.bot.do(l.train(UnitTypeId.OVERLORD))
                if hasattr(result, "__await__"):
                    import asyncio
                    asyncio.ensure_future(result)
        except Exception:
            pass

    def _flush_minerals(self) -> None:
        """미네랄 긴급 소비"""
        try:
            larva = self.bot.larva
            if not larva.exists:
                return

            # 저글링 대량 생산
            for _ in range(min(larva.amount, 8)):
                if not larva.exists or not self.bot.can_afford(UnitTypeId.ZERGLING):
                    break
                l = larva.first
                if self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
                    result = self.bot.do(l.train(UnitTypeId.ZERGLING))
                    if hasattr(result, "__await__"):
                        import asyncio
                        asyncio.ensure_future(result)
        except Exception:
            pass

    # =========================================================================
    # 유틸리티
    # =========================================================================

    def _log_problems(self) -> None:
        """문제 로그 출력"""
        if not self.active_problems:
            return
        critical = [p for p in self.active_problems if p.severity == "critical"]
        if critical:
            print(f"[AWARENESS] {len(critical)} CRITICAL problems:")
            for p in critical[:3]:
                print(f"  [{p.severity.upper()}] {p.description}")
                print(f"    → {p.prescription}")

    def get_situation_summary(self) -> str:
        """현재 상황 요약"""
        s = self.situation
        problems_str = ", ".join(p.category for p in self.active_problems[:3]) or "none"
        return (
            f"[{s.phase.upper()}] {s.game_time:.0f}s | "
            f"Supply: {s.supply_used}/{s.supply_cap} | "
            f"Army: {s.army_supply} | Workers: {s.worker_count} | "
            f"Bases: {s.base_count} | M:{s.minerals} G:{s.vespene} | "
            f"Threats: {s.threat_level} | Problems: {problems_str}"
        )

    @property
    def is_emergency(self) -> bool:
        """긴급 상황 여부"""
        return any(p.severity == "critical" for p in self.active_problems)

    @property
    def should_force_army(self) -> bool:
        """군대 강제 생산 모드 여부"""
        return self._force_army_mode
