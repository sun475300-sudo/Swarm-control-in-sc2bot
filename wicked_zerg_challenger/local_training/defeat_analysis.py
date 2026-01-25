# -*- coding: utf-8 -*-
"""
Defeat Analysis System - 패배 원인 분석 및 학습

봇이 왜 졌는지 스스로 분석하고, 다음 게임에 개선점을 반영합니다.

분석 항목:
1. 경제 실패 (드론 부족, 확장 지연)
2. 자원 낭비 (미네랄 뱅킹)
3. 방어 실패 (군대 부족)
4. 보급 차단 (supply block)
5. 기술 지연 (업그레이드 부족)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class DefeatReason:
    """패배 원인 정의"""

    # 경제 관련
    ECONOMY_LOW_DRONES = "economy_low_drones"  # 드론 부족
    ECONOMY_LATE_EXPANSION = "economy_late_expansion"  # 확장 지연
    ECONOMY_NO_GAS = "economy_no_gas"  # 가스 미확보

    # 자원 관련
    RESOURCE_BANKING_MINERALS = "resource_banking_minerals"  # 미네랄 뱅킹
    RESOURCE_BANKING_GAS = "resource_banking_gas"  # 가스 뱅킹

    # 군대 관련
    ARMY_TOO_SMALL = "army_too_small"  # 군대 규모 부족
    ARMY_WRONG_COMPOSITION = "army_wrong_composition"  # 잘못된 조합

    # 방어 관련
    DEFENSE_NO_UNITS = "defense_no_units"  # 방어 병력 없음
    DEFENSE_NO_BUILDINGS = "defense_no_buildings"  # 방어 건물 없음

    # 매크로 관련
    MACRO_SUPPLY_BLOCKED = "macro_supply_blocked"  # 보급 차단
    MACRO_LARVA_CAPPED = "macro_larva_capped"  # 애벌레 낭비
    MACRO_NO_PRODUCTION = "macro_no_production"  # 생산 시설 없음

    # 기술 관련
    TECH_NO_UPGRADES = "tech_no_upgrades"  # 업그레이드 없음
    TECH_LATE_TECH = "tech_late_tech"  # 기술 지연


class DefeatAnalysis:
    """패배 분석 시스템"""

    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.analysis_file = self.data_dir / "defeat_analysis.json"

        # 패배 원인 히스토리
        self.defeat_history: List[Dict] = []

        # 패배 원인별 카운트
        self.reason_counts: Dict[str, int] = {}

        # 로드
        self._load_history()

    def _load_history(self) -> None:
        """패배 히스토리 로드"""
        if not self.analysis_file.exists():
            return

        try:
            with open(self.analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.defeat_history = data.get("history", [])
            self.reason_counts = data.get("reason_counts", {})
        except Exception as e:
            print(f"[DEFEAT_ANALYSIS] Failed to load history: {e}")

    def _save_history(self) -> None:
        """패배 히스토리 저장"""
        try:
            data = {
                "history": self.defeat_history[-50:],  # 최근 50개만 저장
                "reason_counts": self.reason_counts,
                "last_updated": datetime.now().isoformat(),
            }

            with open(self.analysis_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[DEFEAT_ANALYSIS] Failed to save history: {e}")

    def analyze_defeat(self, bot, game_result: str = "Defeat") -> List[str]:
        """
        패배 원인 분석

        Args:
            bot: BotAI 인스턴스
            game_result: 게임 결과 ("Defeat", "Victory")

        Returns:
            패배 원인 리스트
        """
        if game_result != "Defeat":
            return []

        reasons = []
        game_time = getattr(bot, "time", 0)

        # 1. 경제 분석
        drone_count = len(bot.units.filter(lambda u: u.name == "Drone"))
        base_count = len(bot.townhalls)

        if game_time > 180 and drone_count < 30:  # 3분 이후 드론 30 미만
            reasons.append(DefeatReason.ECONOMY_LOW_DRONES)

        if game_time > 120 and base_count < 2:  # 2분 이후 1베이스
            reasons.append(DefeatReason.ECONOMY_LATE_EXPANSION)

        if game_time > 180 and len(bot.gas_buildings) == 0:  # 3분 이후 가스 없음
            reasons.append(DefeatReason.ECONOMY_NO_GAS)

        # 2. 자원 뱅킹 분석
        minerals = getattr(bot, "minerals", 0)
        vespene = getattr(bot, "vespene", 0)

        if game_time > 120 and minerals > 1000:  # 2분 이후 미네랄 1000+
            reasons.append(DefeatReason.RESOURCE_BANKING_MINERALS)

        if game_time > 240 and vespene > 500:  # 4분 이후 가스 500+
            reasons.append(DefeatReason.RESOURCE_BANKING_GAS)

        # 3. 군대 분석
        army_units = bot.units.filter(lambda u: u.can_attack and u.name != "Queen")
        army_count = len(army_units)
        army_value = sum(u.health + u.shield for u in army_units)

        if game_time > 240 and army_count < 10:  # 4분 이후 군대 10 미만
            reasons.append(DefeatReason.ARMY_TOO_SMALL)

        if game_time > 300 and army_value < 500:  # 5분 이후 군대 가치 500 미만
            reasons.append(DefeatReason.ARMY_TOO_SMALL)

        # 4. 방어 분석
        defense_buildings = bot.structures.filter(
            lambda s: s.name in ["SpineCrawler", "SporeCrawler"]
        )

        if game_time > 300 and len(defense_buildings) == 0:  # 5분 이후 방어 건물 없음
            reasons.append(DefeatReason.DEFENSE_NO_BUILDINGS)

        # 5. 매크로 분석
        supply_left = bot.supply_left
        supply_cap = bot.supply_cap

        if supply_left <= 0 and supply_cap < 200:  # Supply blocked
            reasons.append(DefeatReason.MACRO_SUPPLY_BLOCKED)

        # 애벌레 체크
        total_larva = sum(th.assigned_harvesters for th in bot.townhalls.ready)
        if total_larva > 15:  # 애벌레 15+ = 낭비
            reasons.append(DefeatReason.MACRO_LARVA_CAPPED)

        # 6. 기술 분석
        if game_time > 360:  # 6분 이후
            if not hasattr(bot, "state") or not bot.state:
                pass
            elif hasattr(bot.state, "upgrades"):
                upgrades = bot.state.upgrades
                if len(upgrades) == 0:
                    reasons.append(DefeatReason.TECH_NO_UPGRADES)

        # 패배 원인 기록
        self._record_defeat(reasons, game_time)

        return reasons

    def _record_defeat(self, reasons: List[str], game_time: float) -> None:
        """패배 기록"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "game_time": game_time,
            "reasons": reasons,
        }

        self.defeat_history.append(record)

        # 카운트 업데이트
        for reason in reasons:
            self.reason_counts[reason] = self.reason_counts.get(reason, 0) + 1

        self._save_history()

    def get_top_failure_reasons(self, top_n: int = 5) -> List[tuple]:
        """
        가장 빈번한 패배 원인 반환

        Args:
            top_n: 상위 N개

        Returns:
            [(reason, count), ...] 리스트
        """
        sorted_reasons = sorted(
            self.reason_counts.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_reasons[:top_n]

    def get_feedback_for_next_game(self) -> Dict[str, float]:
        """
        다음 게임을 위한 피드백 (보상 가중치 조정)

        Returns:
            {"reason": weight_multiplier} 형태의 딕셔너리
        """
        feedback = {}

        top_reasons = self.get_top_failure_reasons(top_n=3)

        for reason, count in top_reasons:
            # 빈도가 높을수록 강한 보상 가중치 적용
            weight = 1.0 + (count * 0.1)  # 10%씩 증가

            if reason == DefeatReason.ECONOMY_LOW_DRONES:
                feedback["drone_production"] = weight
            elif reason == DefeatReason.RESOURCE_BANKING_MINERALS:
                feedback["mineral_spending"] = weight
            elif reason == DefeatReason.ARMY_TOO_SMALL:
                feedback["army_production"] = weight
            elif reason == DefeatReason.ECONOMY_LATE_EXPANSION:
                feedback["expansion_timing"] = weight
            elif reason == DefeatReason.MACRO_SUPPLY_BLOCKED:
                feedback["supply_management"] = weight

        return feedback

    def print_analysis(self) -> None:
        """패배 분석 출력"""
        print("\n" + "=" * 70)
        print("[DEFEAT_ANALYSIS] FAILURE PATTERN ANALYSIS")
        print("=" * 70)
        print(f"Total Defeats Analyzed: {len(self.defeat_history)}")

        if not self.reason_counts:
            print("No defeats recorded yet.")
            print("=" * 70)
            return

        print("\nTop Failure Reasons:")
        top_reasons = self.get_top_failure_reasons(top_n=5)

        for idx, (reason, count) in enumerate(top_reasons, 1):
            percentage = (count / len(self.defeat_history)) * 100
            print(f"  {idx}. {reason}: {count} times ({percentage:.1f}%)")

        print("\n" + "-" * 70)
        print("Recommended Focus Areas:")
        feedback = self.get_feedback_for_next_game()

        for area, weight in feedback.items():
            boost = (weight - 1.0) * 100
            print(f"  - {area}: +{boost:.0f}% priority")

        print("=" * 70)

    def get_penalty_multiplier_for_reason(self, reason: str) -> float:
        """
        특정 패배 원인에 대한 페널티 배율 반환

        자주 발생하는 실패 원인일수록 강한 페널티 적용

        Args:
            reason: DefeatReason 상수

        Returns:
            페널티 배율 (1.0 = 기본, 2.0 = 2배 강화)
        """
        count = self.reason_counts.get(reason, 0)

        if count == 0:
            return 1.0

        # 빈도에 따라 페널티 강화
        # 5회 이상 → 1.5배
        # 10회 이상 → 2.0배
        # 20회 이상 → 3.0배
        if count >= 20:
            return 3.0
        elif count >= 10:
            return 2.0
        elif count >= 5:
            return 1.5
        else:
            return 1.0 + (count * 0.1)

    def clear_old_history(self, keep_recent: int = 50) -> None:
        """오래된 기록 삭제"""
        if len(self.defeat_history) > keep_recent:
            self.defeat_history = self.defeat_history[-keep_recent:]
            self._save_history()
