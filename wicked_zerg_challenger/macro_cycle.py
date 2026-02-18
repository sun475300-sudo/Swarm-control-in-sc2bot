# -*- coding: utf-8 -*-
"""
Macro Cycle Manager - 매크로 사이클 매니저 (#108)

저그 매크로 사이클(인젝트 -> 크립 -> 유닛생산 -> 업그레이드)을 자동화합니다.

주요 기능:
1. 퀸 인젝트 라바 자동화 (각 기지별 퀸 매칭)
2. 크립 종양 확산 관리
3. 유닛 생산 큐 관리 (라바 효율 최적화)
4. 업그레이드 큐 관리
5. 라바 사용 우선순위 (드론 > 군대 > 오버로드)
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    UnitTypeId = None
    AbilityId = None
    Point2 = None


class MacroPriority(Enum):
    """매크로 우선순위"""
    INJECT = 1          # 인젝트 라바 (최우선)
    SUPPLY = 2          # 서플라이 관리
    WORKER = 3          # 일꾼 생산
    ARMY = 4            # 군대 생산
    CREEP = 5           # 크립 확산
    UPGRADE = 6         # 업그레이드
    TECH = 7            # 테크 건물


class QueenAssignment:
    """퀸-기지 배정 정보"""

    def __init__(self, queen_tag: int, hatchery_tag: int):
        """
        Args:
            queen_tag: 퀸 유닛 태그
            hatchery_tag: 해처리 유닛 태그
        """
        self.queen_tag = queen_tag
        self.hatchery_tag = hatchery_tag
        self.last_inject_time: float = 0.0
        self.inject_count: int = 0

    @property
    def inject_cooldown_ready(self) -> bool:
        """인젝트 쿨다운 확인 (25초)"""
        # 외부에서 게임 시간과 비교하여 사용
        return True


class MacroCycleManager:
    """
    매크로 사이클 관리자

    저그의 핵심 매크로 루틴을 자동화합니다:
    1. 인젝트 라바: 모든 기지에 퀸 배정, 자동 인젝트
    2. 크립 확산: 유휴 퀸으로 크립 종양 배치
    3. 유닛 생산: 라바 효율 극대화 (낭비 최소화)
    4. 업그레이드: 적절한 타이밍에 업그레이드 시작

    사용 예:
        macro = MacroCycleManager(bot)
        macro.update()  # 매 스텝 호출
    """

    # 인젝트 쿨다운 (초)
    INJECT_COOLDOWN = 25.0

    # 기지당 최적 드론 수
    OPTIMAL_DRONES_PER_BASE = 16

    # 최대 드론 수
    MAX_DRONES = 80

    def __init__(self, bot):
        """
        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot

        # 퀸-기지 배정
        self.queen_assignments: Dict[int, QueenAssignment] = {}
        self.unassigned_queens: Set[int] = set()

        # 크립 관리
        self.creep_queen_tags: Set[int] = set()  # 크립 전용 퀸
        self.last_creep_time: float = 0.0
        self.creep_interval: float = 5.0  # 크립 시도 간격

        # 생산 큐
        self.production_queue: List[Dict[str, Any]] = []
        self.pending_larva_usage: int = 0

        # 통계
        self.total_injects: int = 0
        self.total_creep_tumors: int = 0
        self.larva_wasted: int = 0  # 낭비된 라바 수

        # 라바 효율 추적
        self.last_larva_count: int = 0
        self.larva_efficiency: float = 1.0

        print("[MACRO_CYCLE] 매크로 사이클 매니저 초기화 완료")

    def update(self) -> None:
        """
        매 스텝 매크로 사이클 실행

        우선순위 순서:
        1. 인젝트 라바 (모든 기지)
        2. 서플라이 체크 (블록 방지)
        3. 일꾼 생산
        4. 군대 생산
        5. 크립 확산
        6. 업그레이드
        """
        game_time = getattr(self.bot, "time", 0.0)

        # 퀸 배정 업데이트
        self._update_queen_assignments()

        # 1. 인젝트 라바
        self._execute_injects(game_time)

        # 2. 서플라이 체크
        self._check_supply(game_time)

        # 3. 라바 효율 계산
        self._update_larva_efficiency()

        # 4. 크립 확산
        self._execute_creep_spread(game_time)

    def _update_queen_assignments(self) -> None:
        """퀸-기지 배정 업데이트"""
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "townhalls"):
            return

        # 현존 기지 태그 목록
        active_hatchery_tags = set()
        if self.bot.townhalls.exists:
            for th in self.bot.townhalls:
                active_hatchery_tags.add(th.tag)

        # 현존 퀸 태그 목록
        active_queen_tags = set()
        try:
            if UnitTypeId:
                queens = self.bot.units(UnitTypeId.QUEEN)
                for q in queens:
                    active_queen_tags.add(q.tag)
        except Exception:
            pass

        # 죽은 퀸/기지 제거
        dead_assignments = []
        for queen_tag, assignment in self.queen_assignments.items():
            if queen_tag not in active_queen_tags:
                dead_assignments.append(queen_tag)
            elif assignment.hatchery_tag not in active_hatchery_tags:
                dead_assignments.append(queen_tag)

        for tag in dead_assignments:
            del self.queen_assignments[tag]

        # 배정되지 않은 퀸 찾기
        assigned_queen_tags = set(self.queen_assignments.keys())
        unassigned = active_queen_tags - assigned_queen_tags - self.creep_queen_tags

        # 배정되지 않은 기지 찾기
        assigned_hatchery_tags = {a.hatchery_tag for a in self.queen_assignments.values()}
        unassigned_hatcheries = active_hatchery_tags - assigned_hatchery_tags

        # 매칭 (가장 가까운 퀸-기지 페어링)
        for h_tag in unassigned_hatcheries:
            if not unassigned:
                break

            hatchery = None
            for th in self.bot.townhalls:
                if th.tag == h_tag:
                    hatchery = th
                    break

            if not hatchery:
                continue

            # 가장 가까운 미배정 퀸 찾기
            best_queen_tag = None
            best_dist = float("inf")

            for q_tag in unassigned:
                try:
                    if UnitTypeId:
                        queen = self.bot.units.find_by_tag(q_tag)
                        if queen:
                            dist = queen.distance_to(hatchery)
                            if dist < best_dist:
                                best_dist = dist
                                best_queen_tag = q_tag
                except Exception:
                    continue

            if best_queen_tag:
                self.queen_assignments[best_queen_tag] = QueenAssignment(
                    best_queen_tag, h_tag
                )
                unassigned.discard(best_queen_tag)

        self.unassigned_queens = unassigned

    def _execute_injects(self, game_time: float) -> None:
        """모든 배정된 퀸으로 인젝트 실행"""
        for queen_tag, assignment in self.queen_assignments.items():
            # 인젝트 쿨다운 체크
            if game_time - assignment.last_inject_time < self.INJECT_COOLDOWN:
                continue

            try:
                if not UnitTypeId or not AbilityId:
                    continue

                queen = self.bot.units.find_by_tag(queen_tag)
                hatchery = self.bot.townhalls.find_by_tag(assignment.hatchery_tag)

                if not queen or not hatchery:
                    continue

                # 퀸 에너지 체크 (25 이상)
                if queen.energy < 25:
                    continue

                # 해처리가 이미 인젝트 상태인지 체크
                if hatchery.is_idle or not hasattr(hatchery, "has_buff"):
                    queen(AbilityId.EFFECT_INJECTLARVA, hatchery)
                    assignment.last_inject_time = game_time
                    assignment.inject_count += 1
                    self.total_injects += 1

            except Exception:
                continue

    def _check_supply(self, game_time: float) -> None:
        """서플라이 블록 방지"""
        supply_left = getattr(self.bot, "supply_left", 0)
        supply_used = getattr(self.bot, "supply_used", 0)
        supply_cap = getattr(self.bot, "supply_cap", 0)

        # 서플라이 여유분이 적으면 오버로드 생산
        if supply_cap < 200:
            # 서플라이 여유분 임계값 (서플라이 사용량에 따라 동적)
            threshold = max(2, min(8, supply_used // 20))

            if supply_left <= threshold:
                # 오버로드가 이미 생산 중인지 확인
                already_pending = 0
                try:
                    if UnitTypeId:
                        already_pending = self.bot.already_pending(UnitTypeId.OVERLORD)
                except Exception:
                    pass

                # 필요한 오버로드 수 계산
                needed = max(0, 2 - already_pending)
                if needed > 0:
                    self.production_queue.insert(0, {
                        "unit": "overlord",
                        "count": needed,
                        "priority": MacroPriority.SUPPLY.value,
                    })

    def _update_larva_efficiency(self) -> None:
        """라바 사용 효율 추적"""
        try:
            if not UnitTypeId or not hasattr(self.bot, "units"):
                return

            current_larva = self.bot.units(UnitTypeId.LARVA).amount
            base_count = self.bot.townhalls.amount if hasattr(self.bot, "townhalls") else 1

            # 기지당 최적 라바 수: 3 (인젝트 1회당 3라바)
            optimal_larva = base_count * 3
            max_larva = base_count * 19  # 기지당 최대 19라바

            if current_larva > optimal_larva * 2:
                # 라바가 너무 많이 쌓이면 효율 감소
                self.larva_wasted += current_larva - optimal_larva
                self.larva_efficiency = optimal_larva / max(current_larva, 1)
            else:
                self.larva_efficiency = min(1.0, current_larva / max(optimal_larva, 1))

            self.last_larva_count = current_larva

        except Exception:
            pass

    def _execute_creep_spread(self, game_time: float) -> None:
        """크립 확산 실행 (유휴 퀸 사용)"""
        if game_time - self.last_creep_time < self.creep_interval:
            return

        self.last_creep_time = game_time

        # 크립 전용 퀸이 있으면 우선 사용
        for queen_tag in self.creep_queen_tags:
            try:
                if not UnitTypeId or not AbilityId:
                    break

                queen = self.bot.units.find_by_tag(queen_tag)
                if not queen or queen.energy < 25:
                    continue

                # 크립 종양 배치
                self._place_creep_tumor(queen)

            except Exception:
                continue

        # 인젝트 배정된 퀸 중 에너지가 충분한 퀸으로도 크립 확산
        for queen_tag, assignment in self.queen_assignments.items():
            try:
                if not UnitTypeId or not AbilityId:
                    break

                queen = self.bot.units.find_by_tag(queen_tag)
                if not queen:
                    continue

                # 인젝트에 필요한 25 에너지 + 크립에 필요한 25 에너지 = 50 이상
                if queen.energy >= 50:
                    self._place_creep_tumor(queen)

            except Exception:
                continue

    def _place_creep_tumor(self, queen) -> bool:
        """크립 종양 배치"""
        try:
            if not AbilityId or not Point2:
                return False

            # 퀸 위치 주변에 크립이 없는 곳 찾기
            pos = queen.position
            target = pos.towards(self.bot.game_info.map_center, 8)

            # 크립 위에만 배치 가능
            if hasattr(self.bot, "has_creep"):
                if self.bot.has_creep(target):
                    queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, target)
                    self.total_creep_tumors += 1
                    return True

        except Exception:
            pass
        return False

    def get_optimal_drone_target(self) -> int:
        """최적 드론 목표 수 계산"""
        base_count = 0
        if hasattr(self.bot, "townhalls"):
            base_count = self.bot.townhalls.amount

        # 기지당 16드론 + 가스 6
        mineral_workers = base_count * self.OPTIMAL_DRONES_PER_BASE
        gas_workers = min(base_count * 2, 6) * 3  # 가스 기지당 3드론

        target = min(mineral_workers + gas_workers, self.MAX_DRONES)
        return target

    def get_larva_priority_list(self) -> List[Dict[str, Any]]:
        """
        라바 사용 우선순위 리스트 반환

        Returns:
            우선순위 순서대로 생산 지시 리스트
        """
        priorities = []

        # 1. 서플라이 위기 -> 오버로드
        supply_left = getattr(self.bot, "supply_left", 0)
        if supply_left <= 2:
            priorities.append({
                "unit": "overlord",
                "reason": "서플라이 블록 방지",
                "priority": 1,
            })

        # 2. 드론 부족
        drone_count = 0
        try:
            if UnitTypeId and hasattr(self.bot, "units"):
                drone_count = self.bot.units(UnitTypeId.DRONE).amount
        except Exception:
            pass

        target_drones = self.get_optimal_drone_target()
        if drone_count < target_drones:
            priorities.append({
                "unit": "drone",
                "reason": f"드론 부족 ({drone_count}/{target_drones})",
                "priority": 2,
            })

        # 3. 군대 생산
        priorities.append({
            "unit": "army",
            "reason": "군대 확충",
            "priority": 3,
        })

        return priorities

    def designate_creep_queen(self, queen_tag: int) -> None:
        """퀸을 크립 전용으로 지정"""
        self.creep_queen_tags.add(queen_tag)
        # 인젝트 배정에서 제거
        if queen_tag in self.queen_assignments:
            del self.queen_assignments[queen_tag]

    def get_stats(self) -> Dict[str, Any]:
        """매크로 사이클 통계"""
        return {
            "queen_assignments": len(self.queen_assignments),
            "unassigned_queens": len(self.unassigned_queens),
            "creep_queens": len(self.creep_queen_tags),
            "total_injects": self.total_injects,
            "total_creep_tumors": self.total_creep_tumors,
            "larva_efficiency": round(self.larva_efficiency, 2),
            "larva_wasted": self.larva_wasted,
            "production_queue_size": len(self.production_queue),
        }
