# -*- coding: utf-8 -*-
"""
Queen Specialization Manager - 여왕 전문 분담 체제

여왕을 3가지 역할로 엄격 분리:
- PUMP: 인젝트 전담. 에너지 25 이상이면 무조건 인젝트만 수행. 절대 다른 행동 금지.
- CREEP: 점막 확장 전담. A* 고속도로 웨이포인트를 따라 적진 방향으로 점막 확장.
- COMBAT: 본대 호위. 전투 시 수혈(Transfusion) 제공.

배정 규칙:
1. 기지당 PUMP 1마리 (라바 펌핑 보장)
2. 2기지당 CREEP 1마리 (최소 1, 기지 2개 이상일 때)
3. 나머지 전부 COMBAT
"""

from enum import Enum
from typing import Dict, List, Optional, Set

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    class AbilityId:
        EFFECT_INJECTLARVA = "EFFECT_INJECTLARVA"
        BUILD_CREEPTUMOR_QUEEN = "BUILD_CREEPTUMOR_QUEEN"
        TRANSFUSION_TRANSFUSION = "TRANSFUSION_TRANSFUSION"
    class UnitTypeId:
        QUEEN = "QUEEN"
        HATCHERY = "HATCHERY"
        LAIR = "LAIR"
        HIVE = "HIVE"
    Point2 = tuple


class QueenSpecialization(Enum):
    """여왕 전문 역할 - 한번 배정되면 절대 벗어나지 않음"""
    PUMP = "pump"       # 인젝트 전담 (에너지 25 예약)
    CREEP = "creep"     # 점막 확장 전담 (A* 고속도로)
    COMBAT = "combat"   # 본대 호위 + 수혈


class QueenSpecializationManager:
    """
    여왕 전문 분담 관리자

    PUMP 퀸은 절대 인젝트 외에 다른 행동을 하지 않습니다.
    CREEP 퀸은 A* 고속도로 웨이포인트를 따라 점막을 확장합니다.
    COMBAT 퀸은 본대와 함께 이동하며 수혈을 제공합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.specializations: Dict[int, QueenSpecialization] = {}  # queen_tag -> spec
        self.pump_assignments: Dict[int, int] = {}  # queen_tag -> hatchery_tag
        self.last_inject_time: Dict[int, float] = {}  # hatchery_tag -> time
        self.last_creep_time: Dict[int, float] = {}  # queen_tag -> time
        self.last_transfuse_time: Dict[int, float] = {}  # queen_tag -> time

        # Config
        self.inject_cooldown = 29.0
        self.creep_cooldown = 4.0
        self.transfuse_cooldown = 1.0
        self.pump_energy_reserve = 25
        self.creep_energy_threshold = 25
        self.transfuse_energy = 50
        self.transfuse_hp_threshold = 0.5

    def assign_roles(self, queens, hatcheries) -> None:
        """
        여왕 역할 배정 (매 프레임 호출)

        우선순위:
        1. PUMP: 기지당 1마리 (라바 인젝트 전담)
        2. CREEP: 2기지당 1마리 (점막 확장 전담)
        3. COMBAT: 나머지 전부 (본대 호위)
        """
        current_tags = {q.tag for q in queens}

        # 죽은 퀸 정리
        self.specializations = {
            t: s for t, s in self.specializations.items() if t in current_tags
        }
        self.pump_assignments = {
            qt: ht for qt, ht in self.pump_assignments.items() if qt in current_tags
        }

        assigned: Set[int] = set()

        # === Phase 1: PUMP 퀸 (기지당 1마리) ===
        hatch_tags = {h.tag for h in hatcheries}

        # 기존 PUMP 배정 유지
        for qt, ht in list(self.pump_assignments.items()):
            if ht not in hatch_tags:
                del self.pump_assignments[qt]
                continue
            queen = self._find_by_tag(queens, qt)
            hatch = self._find_by_tag(hatcheries, ht)
            if queen and hatch:
                # 너무 멀면 재배정
                try:
                    if queen.distance_to(hatch) > 12:
                        del self.pump_assignments[qt]
                        continue
                except Exception:
                    pass
                self.specializations[qt] = QueenSpecialization.PUMP
                assigned.add(qt)

        # 미배정 해처리에 PUMP 퀸 배정
        assigned_hatches = set(self.pump_assignments.values())
        for hatch in hatcheries:
            if hatch.tag in assigned_hatches:
                continue
            unassigned = [q for q in queens if q.tag not in assigned]
            if not unassigned:
                break
            closest = min(unassigned, key=lambda q: q.distance_to(hatch))
            self.specializations[closest.tag] = QueenSpecialization.PUMP
            self.pump_assignments[closest.tag] = hatch.tag
            assigned.add(closest.tag)

        # === Phase 2: CREEP 퀸 (2기지당 1마리, 최소 1) ===
        creep_count = max(1, len(hatcheries) // 2) if len(hatcheries) >= 2 else 0
        unassigned = [q for q in queens if q.tag not in assigned]

        # 기존 CREEP 퀸 유지
        existing_creep = [
            qt for qt, spec in self.specializations.items()
            if spec == QueenSpecialization.CREEP and qt in current_tags and qt not in assigned
        ]
        for qt in existing_creep[:creep_count]:
            assigned.add(qt)
            creep_count -= 1

        # 추가 CREEP 배정
        for queen in unassigned[:creep_count]:
            if queen.tag in assigned:
                continue
            self.specializations[queen.tag] = QueenSpecialization.CREEP
            assigned.add(queen.tag)

        # === Phase 3: COMBAT 퀸 (나머지 전부) ===
        for queen in queens:
            if queen.tag not in assigned:
                self.specializations[queen.tag] = QueenSpecialization.COMBAT
                assigned.add(queen.tag)

    async def execute_pump_queen(self, queen, hatcheries) -> None:
        """
        PUMP 퀸: 인젝트 전담. 에너지 25 이상이면 무조건 인젝트.
        절대 다른 행동(점막, 수혈 등)을 하지 않음.
        """
        if queen.energy < self.pump_energy_reserve:
            return

        hatch_tag = self.pump_assignments.get(queen.tag)
        if not hatch_tag:
            return

        hatch = self._find_by_tag(hatcheries, hatch_tag)
        if not hatch:
            return

        current_time = getattr(self.bot, "time", 0.0)

        # 인젝트 쿨다운 체크
        last_inject = self.last_inject_time.get(hatch_tag, 0.0)
        if current_time - last_inject < self.inject_cooldown:
            return

        # 해처리까지 이동
        try:
            dist = queen.distance_to(hatch)
        except Exception:
            return

        if dist > 4.0:
            if dist <= 10.0:
                self.bot.do(queen.move(hatch.position))
            return

        # 인젝트 실행
        try:
            self.bot.do(queen(AbilityId.EFFECT_INJECTLARVA, hatch))
            self.last_inject_time[hatch_tag] = current_time
        except Exception:
            pass

    async def execute_creep_queen(self, queen, highway_waypoints: List) -> None:
        """
        CREEP 퀸: A* 고속도로 경로를 따라 점막 확장 전담.
        점막 위에서만 종양 설치, 아니면 이동.
        """
        if queen.energy < self.creep_energy_threshold:
            # 에너지 부족하면 가장 가까운 해처리 근처에서 대기
            if hasattr(self.bot, "townhalls") and self.bot.townhalls:
                closest_hatch = self.bot.townhalls.closest_to(queen)
                if queen.distance_to(closest_hatch) > 8:
                    self.bot.do(queen.move(closest_hatch.position))
            return

        current_time = getattr(self.bot, "time", 0.0)
        last_creep = self.last_creep_time.get(queen.tag, 0.0)
        if current_time - last_creep < self.creep_cooldown:
            return

        # 고속도로 웨이포인트에서 다음 미완성 지점 찾기
        target = None
        if highway_waypoints:
            for wp in highway_waypoints:
                try:
                    if not self.bot.has_creep(wp):
                        target = wp
                        break
                except Exception:
                    continue

        # 고속도로 없으면 적 방향으로 확장
        if target is None:
            enemy_starts = getattr(self.bot, "enemy_start_locations", [])
            if enemy_starts:
                target = queen.position.towards(enemy_starts[0], 9.0)
            else:
                return

        # 점막 위에 있으면 종양 설치
        try:
            if self.bot.has_creep(queen.position):
                # 타겟 방향으로 9거리에 종양 설치
                tumor_pos = queen.position.towards(target, min(9.0, queen.distance_to(target)))
                self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, tumor_pos))
                self.last_creep_time[queen.tag] = current_time
            else:
                # 점막 가장자리로 이동
                if hasattr(self.bot, "townhalls") and self.bot.townhalls:
                    closest_hatch = self.bot.townhalls.closest_to(queen)
                    move_target = queen.position.towards(closest_hatch.position, 3)
                    self.bot.do(queen.move(move_target))
        except Exception:
            pass

    async def execute_combat_queen(self, queen, army_center) -> None:
        """
        COMBAT 퀸: 본대와 함께 이동하며 부상 유닛에 수혈 제공.
        """
        current_time = getattr(self.bot, "time", 0.0)

        # 수혈 가능 여부 확인
        if queen.energy >= self.transfuse_energy:
            last_trans = self.last_transfuse_time.get(queen.tag, 0.0)
            if current_time - last_trans >= self.transfuse_cooldown:
                # 주변 부상 유닛 찾기
                injured = self._find_injured_nearby(queen, range_dist=7.0)
                if injured:
                    try:
                        self.bot.do(queen(AbilityId.TRANSFUSION_TRANSFUSION, injured))
                        self.last_transfuse_time[queen.tag] = current_time
                        return
                    except Exception:
                        pass

        # 본대 따라가기
        if army_center:
            try:
                if queen.distance_to(army_center) > 8:
                    self.bot.do(queen.move(army_center))
            except Exception:
                pass

    def _find_injured_nearby(self, queen, range_dist: float = 7.0):
        """수혈 대상 - HP 비율 낮은 순으로 가치 높은 유닛 우선"""
        if not hasattr(self.bot, "units"):
            return None

        # 우선순위 가중치 (높을수록 우선)
        UNIT_VALUE = {
            "ULTRALISK": 100, "BROODLORD": 90, "QUEEN": 85,
            "RAVAGER": 70, "LURKER": 65, "ROACH": 50,
            "HYDRALISK": 45, "MUTALISK": 40, "ZERGLING": 30,
        }

        best_target = None
        best_score = 0

        for unit in self.bot.units:
            if not hasattr(unit, "health") or not hasattr(unit, "health_max"):
                continue
            if unit.health_max == 0:
                continue

            hp_ratio = unit.health / unit.health_max
            if hp_ratio >= self.transfuse_hp_threshold:
                continue

            try:
                if queen.distance_to(unit) > range_dist:
                    continue
            except Exception:
                continue

            type_name = getattr(unit.type_id, "name", "").upper()
            value = UNIT_VALUE.get(type_name, 30)
            # 점수: 가치 높고 HP 낮을수록 우선
            score = value * (1.0 - hp_ratio)

            if score > best_score:
                best_score = score
                best_target = unit

        return best_target

    def get_role(self, queen_tag: int) -> Optional[QueenSpecialization]:
        """특정 퀸의 역할 반환"""
        return self.specializations.get(queen_tag)

    def get_role_counts(self) -> Dict[str, int]:
        """역할별 퀸 수 반환"""
        counts = {"pump": 0, "creep": 0, "combat": 0}
        for spec in self.specializations.values():
            counts[spec.value] += 1
        return counts

    @staticmethod
    def _find_by_tag(units, tag: int):
        """태그로 유닛 찾기"""
        if tag is None:
            return None
        for unit in units:
            if unit.tag == tag:
                return unit
        return None