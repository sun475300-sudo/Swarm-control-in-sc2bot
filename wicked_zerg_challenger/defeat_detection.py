# -*- coding: utf-8 -*-
"""
Defeat Detection System - 패배 직감 로직

게임 중 패배가 확실해 보일 때를 미리 감지하여 조기 항복 또는 마지막 방어 시도를 판단합니다.

패배 조건:
1. 모든 해처리 파괴 + 생산 불가 상태
2. 압도적인 병력 열세 (적 병력 가치가 아군의 5배 이상)
3. 회복 불가능한 경제 상태 (미네랄 < 50, 일꾼 < 3, 해처리 없음)
4. 모든 건물 파괴됨
5. 기지 전멸 (townhalls == 0 and 건설 중인 해처리 없음)
"""

from typing import Dict, Optional, Tuple
from sc2.position import Point2


class DefeatLevel:
    """패배 가능성 수준"""
    SAFE = 0           # 안전
    DISADVANTAGE = 1   # 불리한 상황
    CRITICAL = 2       # 위기 상황
    IMMINENT = 3       # 패배 직전
    INEVITABLE = 4     # 패배 불가피


class DefeatDetection:
    """
    패배 직감 감지 시스템

    Features:
    - 실시간 전력 비교
    - 경제 상태 평가
    - 생산 능력 평가
    - 패배 직전 마지막 방어 시도
    """

    def __init__(self, bot):
        self.bot = bot

        # 패배 감지 상태
        self.defeat_level = DefeatLevel.SAFE
        self.defeat_reason = None
        self.last_check_iteration = 0
        self.check_interval = 8  # 8프레임마다 체크 (성능 고려)

        # 패배 직전 마지막 방어 플래그
        self.last_stand_active = False
        self.last_stand_position = None

        # ★★★ 임계값 설정 (패배 판정 기준 강화) ★★★
        self.military_ratio_critical = 3.0  # 적 병력이 아군의 3배 이상 (5.0 → 3.0)
        self.military_ratio_imminent = 6.0  # 적 병력이 아군의 6배 이상 (10.0 → 6.0)
        self.min_workers_for_recovery = 5   # 최소 일꾼 수 (3 → 5)
        self.min_minerals_for_recovery = 100  # 최소 미네랄 (50 → 100)

        # ★★★ 추가: 빠른 포기를 위한 새로운 조건 ★★★
        self.max_critical_duration = 60  # 위기 상태 최대 지속 시간 (초)
        self.critical_start_time = None  # 위기 상태 시작 시간

        # 통계
        self.defeat_warnings = 0
        self.critical_moments = 0

    async def on_step(self, iteration: int) -> Dict:
        """
        패배 직감 체크 (매 스텝 호출)

        Returns:
            dict: {
                "defeat_level": int (0-4),
                "defeat_reason": str or None,
                "should_surrender": bool,
                "last_stand_required": bool,
                "last_stand_position": Point2 or None
            }
        """
        # 체크 간격 조절
        if iteration - self.last_check_iteration < self.check_interval:
            return self._get_current_status()

        self.last_check_iteration = iteration

        # 패배 조건 체크
        defeat_level, reason = await self._evaluate_defeat_conditions()

        # 상태 업데이트
        self.defeat_level = defeat_level
        self.defeat_reason = reason

        # 패배 직전이면 마지막 방어 시도
        if defeat_level >= DefeatLevel.IMMINENT:
            self._activate_last_stand()
            self.critical_moments += 1
        elif defeat_level >= DefeatLevel.CRITICAL:
            self.defeat_warnings += 1
        else:
            self.last_stand_active = False
            self.last_stand_position = None

        return self._get_current_status()

    async def _evaluate_defeat_conditions(self) -> Tuple[int, Optional[str]]:
        """
        패배 조건 평가

        Returns:
            (defeat_level, reason)
        """
        # ★★★ 빠른 포기 조건 추가 ★★★

        # 1. 기지 전멸 체크
        if await self._check_base_elimination():
            return DefeatLevel.INEVITABLE, "모든 기지 파괴됨 (해처리 0)"

        # 2. 건물 전멸 체크
        if await self._check_structure_elimination():
            return DefeatLevel.INEVITABLE, "모든 건물 파괴됨"

        # ★★★ 3. 일꾼 전멸 + 회복 불가 ★★★
        if await self._check_worker_elimination():
            return DefeatLevel.INEVITABLE, "일꾼 전멸 + 회복 불가능"

        # 4. 압도적 병력 열세 체크
        military_status = await self._check_military_disadvantage()
        if military_status[0] >= DefeatLevel.IMMINENT:
            return military_status

        # 5. 경제 회복 불가 상태 체크
        economy_status = await self._check_unrecoverable_economy()
        if economy_status[0] >= DefeatLevel.CRITICAL:
            return economy_status

        # 6. 생산 능력 상실 체크
        production_status = await self._check_production_loss()
        if production_status[0] >= DefeatLevel.CRITICAL:
            return production_status

        # ★★★ 7. 위기 상태 장기 지속 체크 ★★★
        duration_status = await self._check_critical_duration()
        if duration_status[0] >= DefeatLevel.INEVITABLE:
            return duration_status

        # 8. 복합 위기 상황 체크
        combined_status = await self._check_combined_crisis()
        if combined_status[0] >= DefeatLevel.CRITICAL:
            return combined_status

        # 위기 상태 시작 시간 추적
        game_time = getattr(self.bot, "time", 0)
        if military_status[0] >= DefeatLevel.CRITICAL or economy_status[0] >= DefeatLevel.CRITICAL:
            if self.critical_start_time is None:
                self.critical_start_time = game_time
        else:
            self.critical_start_time = None  # 회복되면 리셋

        # 안전 또는 불리한 상황
        if military_status[0] == DefeatLevel.DISADVANTAGE:
            return military_status

        return DefeatLevel.SAFE, None

    async def _check_base_elimination(self) -> bool:
        """모든 기지 파괴됨 체크"""
        if not hasattr(self.bot, "townhalls"):
            return False

        townhalls = self.bot.townhalls

        # 완성된 해처리 없음
        if not townhalls.exists:
            # 건설 중인 해처리도 없으면 패배
            if hasattr(self.bot, "structures"):
                building_hatcheries = self.bot.structures.filter(
                    lambda s: s.type_id.name in ["HATCHERY", "LAIR", "HIVE"] and not s.is_ready
                )
                if not building_hatcheries.exists:
                    return True
            else:
                return True

        return False

    async def _check_structure_elimination(self) -> bool:
        """모든 건물 파괴됨 체크"""
        if not hasattr(self.bot, "structures"):
            return False

        structures = self.bot.structures

        # 건물이 하나도 없으면 패배
        if not structures.exists:
            return True

        # 스포닝 풀도 없고 일꾼도 없으면 생산 불가
        if hasattr(self.bot, "workers"):
            workers = self.bot.workers
            spawning_pools = structures.filter(lambda s: s.type_id.name == "SPAWNINGPOOL")

            if not spawning_pools.exists and not workers.exists:
                return True

        return False

    async def _check_worker_elimination(self) -> bool:
        """
        ★★★ 일꾼 전멸 + 회복 불가능 체크 ★★★

        조건:
        1. 일꾼 3마리 이하
        2. 미네랄 100 미만
        3. 해처리 없거나 라바 없음
        """
        if not hasattr(self.bot, "workers"):
            return False

        workers = self.bot.workers
        minerals = getattr(self.bot, "minerals", 0)
        townhalls = getattr(self.bot, "townhalls", [])

        # 일꾼이 충분하면 안전
        if workers.amount > 3:
            return False

        # 일꾼 3마리 이하 + 미네랄 부족
        if workers.amount <= 3 and minerals < 100:
            # 해처리가 없거나 라바가 없으면 회복 불가
            if not townhalls.exists:
                return True

            # 라바 확인
            larva = getattr(self.bot, "larva", [])
            if not larva.exists:
                return True

        return False

    async def _check_critical_duration(self) -> Tuple[int, Optional[str]]:
        """
        ★★★ 위기 상태 장기 지속 체크 ★★★

        위기 상태가 60초 이상 지속되면 패배로 간주
        """
        if self.critical_start_time is None:
            return DefeatLevel.SAFE, None

        game_time = getattr(self.bot, "time", 0)
        duration = game_time - self.critical_start_time

        if duration > self.max_critical_duration:
            return DefeatLevel.INEVITABLE, f"위기 상태 {int(duration)}초 지속 (회복 불가)"

        return DefeatLevel.SAFE, None

    async def _check_military_disadvantage(self) -> Tuple[int, Optional[str]]:
        """압도적 병력 열세 체크"""
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "enemy_units"):
            return DefeatLevel.SAFE, None

        # 아군 병력 가치 계산
        our_military_value = 0
        our_units = self.bot.units.filter(
            lambda u: u.can_attack and not u.is_structure and u.type_id.name != "OVERLORD"
        )

        for unit in our_units:
            our_military_value += self._get_unit_value(unit)

        # 적 병력 가치 계산
        enemy_military_value = 0
        enemy_units = self.bot.enemy_units.filter(
            lambda u: u.can_attack and not u.is_structure
        )

        for unit in enemy_units:
            enemy_military_value += self._get_unit_value(unit)

        # 비율 계산
        if our_military_value == 0:
            if enemy_military_value > 500:  # 적 병력이 500 이상
                return DefeatLevel.IMMINENT, f"병력 0 vs 적 병력 {enemy_military_value:.0f}"
            elif enemy_military_value > 200:
                return DefeatLevel.CRITICAL, f"병력 0 vs 적 병력 {enemy_military_value:.0f}"
            else:
                return DefeatLevel.DISADVANTAGE, "병력 없음"

        ratio = enemy_military_value / our_military_value

        if ratio >= self.military_ratio_imminent:
            return DefeatLevel.IMMINENT, f"병력 비율 1:{ratio:.1f} (적 압도적 우세)"
        elif ratio >= self.military_ratio_critical:
            return DefeatLevel.CRITICAL, f"병력 비율 1:{ratio:.1f} (매우 불리)"
        elif ratio >= 3.0:
            return DefeatLevel.DISADVANTAGE, f"병력 비율 1:{ratio:.1f} (불리)"

        return DefeatLevel.SAFE, None

    async def _check_unrecoverable_economy(self) -> Tuple[int, Optional[str]]:
        """경제 회복 불가 상태 체크"""
        if not hasattr(self.bot, "workers") or not hasattr(self.bot, "minerals"):
            return DefeatLevel.SAFE, None

        workers = self.bot.workers
        minerals = self.bot.minerals

        # 일꾼 3명 미만 + 미네랄 50 미만 + 해처리 없음
        if workers.amount < self.min_workers_for_recovery:
            if minerals < self.min_minerals_for_recovery:
                if not self.bot.townhalls.exists:
                    return DefeatLevel.IMMINENT, f"경제 붕괴 (일꾼 {workers.amount}, 미네랄 {minerals}, 해처리 0)"
                else:
                    return DefeatLevel.CRITICAL, f"경제 위기 (일꾼 {workers.amount}, 미네랄 {minerals})"

        # 일꾼 0명 (모든 일꾼 사망)
        if workers.amount == 0:
            if minerals < 50:
                return DefeatLevel.IMMINENT, "모든 일꾼 사망 + 미네랄 부족"
            else:
                return DefeatLevel.CRITICAL, "모든 일꾼 사망"

        return DefeatLevel.SAFE, None

    async def _check_production_loss(self) -> Tuple[int, Optional[str]]:
        """생산 능력 상실 체크"""
        if not hasattr(self.bot, "structures") or not hasattr(self.bot, "townhalls"):
            return DefeatLevel.SAFE, None

        structures = self.bot.structures
        townhalls = self.bot.townhalls

        # 해처리 없고 라바도 없으면 생산 불가
        if not townhalls.exists:
            total_larva = 0
            if hasattr(self.bot, "larva"):
                total_larva = self.bot.larva.amount

            if total_larva == 0:
                return DefeatLevel.CRITICAL, "생산 능력 상실 (해처리 0, 라바 0)"

        # 스포닝 풀 없고 일꾼도 못 만들면 위기
        spawning_pools = structures.filter(lambda s: s.type_id.name == "SPAWNINGPOOL")
        if not spawning_pools.exists and not townhalls.exists:
            return DefeatLevel.CRITICAL, "군대 생산 불가 (스포닝 풀 없음, 해처리 없음)"

        return DefeatLevel.SAFE, None

    async def _check_combined_crisis(self) -> Tuple[int, Optional[str]]:
        """복합 위기 상황 체크"""
        if not hasattr(self.bot, "workers") or not hasattr(self.bot, "townhalls"):
            return DefeatLevel.SAFE, None

        workers = self.bot.workers
        townhalls = self.bot.townhalls
        minerals = self.bot.minerals if hasattr(self.bot, "minerals") else 0

        # 복합 위기: 일꾼 < 5 and 해처리 1개 이하 and 미네랄 < 100
        crisis_count = 0

        if workers.amount < 5:
            crisis_count += 1

        if townhalls.amount <= 1:
            crisis_count += 1

        if minerals < 100:
            crisis_count += 1

        # 3가지 모두 해당하면 위기
        if crisis_count >= 3:
            return DefeatLevel.CRITICAL, f"복합 위기 (일꾼 {workers.amount}, 해처리 {townhalls.amount}, 미네랄 {minerals})"

        return DefeatLevel.SAFE, None

    def _get_unit_value(self, unit) -> float:
        """
        유닛 가치 계산 (미네랄 + 가스*1.5 기반)

        고위협 유닛은 가중치 추가
        """
        unit_name = unit.type_id.name.upper()

        # 기본 가치 (대략적인 비용)
        base_values = {
            # 저그
            "DRONE": 50, "ZERGLING": 25, "ROACH": 75, "HYDRALISK": 100,
            "MUTALISK": 100, "BANELING": 50, "RAVAGER": 100, "ULTRALISK": 300,
            "BROODLORD": 250, "CORRUPTOR": 150, "INFESTOR": 150,
            "QUEEN": 150, "SWARMHOST": 200, "VIPER": 200, "LURKER": 200,

            # 테란
            "MARINE": 50, "MARAUDER": 100, "SIEGETANK": 150, "THOR": 300,
            "BATTLECRUISER": 400, "MEDIVAC": 100, "LIBERATOR": 150,
            "CYCLONE": 125, "HELLION": 100, "BANSHEE": 150, "RAVEN": 100,

            # 프로토스
            "ZEALOT": 100, "STALKER": 125, "IMMORTAL": 275, "COLOSSUS": 300,
            "ARCHON": 175, "HIGHTEMPLAR": 50, "DARKTEMPLAR": 125,
            "PHOENIX": 150, "VOIDRAY": 250, "CARRIER": 350, "TEMPEST": 300,
            "DISRUPTOR": 150, "ORACLE": 150, "OBSERVER": 25,
        }

        # 고위협 유닛 가중치
        high_threat_multiplier = {
            "SIEGETANK": 2.0, "SIEGETANKSIEGED": 2.0, "COLOSSUS": 2.0,
            "IMMORTAL": 1.5, "THOR": 2.0, "BATTLECRUISER": 2.5,
            "ULTRALISK": 2.0, "BROODLORD": 2.0, "CARRIER": 2.5,
        }

        base_value = base_values.get(unit_name, 50)
        multiplier = high_threat_multiplier.get(unit_name, 1.0)

        return base_value * multiplier

    def _activate_last_stand(self):
        """마지막 방어 활성화"""
        self.last_stand_active = True

        # 마지막 방어 위치: 남은 해처리 중심 또는 스타팅 위치
        if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
            self.last_stand_position = self.bot.townhalls.first.position
        elif hasattr(self.bot, "start_location"):
            self.last_stand_position = self.bot.start_location
        else:
            self.last_stand_position = None

    def _get_current_status(self) -> Dict:
        """현재 패배 감지 상태 반환"""
        # ★★★ 패배 불가피 시 즉시 항복 (훈련 효율 향상) ★★★
        should_surrender = self.defeat_level >= DefeatLevel.INEVITABLE

        # ★★★ 추가: 위기 상황이 오래 지속되면 항복 (시간 절약) ★★★
        if self.defeat_level >= DefeatLevel.IMMINENT:
            # 패배 직전 상태가 30초 이상 지속되면 항복
            game_time = getattr(self.bot, "time", 0)
            if self.critical_moments > 5:  # ~40초 지속
                should_surrender = True
                self.defeat_reason = "장기간 패배 직전 상태 (항복)"

        return {
            "defeat_level": self.defeat_level,
            "defeat_reason": self.defeat_reason,
            "should_surrender": should_surrender,
            "last_stand_required": self.last_stand_active,
            "last_stand_position": self.last_stand_position,
            "defeat_warnings": self.defeat_warnings,
            "critical_moments": self.critical_moments,
        }

    def get_defeat_level_name(self) -> str:
        """패배 수준 이름 반환"""
        level_names = {
            DefeatLevel.SAFE: "안전",
            DefeatLevel.DISADVANTAGE: "불리",
            DefeatLevel.CRITICAL: "위기",
            DefeatLevel.IMMINENT: "패배 직전",
            DefeatLevel.INEVITABLE: "패배 불가피",
        }
        return level_names.get(self.defeat_level, "알 수 없음")

    def should_attempt_last_stand(self) -> bool:
        """마지막 방어 시도 여부"""
        return self.last_stand_active and self.last_stand_position is not None

    def get_statistics(self) -> Dict:
        """통계 반환"""
        return {
            "defeat_level": self.defeat_level,
            "defeat_level_name": self.get_defeat_level_name(),
            "defeat_reason": self.defeat_reason,
            "defeat_warnings": self.defeat_warnings,
            "critical_moments": self.critical_moments,
            "last_stand_active": self.last_stand_active,
        }
