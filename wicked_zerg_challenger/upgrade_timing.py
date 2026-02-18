# -*- coding: utf-8 -*-
"""
Upgrade Timing Manager - 업그레이드 타이밍 관리자 (#109)

기존 EvolutionUpgradeManager(upgrade_manager.py)를 보완하는
전략적 업그레이드 타이밍 결정 시스템입니다.

주요 기능:
1. 적 상황에 따른 업그레이드 우선순위 동적 결정
2. 최적 타이밍 계산 (경제 상태 + 적 위협 수준)
3. 업그레이드 경로(Path) 추천
4. 투자 대비 효과(ROI) 분석
5. 기존 EvolutionUpgradeManager와 연동
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
except ImportError:
    UnitTypeId = None
    UpgradeId = None


class UpgradePathType(Enum):
    """업그레이드 경로 타입"""
    MELEE_FIRST = "melee_first"          # 근접 공격 우선 (저글링/맹독충)
    RANGED_FIRST = "ranged_first"        # 원거리 공격 우선 (바퀴/히드라)
    ARMOR_FIRST = "armor_first"          # 방어 우선 (테란 바이오닉 대응)
    AIR_FIRST = "air_first"              # 공중 우선 (뮤탈/커럽터)
    BALANCED = "balanced"                # 균형 (공1 -> 방1 -> 공2 -> 방2)
    SPEED_FIRST = "speed_first"          # 속도업 우선 (발업, 히속업 등)


class UpgradeTimingManager:
    """
    업그레이드 타이밍 관리자

    기존 EvolutionUpgradeManager의 우선순위 결정을 지원하며,
    게임 상황에 따른 최적 업그레이드 타이밍을 계산합니다.

    사용 예:
        timing_mgr = UpgradeTimingManager(bot)
        timing_mgr.update()
        path = timing_mgr.get_recommended_path()
        next_timing = timing_mgr.get_next_upgrade_timing()
    """

    # 타이밍 벤치마크 (프로 게이머 기준, 초)
    BENCHMARK_TIMINGS = {
        "zergling_speed": 120,        # 2분 (최대한 빨리)
        "ground_attack_1": 240,       # 4분
        "ground_armor_1": 300,        # 5분
        "roach_speed": 270,           # 4분 30초
        "hydra_speed": 330,           # 5분 30초
        "lair": 240,                  # 4분
        "ground_attack_2": 420,       # 7분
        "ground_armor_2": 480,        # 8분
        "hive": 540,                  # 9분
        "ground_attack_3": 660,       # 11분
        "ground_armor_3": 720,        # 12분
        "adrenal_glands": 600,        # 10분
    }

    def __init__(self, bot):
        """
        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot

        # 현재 추천 경로
        self.recommended_path: UpgradePathType = UpgradePathType.BALANCED

        # 실제 타이밍 기록
        self.actual_timings: Dict[str, float] = {}

        # 성능 추적
        self.timing_score: float = 1.0  # 벤치마크 대비 점수

        # 적 정보 캐시
        self._last_analysis_time: float = 0.0
        self._analysis_interval: float = 10.0

        print("[UPGRADE_TIMING] 업그레이드 타이밍 관리자 초기화 완료")

    def update(self) -> None:
        """매 스텝 업데이트"""
        game_time = getattr(self.bot, "time", 0.0)

        # 분석 주기 확인
        if game_time - self._last_analysis_time < self._analysis_interval:
            return
        self._last_analysis_time = game_time

        # 적 상황 분석 및 경로 결정
        self._analyze_and_recommend(game_time)

        # 타이밍 점수 업데이트
        self._update_timing_score(game_time)

    def get_recommended_path(self) -> UpgradePathType:
        """추천 업그레이드 경로 반환"""
        return self.recommended_path

    def get_upgrade_priority_order(self) -> List[str]:
        """
        현재 추천 경로에 따른 업그레이드 우선순위 반환

        Returns:
            업그레이드 레인 우선순위 리스트 ["melee", "armor", ...]
        """
        path_orders = {
            UpgradePathType.MELEE_FIRST: ["melee", "armor", "melee", "armor", "melee", "armor"],
            UpgradePathType.RANGED_FIRST: ["missile", "armor", "missile", "armor", "missile", "armor"],
            UpgradePathType.ARMOR_FIRST: ["armor", "melee", "armor", "missile", "armor", "melee"],
            UpgradePathType.AIR_FIRST: ["air_attack", "air_armor", "missile", "armor"],
            UpgradePathType.BALANCED: ["melee", "armor", "missile", "melee", "armor", "missile"],
            UpgradePathType.SPEED_FIRST: ["melee", "missile", "armor", "melee", "missile", "armor"],
        }
        return path_orders.get(self.recommended_path, path_orders[UpgradePathType.BALANCED])

    def should_upgrade_now(self, upgrade_name: str) -> bool:
        """
        특정 업그레이드를 지금 시작해야 하는지 판단

        Args:
            upgrade_name: 업그레이드 이름 (벤치마크 키)

        Returns:
            지금 시작해야 하면 True
        """
        game_time = getattr(self.bot, "time", 0.0)
        benchmark = self.BENCHMARK_TIMINGS.get(upgrade_name, 0)

        if benchmark == 0:
            return True

        # 벤치마크 시간 +-30초 이내면 시작
        return abs(game_time - benchmark) < 30 or game_time > benchmark

    def get_next_upgrade_timing(self) -> Optional[Dict[str, Any]]:
        """
        다음 업그레이드 타이밍 정보 반환

        Returns:
            {"upgrade": 이름, "benchmark_time": 벤치마크 시간, "overdue": 지연 여부}
        """
        game_time = getattr(self.bot, "time", 0.0)

        for name, benchmark in sorted(self.BENCHMARK_TIMINGS.items(), key=lambda x: x[1]):
            if name in self.actual_timings:
                continue  # 이미 완료

            return {
                "upgrade": name,
                "benchmark_time": benchmark,
                "current_time": game_time,
                "overdue": game_time > benchmark + 30,
                "time_until": max(0, benchmark - game_time),
            }

        return None

    def record_upgrade_completion(self, upgrade_name: str) -> None:
        """
        업그레이드 완료 시간 기록

        Args:
            upgrade_name: 완료된 업그레이드 이름
        """
        game_time = getattr(self.bot, "time", 0.0)
        self.actual_timings[upgrade_name] = game_time

        benchmark = self.BENCHMARK_TIMINGS.get(upgrade_name, 0)
        if benchmark > 0:
            diff = game_time - benchmark
            status = "정시" if abs(diff) < 15 else ("지연" if diff > 0 else "빠름")
            print(f"[UPGRADE_TIMING] {upgrade_name} 완료: {int(game_time)}초 "
                  f"(벤치마크: {benchmark}초, {status}: {diff:+.0f}초)")

    def _analyze_and_recommend(self, game_time: float) -> None:
        """적 상황 분석 및 업그레이드 경로 추천"""
        if not hasattr(self.bot, "enemy_units"):
            return

        # 적 유닛 분류
        enemy_bio = 0
        enemy_mech = 0
        enemy_air = 0

        for unit in self.bot.enemy_units:
            try:
                name = getattr(unit.type_id, "name", "").upper()
                if name in ("MARINE", "MARAUDER", "ZEALOT", "STALKER", "ADEPT",
                           "ZERGLING", "HYDRALISK"):
                    enemy_bio += 1
                elif name in ("SIEGETANK", "SIEGETANKSIEGED", "THOR", "CYCLONE",
                             "COLOSSUS", "IMMORTAL", "ROACH"):
                    enemy_mech += 1
                elif name in ("MUTALISK", "VOIDRAY", "CARRIER", "BATTLECRUISER",
                             "PHOENIX", "ORACLE", "LIBERATOR", "BANSHEE",
                             "CORRUPTOR", "BROODLORD"):
                    enemy_air += 1
            except Exception:
                continue

        # 경로 결정
        total = enemy_bio + enemy_mech + enemy_air
        if total == 0:
            self.recommended_path = UpgradePathType.BALANCED
            return

        bio_ratio = enemy_bio / total
        mech_ratio = enemy_mech / total
        air_ratio = enemy_air / total

        if air_ratio > 0.4:
            self.recommended_path = UpgradePathType.AIR_FIRST
        elif bio_ratio > 0.6:
            self.recommended_path = UpgradePathType.ARMOR_FIRST
        elif mech_ratio > 0.5:
            self.recommended_path = UpgradePathType.RANGED_FIRST
        else:
            # 아군 조합 기반 결정
            self.recommended_path = self._decide_by_own_composition()

    def _decide_by_own_composition(self) -> UpgradePathType:
        """아군 유닛 조합 기반 경로 결정"""
        if not hasattr(self.bot, "units") or not UnitTypeId:
            return UpgradePathType.BALANCED

        try:
            zergling_count = self.bot.units(UnitTypeId.ZERGLING).amount
            roach_count = self.bot.units(UnitTypeId.ROACH).amount
            hydra_count = self.bot.units(UnitTypeId.HYDRALISK).amount
            muta_count = self.bot.units(UnitTypeId.MUTALISK).amount

            melee_total = zergling_count
            ranged_total = roach_count + hydra_count
            air_total = muta_count

            if air_total > 5:
                return UpgradePathType.AIR_FIRST
            elif ranged_total > melee_total:
                return UpgradePathType.RANGED_FIRST
            elif melee_total > 10:
                return UpgradePathType.MELEE_FIRST
            else:
                return UpgradePathType.BALANCED

        except Exception:
            return UpgradePathType.BALANCED

    def _update_timing_score(self, game_time: float) -> None:
        """벤치마크 대비 타이밍 점수 업데이트"""
        if not self.actual_timings:
            return

        total_diff = 0.0
        count = 0

        for name, actual_time in self.actual_timings.items():
            benchmark = self.BENCHMARK_TIMINGS.get(name, 0)
            if benchmark > 0:
                # 정규화된 차이 (양수 = 지연, 음수 = 빠름)
                diff = (actual_time - benchmark) / benchmark
                total_diff += diff
                count += 1

        if count > 0:
            avg_diff = total_diff / count
            # 점수: 1.0 = 벤치마크 정확히 맞춤, >1.0 = 빠름, <1.0 = 느림
            self.timing_score = max(0.0, 1.0 - avg_diff)

    def get_stats(self) -> Dict[str, Any]:
        """타이밍 통계"""
        return {
            "recommended_path": self.recommended_path.value,
            "timing_score": round(self.timing_score, 2),
            "completed_upgrades": len(self.actual_timings),
            "actual_timings": self.actual_timings,
        }
