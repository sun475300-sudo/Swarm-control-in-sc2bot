"""
Queen Inject Optimizer - 완벽한 Inject 타이밍 자동화

★ Phase 18: Enhanced Features ★
- 인젝트 미스 감지 및 자동 보정
- 여왕 역할 분담 시스템 (Inject/Defense/Creep)
- 에너지 기반 스마트 우선순위
- 29초 Inject 쿨다운 정밀 추적
- 기지당 Multiple Queen 로테이션
- Inject 우선순위 (메인 > 자연 확장 > 3rd)

Features:
- Perfect inject timing (larva 생산 극대화)
- Queen-to-Hatchery 자동 매칭
- Inject 실패 시 자동 재시도
- 성능 통계 추적
"""

from typing import Dict, Set, Optional, Tuple
from collections import defaultdict
from enum import Enum
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.unit import Unit
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        QUEEN = "QUEEN"
        HATCHERY = "HATCHERY"
        LAIR = "LAIR"
        HIVE = "HIVE"
    class AbilityId:
        EFFECT_INJECTLARVA = "EFFECT_INJECTLARVA"
    Unit = None


class QueenRole(Enum):
    """
    ★ Phase 18: Queen Role Assignment System ★

    여왕 역할 분류:
    - INJECT: 인젝트 전용 (에너지를 인젝트에만 사용)
    - DEFENSE: 방어 전용 (트랜스퓨즈, 대공 방어)
    - CREEP: 점막 전용 (점막 종양 생성)
    - FLEXIBLE: 유연 (상황에 따라 모든 역할 수행)
    """
    INJECT = "inject"
    DEFENSE = "defense"
    CREEP = "creep"
    FLEXIBLE = "flexible"


class QueenInjectOptimizer:
    """
    Queen Inject 최적화 시스템
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("InjectOptimizer")

        # ★ Inject Tracking ★
        self.inject_cooldowns: Dict[int, float] = {}  # {hatchery_tag: last_inject_time}
        self.INJECT_COOLDOWN = 29.0  # 29초 쿨다운
        self.INJECT_ENERGY_COST = 25  # 에너지 비용

        # ★ Queen Assignment ★
        self.queen_assignments: Dict[int, int] = {}  # {queen_tag: hatchery_tag}
        self.hatchery_queens: Dict[int, Set[int]] = defaultdict(set)  # {hatchery_tag: {queen_tags}}

        # ★ Priority System ★
        self.hatchery_priorities: Dict[int, int] = {}  # {hatchery_tag: priority}

        # ★ Statistics ★
        self.total_injects = 0
        self.missed_injects = 0
        self.inject_efficiency = 1.0  # 0.0 ~ 1.0

        # ★ Energy Priority System ★
        self.CREEP_ALLOWED_ENERGY = 50  # Inject + Creep 둘 다 가능한 최소 에너지
        self.queens_reserved_for_inject: Set[int] = set()  # Inject 대기 중인 Queen tags

        # ★★★ Phase 18: Queen Role System ★★★
        self.queen_roles: Dict[int, QueenRole] = {}  # {queen_tag: role}
        self.inject_queens_per_base = 1  # 기지당 인젝트 전용 여왕 수
        self.defense_queens_total = 2  # 방어 전용 여왕 수
        self.creep_queens_total = 2  # 점막 전용 여왕 수

        # ★★★ Phase 18: Inject Miss Detection ★★★
        self.expected_inject_times: Dict[int, float] = {}  # {hatchery_tag: next_expected_inject_time}
        self.inject_miss_threshold = 3.0  # 예상 시간에서 3초 이상 차이나면 미스로 간주
        self.inject_retry_attempts: Dict[int, int] = defaultdict(int)  # {hatchery_tag: retry_count}
        self.max_retry_attempts = 3  # 최대 재시도 횟수

        # ★★★ Phase 18: Performance Metrics ★★★
        self.last_efficiency_report = 0
        self.efficiency_report_interval = 60.0  # 1분마다 리포트

    async def on_step(self, iteration: int):
        """★ Phase 18: 매 프레임 실행 (향상된 인젝트 시스템) ★"""
        try:
            game_time = self.bot.time

            # 0. ★ Phase 18: Update queen role assignments ★
            if iteration % 220 == 0:  # ~10초마다
                self._assign_queen_roles()

            # 1. Update queen assignments
            if iteration % 110 == 0:  # ~5초마다
                self._update_queen_assignments()

            # 2. Update hatchery priorities
            if iteration % 220 == 0:  # ~10초마다
                self._update_hatchery_priorities()

            # 3. ★ Phase 18: Detect inject misses ★
            if iteration % 44 == 0:  # ~2초마다
                self._detect_inject_misses(game_time)

            # 4. Execute injects
            if iteration % 11 == 0:  # ~0.5초마다 (빠른 반응)
                await self._execute_injects()

            # 5. Monitor inject efficiency
            if iteration % 660 == 0:  # ~30초마다
                self._calculate_inject_efficiency()

            # 6. ★ Phase 18: Enhanced efficiency report ★
            if game_time - self.last_efficiency_report >= self.efficiency_report_interval:
                self._print_enhanced_report(game_time)
                self.last_efficiency_report = game_time

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[INJECT_OPT] Error: {e}")

    # ========================================
    # Queen Assignment
    # ========================================

    def _update_queen_assignments(self):
        """
        Queen을 Hatchery에 자동 할당

        - 각 Hatchery마다 전담 Queen 배정
        - 거리 기반 최적 매칭
        """
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "townhalls"):
            return

        queens = self.bot.units(UnitTypeId.QUEEN)
        hatcheries = self.bot.townhalls.ready

        if not queens or not hatcheries:
            return

        # ★ 현재 할당 초기화 ★
        self.hatchery_queens.clear()

        # ★ Queen 할당 ★
        for queen in queens:
            # 이미 할당되어 있는지 확인
            if queen.tag in self.queen_assignments:
                assigned_hatchery_tag = self.queen_assignments[queen.tag]

                # Hatchery가 아직 존재하는지 확인
                hatchery_exists = any(h.tag == assigned_hatchery_tag for h in hatcheries)

                if hatchery_exists:
                    self.hatchery_queens[assigned_hatchery_tag].add(queen.tag)
                    continue

            # ★ 새로운 할당: 가장 가까운 Hatchery ★
            closest_hatchery = min(
                hatcheries,
                key=lambda h: h.position.distance_to(queen.position)
            )

            self.queen_assignments[queen.tag] = closest_hatchery.tag
            self.hatchery_queens[closest_hatchery.tag].add(queen.tag)

    # ========================================
    # Hatchery Priority
    # ========================================

    def _update_hatchery_priorities(self):
        """
        Hatchery 우선순위 업데이트

        1순위: 메인 (본진에서 가까움)
        2순위: 자연 확장
        3순위: 이후 확장들
        """
        if not hasattr(self.bot, "townhalls"):
            return

        hatcheries = self.bot.townhalls.ready

        # ★ 본진으로부터 거리 기반 우선순위 ★
        main_base = self.bot.start_location

        hatchery_distances = [
            (h.tag, h.position.distance_to(main_base))
            for h in hatcheries
        ]

        # 거리 순으로 정렬 (가까운 것부터)
        hatchery_distances.sort(key=lambda x: x[1])

        # ★ 우선순위 할당 (낮은 숫자 = 높은 우선순위) ★
        # 가장 가까운 기지 (메인) = 0 (최고 우선순위)
        # 정렬 시 ascending order로 하므로 0이 먼저 처리됨
        for priority, (hatchery_tag, _) in enumerate(hatchery_distances):
            self.hatchery_priorities[hatchery_tag] = priority

    # ========================================
    # Inject Execution
    # ========================================

    async def _execute_injects(self):
        """
        Inject 실행

        - 쿨다운 체크
        - 에너지 체크
        - 우선순위 순서로 Inject
        """
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "townhalls"):
            return

        game_time = self.bot.time
        queens = self.bot.units(UnitTypeId.QUEEN)
        hatcheries = self.bot.townhalls.ready

        if not queens or not hatcheries:
            return

        # ★ 우선순위 순으로 정렬 ★
        sorted_hatcheries = sorted(
            hatcheries,
            key=lambda h: self.hatchery_priorities.get(h.tag, 999)
        )

        for hatchery in sorted_hatcheries:
            # ★ Inject 쿨다운 체크 ★
            if not self._can_inject(hatchery, game_time):
                continue

            # ★ 이 Hatchery에 할당된 Queen 찾기 ★
            assigned_queen_tags = self.hatchery_queens.get(hatchery.tag, set())

            if not assigned_queen_tags:
                # 할당된 Queen이 없으면 가장 가까운 Queen 사용
                idle_queens = queens.idle
                if idle_queens:
                    queen = min(idle_queens, key=lambda q: q.position.distance_to(hatchery.position))
                else:
                    continue
            else:
                # 할당된 Queen 중 사용 가능한 Queen 찾기
                available_queen = None

                for queen_tag in assigned_queen_tags:
                    queen = self.bot.units.find_by_tag(queen_tag)

                    if queen and queen.energy >= self.INJECT_ENERGY_COST:
                        available_queen = queen
                        break

                if not available_queen:
                    continue

                queen = available_queen

            # ★ Phase 18: 역할 체크 - Inject 역할만 인젝트 수행 ★
            if not self.can_queen_do_inject(queen.tag):
                continue

            # ★ Inject 실행 ★
            if queen.energy >= self.INJECT_ENERGY_COST:
                # Hatchery가 이미 Inject를 받고 있는지 확인
                if self._is_hatchery_already_injected(hatchery):
                    continue

                # Inject!
                self.bot.do(queen(AbilityId.EFFECT_INJECTLARVA, hatchery))

                # 쿨다운 및 예상 시간 기록
                self.inject_cooldowns[hatchery.tag] = game_time
                self.expected_inject_times[hatchery.tag] = game_time + self.INJECT_COOLDOWN  # ★ Phase 18

                # 재시도 카운터 초기화
                self.inject_retry_attempts[hatchery.tag] = 0  # ★ Phase 18

                self.total_injects += 1

                if self.total_injects % 10 == 0:
                    role = self.get_queen_role(queen.tag)
                    self.logger.info(
                        f"[{int(game_time)}s] ★ INJECT #{self.total_injects} → Hatchery (Priority {self.hatchery_priorities.get(hatchery.tag, 0)}, Queen Role: {role.value}) ★"
                    )

    def _can_inject(self, hatchery: Unit, game_time: float) -> bool:
        """
        Hatchery에 Inject 가능한지 확인

        Args:
            hatchery: 체크할 Hatchery
            game_time: 현재 게임 시간

        Returns:
            Inject 가능 여부
        """
        hatchery_tag = hatchery.tag

        # ★ 쿨다운 체크 ★
        if hatchery_tag in self.inject_cooldowns:
            last_inject = self.inject_cooldowns[hatchery_tag]
            time_since_inject = game_time - last_inject

            if time_since_inject < self.INJECT_COOLDOWN:
                return False

        return True

    def _is_hatchery_already_injected(self, hatchery: Unit) -> bool:
        """
        Hatchery가 이미 Inject 버프를 받고 있는지 확인

        Args:
            hatchery: 체크할 Hatchery

        Returns:
            Inject 버프 여부
        """
        # SC2 API를 통해 버프 확인
        if hasattr(hatchery, "buffs"):
            # Inject larva buff ID (정확한 ID는 SC2 API 문서 참조)
            for buff in hatchery.buffs:
                buff_name = str(buff).upper()
                if "INJECT" in buff_name or "LARVA" in buff_name:
                    return True

        return False

    # ========================================
    # Statistics
    # ========================================

    def _calculate_inject_efficiency(self):
        """
        Inject 효율성 계산

        - 이론적 최대 Inject 수 vs 실제 Inject 수
        """
        if not hasattr(self.bot, "townhalls"):
            return

        game_time = self.bot.time
        hatcheries = self.bot.townhalls.ready

        if game_time < 60 or not hatcheries:
            return

        # ★ 이론적 최대 Inject 수 ★
        # (게임 시간 / 29초) * Hatchery 수
        avg_hatcheries = hatcheries.amount  # 단순화
        theoretical_max = (game_time / self.INJECT_COOLDOWN) * avg_hatcheries

        # ★ 효율성 계산 ★
        if theoretical_max > 0:
            self.inject_efficiency = min(1.0, self.total_injects / theoretical_max)

            self.logger.info(
                f"[{int(game_time)}s] ★ INJECT EFFICIENCY: {self.inject_efficiency*100:.1f}% "
                f"({self.total_injects}/{int(theoretical_max)} injects) ★"
            )

    def can_use_queen_for_creep(self, queen: Unit) -> bool:
        """
        Queen을 Creep Tumor에 사용할 수 있는지 확인

        우선순위:
        1. Inject가 최우선 (25 에너지 필요)
        2. Queen이 50+ 에너지를 가지고 있을 때만 Creep도 허용

        Args:
            queen: 확인할 Queen

        Returns:
            Creep에 사용 가능 여부
        """
        if not queen:
            return False

        # ★ 에너지 체크: 50 이상이어야 Inject + Creep 둘 다 가능 ★
        if queen.energy < self.CREEP_ALLOWED_ENERGY:
            return False  # Inject 에너지를 보존

        # ★ Inject 대기 중인 Queen은 Creep 사용 불가 ★
        if queen.tag in self.queens_reserved_for_inject:
            return False

        # ★ 할당된 Hatchery에 Inject가 필요한지 확인 ★
        if queen.tag in self.queen_assignments:
            hatchery_tag = self.queen_assignments[queen.tag]
            hatchery = self.bot.units.find_by_tag(hatchery_tag)

            if hatchery:
                game_time = self.bot.time
                # Inject 쿨다운이 거의 끝나가면 (5초 이내) Creep 사용 불가
                if hatchery_tag in self.inject_cooldowns:
                    time_since_inject = game_time - self.inject_cooldowns[hatchery_tag]
                    if time_since_inject >= (self.INJECT_COOLDOWN - 5.0):
                        return False  # Inject 준비 중

        return True  # Creep 사용 가능

    def get_inject_stats(self) -> Dict:
        """Inject 통계 반환"""
        return {
            "total_injects": self.total_injects,
            "missed_injects": self.missed_injects,
            "inject_efficiency": self.inject_efficiency,
            "queens_assigned": len(self.queen_assignments),
            "hatcheries_covered": len(self.hatchery_queens),
        }

    # ========================================
    # ★★★ Phase 18: Queen Role System ★★★
    # ========================================

    def _assign_queen_roles(self):
        """
        ★ Phase 18: 여왕 역할 자동 분담 ★

        역할 분배:
        1. Inject 전용: 기지당 1마리 (최우선)
        2. Defense 전용: 2마리 (기지 근처 배치)
        3. Creep 전용: 2마리 (전선 방향 배치)
        4. Flexible: 나머지 (상황에 따라 모든 역할)
        """
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "townhalls"):
            return

        queens = self.bot.units(UnitTypeId.QUEEN)
        hatcheries = self.bot.townhalls.ready

        if not queens or not hatcheries:
            return

        # ★ 1. Inject 전용 여왕 배정 (기지당 1마리) ★
        inject_queens_needed = len(hatcheries) * self.inject_queens_per_base
        assigned_inject = 0

        for queen in queens:
            if assigned_inject >= inject_queens_needed:
                break

            # 아직 역할이 없거나 Flexible인 경우
            if queen.tag not in self.queen_roles or self.queen_roles[queen.tag] == QueenRole.FLEXIBLE:
                self.queen_roles[queen.tag] = QueenRole.INJECT
                assigned_inject += 1

        # ★ 2. Defense 전용 여왕 배정 ★
        defense_assigned = 0
        for queen in queens:
            if defense_assigned >= self.defense_queens_total:
                break

            if queen.tag not in self.queen_roles or self.queen_roles[queen.tag] == QueenRole.FLEXIBLE:
                self.queen_roles[queen.tag] = QueenRole.DEFENSE
                defense_assigned += 1

        # ★ 3. Creep 전용 여왕 배정 ★
        creep_assigned = 0
        for queen in queens:
            if creep_assigned >= self.creep_queens_total:
                break

            if queen.tag not in self.queen_roles or self.queen_roles[queen.tag] == QueenRole.FLEXIBLE:
                self.queen_roles[queen.tag] = QueenRole.CREEP
                creep_assigned += 1

        # ★ 4. 나머지는 Flexible ★
        for queen in queens:
            if queen.tag not in self.queen_roles:
                self.queen_roles[queen.tag] = QueenRole.FLEXIBLE

    def get_queen_role(self, queen_tag: int) -> QueenRole:
        """
        여왕의 역할 반환

        Args:
            queen_tag: 여왕 태그

        Returns:
            여왕 역할
        """
        return self.queen_roles.get(queen_tag, QueenRole.FLEXIBLE)

    def can_queen_do_inject(self, queen_tag: int) -> bool:
        """
        ★ Phase 18: 여왕이 인젝트를 할 수 있는지 확인 (역할 기반) ★

        Args:
            queen_tag: 여왕 태그

        Returns:
            인젝트 가능 여부
        """
        role = self.get_queen_role(queen_tag)
        return role in {QueenRole.INJECT, QueenRole.FLEXIBLE}

    # ========================================
    # ★★★ Phase 18: Inject Miss Detection ★★★
    # ========================================

    def _detect_inject_misses(self, game_time: float):
        """
        ★ Phase 18: 인젝트 미스 감지 및 보정 ★

        예상 인젝트 시간과 실제 인젝트 시간을 비교하여 미스를 감지합니다.
        미스가 감지되면 즉시 재시도합니다.
        """
        if not hasattr(self.bot, "townhalls"):
            return

        hatcheries = self.bot.townhalls.ready

        for hatchery in hatcheries:
            hatchery_tag = hatchery.tag

            # ★ 예상 인젝트 시간 체크 ★
            if hatchery_tag in self.expected_inject_times:
                expected_time = self.expected_inject_times[hatchery_tag]
                actual_time = self.inject_cooldowns.get(hatchery_tag, 0)

                # 예상 시간이 지났는데 인젝트가 안 됐으면 미스
                if game_time >= expected_time + self.inject_miss_threshold:
                    # 실제로 인젝트가 안 됐는지 확인
                    if not self._is_hatchery_already_injected(hatchery):
                        # ★ INJECT MISS 감지! ★
                        retry_count = self.inject_retry_attempts[hatchery_tag]

                        if retry_count < self.max_retry_attempts:
                            self.missed_injects += 1
                            self.inject_retry_attempts[hatchery_tag] += 1

                            self.logger.warning(
                                f"[{int(game_time)}s] ★ INJECT MISS DETECTED! ★ "
                                f"Hatchery {hatchery_tag} (Attempt {retry_count + 1}/{self.max_retry_attempts})"
                            )

                            # ★ 즉시 재시도 ★
                            # 쿨다운 초기화하여 _execute_injects에서 다시 시도하도록
                            if hatchery_tag in self.inject_cooldowns:
                                del self.inject_cooldowns[hatchery_tag]

                            # 예상 시간 업데이트
                            self.expected_inject_times[hatchery_tag] = game_time + self.INJECT_COOLDOWN
                        else:
                            # 최대 재시도 횟수 초과 - 포기하고 다음 사이클로
                            self.logger.error(
                                f"[{int(game_time)}s] ★ INJECT MISS - MAX RETRIES EXCEEDED ★ "
                                f"Hatchery {hatchery_tag}"
                            )
                            self.inject_retry_attempts[hatchery_tag] = 0
                            self.expected_inject_times[hatchery_tag] = game_time + self.INJECT_COOLDOWN

            # ★ 예상 시간이 없으면 생성 (첫 인젝트 또는 신규 기지) ★
            else:
                if hatchery_tag in self.inject_cooldowns:
                    last_inject = self.inject_cooldowns[hatchery_tag]
                    self.expected_inject_times[hatchery_tag] = last_inject + self.INJECT_COOLDOWN
                else:
                    # 첫 인젝트 예상 시간 (게임 시작 후 충분한 에너지 모을 때까지 대기)
                    self.expected_inject_times[hatchery_tag] = game_time + 10.0  # 10초 여유

    # ========================================
    # ★★★ Phase 18: Enhanced Reporting ★★★
    # ========================================

    def _print_enhanced_report(self, game_time: float):
        """
        ★ Phase 18: 향상된 인젝트 시스템 리포트 ★

        - 인젝트 효율성
        - 역할별 여왕 수
        - 미스 감지 통계
        """
        if not hasattr(self.bot, "units"):
            return

        queens = self.bot.units(UnitTypeId.QUEEN)

        # 역할별 카운트
        role_counts = {
            QueenRole.INJECT: 0,
            QueenRole.DEFENSE: 0,
            QueenRole.CREEP: 0,
            QueenRole.FLEXIBLE: 0
        }

        for queen in queens:
            role = self.get_queen_role(queen.tag)
            role_counts[role] += 1

        # 평균 여왕 에너지
        avg_energy = sum(q.energy for q in queens) / len(queens) if queens else 0

        self.logger.info(
            f"[{int(game_time)}s] ========== INJECT OPTIMIZER REPORT =========="
        )
        self.logger.info(
            f"Efficiency: {self.inject_efficiency*100:.1f}% "
            f"({self.total_injects} injects, {self.missed_injects} misses)"
        )
        self.logger.info(
            f"Queen Roles: Inject={role_counts[QueenRole.INJECT]}, "
            f"Defense={role_counts[QueenRole.DEFENSE]}, "
            f"Creep={role_counts[QueenRole.CREEP]}, "
            f"Flexible={role_counts[QueenRole.FLEXIBLE]}"
        )
        self.logger.info(
            f"Avg Energy: {avg_energy:.1f} | "
            f"Hatcheries: {len(self.hatchery_queens)} covered"
        )
        self.logger.info("=" * 60)
