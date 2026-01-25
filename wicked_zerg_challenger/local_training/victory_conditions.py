# -*- coding: utf-8 -*-
"""
Victory & Defeat Conditions Learning System

승리조건과 패배조건을 명확히 학습시키는 시스템:

승리 조건:
1. 경제 우위: 드론 수, 기지 수, 자원 수집률
2. 군사력 우위: 군대 규모, 전투 효율
3. 적 피해: 적 일꾼/건물 파괴
4. 기술 우위: 업그레이드 완료

패배 조건:
1. 경제 붕괴: 드론 부족, 확장 실패
2. 방어 실패: 군대 부족, 방어 건물 없음
3. 자원 낭비: 미네랄 뱅킹
4. 기술 지연: 업그레이드 부족
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class VictoryCondition:
    """승리 조건 정의"""

    # 경제 우위
    ECONOMY_ADVANTAGE = "economy_advantage"  # 경제 우위 확보
    EXPANSION_SUCCESS = "expansion_success"  # 확장 성공
    WORKER_SATURATION = "worker_saturation"  # 일꾼 포화

    # 군사력 우위
    ARMY_SUPERIORITY = "army_superiority"  # 군대 우위
    COMBAT_EFFICIENCY = "combat_efficiency"  # 전투 효율

    # 적 피해
    ENEMY_WORKERS_KILLED = "enemy_workers_killed"  # 적 일꾼 학살
    ENEMY_BASES_DESTROYED = "enemy_bases_destroyed"  # 적 기지 파괴
    ENEMY_ARMY_CRUSHED = "enemy_army_crushed"  # 적 군대 섬멸

    # 기술 우위
    TECH_ADVANTAGE = "tech_advantage"  # 기술 우위
    UPGRADE_COMPLETE = "upgrade_complete"  # 업그레이드 완료


class DefeatCondition:
    """패배 조건 정의"""

    # 경제 붕괴
    ECONOMY_COLLAPSE = "economy_collapse"  # 경제 붕괴
    EXPANSION_FAILURE = "expansion_failure"  # 확장 실패
    WORKER_SHORTAGE = "worker_shortage"  # 일꾼 부족

    # 방어 실패
    DEFENSE_FAILURE = "defense_failure"  # 방어 실패
    ARMY_SHORTAGE = "army_shortage"  # 군대 부족
    BASE_LOST = "base_lost"  # 기지 상실

    # 자원 낭비
    RESOURCE_WASTE = "resource_waste"  # 자원 낭비 (뱅킹)
    PRODUCTION_HALT = "production_halt"  # 생산 중단

    # 기술 지연
    TECH_DELAY = "tech_delay"  # 기술 지연
    UPGRADE_NONE = "upgrade_none"  # 업그레이드 없음


class VictoryConditionsLearner:
    """승리/패배 조건 학습 시스템"""

    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.conditions_file = self.data_dir / "victory_conditions.json"

        # 승리 패턴 추적
        self.victory_patterns: List[Dict] = []
        self.defeat_patterns: List[Dict] = []

        # 조건별 승리/패배 카운트
        self.victory_counts: Dict[str, int] = {}
        self.defeat_counts: Dict[str, int] = {}

        # 로드
        self._load_data()

    def _load_data(self) -> None:
        """데이터 로드"""
        if not self.conditions_file.exists():
            return

        try:
            with open(self.conditions_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.victory_patterns = data.get("victory_patterns", [])[-100:]  # 최근 100개
            self.defeat_patterns = data.get("defeat_patterns", [])[-100:]
            self.victory_counts = data.get("victory_counts", {})
            self.defeat_counts = data.get("defeat_counts", {})
        except Exception as e:
            print(f"[VICTORY_CONDITIONS] Failed to load data: {e}")

    def _save_data(self) -> None:
        """데이터 저장"""
        try:
            data = {
                "victory_patterns": self.victory_patterns[-100:],
                "defeat_patterns": self.defeat_patterns[-100:],
                "victory_counts": self.victory_counts,
                "defeat_counts": self.defeat_counts,
                "last_updated": datetime.now().isoformat(),
            }

            with open(self.conditions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[VICTORY_CONDITIONS] Failed to save data: {e}")

    def analyze_game_result(self, bot, game_result: str) -> Tuple[List[str], float]:
        """
        게임 결과 분석

        Args:
            bot: BotAI 인스턴스
            game_result: "Victory" or "Defeat"

        Returns:
            (조건 리스트, 최종 보상)
        """
        game_time = getattr(bot, "time", 0)

        if game_result == "Victory":
            return self._analyze_victory(bot, game_time)
        else:
            return self._analyze_defeat(bot, game_time)

    def _analyze_victory(self, bot, game_time: float) -> Tuple[List[str], float]:
        """승리 조건 분석"""
        conditions = []
        final_reward = 10.0  # 기본 승리 보상

        # 1. 경제 우위 체크
        drone_count = len(bot.units.filter(lambda u: u.name == "Drone"))
        base_count = len(bot.townhalls)

        if drone_count >= 50:
            conditions.append(VictoryCondition.WORKER_SATURATION)
            final_reward += 5.0
        elif drone_count >= 30:
            conditions.append(VictoryCondition.ECONOMY_ADVANTAGE)
            final_reward += 2.0

        if base_count >= 4:
            conditions.append(VictoryCondition.EXPANSION_SUCCESS)
            final_reward += 3.0

        # 2. 군사력 우위 체크
        army_units = bot.units.filter(lambda u: u.can_attack and u.name != "Queen")
        army_value = sum(u.health + u.shield for u in army_units)

        if army_value >= 2000:
            conditions.append(VictoryCondition.ARMY_SUPERIORITY)
            final_reward += 5.0
        elif army_value >= 1000:
            conditions.append(VictoryCondition.COMBAT_EFFICIENCY)
            final_reward += 2.0

        # 3. 적 피해 체크
        if hasattr(bot, "state") and hasattr(bot.state, "score"):
            score = bot.state.score
            killed_units = getattr(score, "killed_value_units", 0)
            killed_structures = getattr(score, "killed_value_structures", 0)

            # 적 일꾼 킬 (가치 50 단위로 추정)
            estimated_worker_kills = killed_units / 50
            if estimated_worker_kills >= 10:
                conditions.append(VictoryCondition.ENEMY_WORKERS_KILLED)
                final_reward += 8.0  # 일꾼 학살 = 매우 높은 보상!

            # 적 건물 파괴
            if killed_structures >= 1000:  # 기지 파괴
                conditions.append(VictoryCondition.ENEMY_BASES_DESTROYED)
                final_reward += 10.0  # 기지 파괴 = 최고 보상!

            # 적 군대 섬멸
            if killed_units >= 2000:
                conditions.append(VictoryCondition.ENEMY_ARMY_CRUSHED)
                final_reward += 6.0

        # 4. 기술 우위 체크
        if hasattr(bot, "state") and hasattr(bot.state, "upgrades"):
            upgrade_count = len(bot.state.upgrades)
            if upgrade_count >= 5:
                conditions.append(VictoryCondition.TECH_ADVANTAGE)
                final_reward += 4.0
            elif upgrade_count >= 2:
                conditions.append(VictoryCondition.UPGRADE_COMPLETE)
                final_reward += 2.0

        # 5. 시간 기반 보너스
        if game_time < 300:  # 5분 이내 승리
            final_reward += 10.0  # 빠른 승리 = 높은 보상
        elif game_time < 600:  # 10분 이내 승리
            final_reward += 5.0

        # 기록
        self._record_victory(conditions, game_time, final_reward)

        return conditions, final_reward

    def _analyze_defeat(self, bot, game_time: float) -> Tuple[List[str], float]:
        """패배 조건 분석"""
        conditions = []
        final_penalty = -10.0  # 기본 패배 페널티

        # 1. 경제 붕괴 체크
        drone_count = len(bot.units.filter(lambda u: u.name == "Drone"))
        base_count = len(bot.townhalls)

        if drone_count < 10 and game_time > 180:  # 3분 이후 드론 10 미만
            conditions.append(DefeatCondition.ECONOMY_COLLAPSE)
            final_penalty -= 5.0
        elif drone_count < 20 and game_time > 300:  # 5분 이후 드론 20 미만
            conditions.append(DefeatCondition.WORKER_SHORTAGE)
            final_penalty -= 3.0

        if base_count == 1 and game_time > 180:  # 3분 이후 1베이스
            conditions.append(DefeatCondition.EXPANSION_FAILURE)
            final_penalty -= 5.0

        # 2. 방어 실패 체크
        army_units = bot.units.filter(lambda u: u.can_attack and u.name != "Queen")
        army_count = len(army_units)

        if army_count < 5 and game_time > 240:  # 4분 이후 군대 5 미만
            conditions.append(DefeatCondition.DEFENSE_FAILURE)
            final_penalty -= 5.0
        elif army_count < 10 and game_time > 300:  # 5분 이후 군대 10 미만
            conditions.append(DefeatCondition.ARMY_SHORTAGE)
            final_penalty -= 3.0

        # 기지 상실
        if base_count == 0:
            conditions.append(DefeatCondition.BASE_LOST)
            final_penalty -= 10.0  # 모든 기지 상실 = 최악

        # 3. 자원 낭비 체크
        minerals = getattr(bot, "minerals", 0)
        if minerals > 1500 and game_time > 120:  # 2분 이후 미네랄 1500+
            conditions.append(DefeatCondition.RESOURCE_WASTE)
            final_penalty -= 5.0

        # 4. 기술 지연 체크
        if game_time > 360:  # 6분 이후
            if hasattr(bot, "state") and hasattr(bot.state, "upgrades"):
                upgrade_count = len(bot.state.upgrades)
                if upgrade_count == 0:
                    conditions.append(DefeatCondition.UPGRADE_NONE)
                    final_penalty -= 3.0

        # 5. 시간 기반 페널티
        if game_time < 180:  # 3분 이내 패배 = 초반 러시 당함
            final_penalty -= 8.0  # 빠른 패배 = 높은 페널티

        # 기록
        self._record_defeat(conditions, game_time, final_penalty)

        return conditions, final_penalty

    def _record_victory(self, conditions: List[str], game_time: float, reward: float) -> None:
        """승리 기록"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "game_time": game_time,
            "conditions": conditions,
            "reward": reward,
        }

        self.victory_patterns.append(record)

        for condition in conditions:
            self.victory_counts[condition] = self.victory_counts.get(condition, 0) + 1

        self._save_data()

    def _record_defeat(self, conditions: List[str], game_time: float, penalty: float) -> None:
        """패배 기록"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "game_time": game_time,
            "conditions": conditions,
            "penalty": penalty,
        }

        self.defeat_patterns.append(record)

        for condition in conditions:
            self.defeat_counts[condition] = self.defeat_counts.get(condition, 0) + 1

        self._save_data()

    def get_most_common_victory_conditions(self, top_n: int = 5) -> List[Tuple[str, int]]:
        """가장 흔한 승리 조건 반환"""
        sorted_conditions = sorted(
            self.victory_counts.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_conditions[:top_n]

    def get_most_common_defeat_conditions(self, top_n: int = 5) -> List[Tuple[str, int]]:
        """가장 흔한 패배 조건 반환"""
        sorted_conditions = sorted(
            self.defeat_counts.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_conditions[:top_n]

    def get_win_rate(self) -> float:
        """승률 반환"""
        total_games = len(self.victory_patterns) + len(self.defeat_patterns)
        if total_games == 0:
            return 0.0
        return len(self.victory_patterns) / total_games

    def print_analysis(self) -> None:
        """분석 결과 출력"""
        print("\n" + "=" * 70)
        print("[VICTORY CONDITIONS] GAME RESULT ANALYSIS")
        print("=" * 70)

        total_victories = len(self.victory_patterns)
        total_defeats = len(self.defeat_patterns)
        total_games = total_victories + total_defeats

        if total_games == 0:
            print("No games recorded yet.")
            print("=" * 70)
            return

        win_rate = self.get_win_rate()

        print(f"Total Games: {total_games}")
        print(f"Victories: {total_victories}")
        print(f"Defeats: {total_defeats}")
        print(f"Win Rate: {win_rate:.1%}")

        print("\n" + "-" * 70)
        print("Top Victory Conditions:")

        victory_conditions = self.get_most_common_victory_conditions(5)
        if victory_conditions:
            for idx, (condition, count) in enumerate(victory_conditions, 1):
                percentage = (count / total_victories * 100) if total_victories > 0 else 0
                print(f"  {idx}. {condition}: {count} times ({percentage:.1f}%)")
        else:
            print("  No victories yet.")

        print("\n" + "-" * 70)
        print("Top Defeat Conditions:")

        defeat_conditions = self.get_most_common_defeat_conditions(5)
        if defeat_conditions:
            for idx, (condition, count) in enumerate(defeat_conditions, 1):
                percentage = (count / total_defeats * 100) if total_defeats > 0 else 0
                print(f"  {idx}. {condition}: {count} times ({percentage:.1f}%)")
        else:
            print("  No defeats yet (amazing!).")

        print("\n" + "-" * 70)
        print("Learning Insights:")

        # 승리 인사이트
        if victory_conditions:
            top_victory = victory_conditions[0][0]
            print(f"  - Most common path to victory: {top_victory}")
            print(f"    -> Keep focusing on this strategy!")

        # 패배 인사이트
        if defeat_conditions:
            top_defeat = defeat_conditions[0][0]
            print(f"  - Most common cause of defeat: {top_defeat}")
            print(f"    -> This needs urgent improvement!")

        # 승률 기반 조언
        if win_rate < 0.3:
            print(f"  - Win rate is low ({win_rate:.1%}). Focus on fundamentals.")
        elif win_rate < 0.5:
            print(f"  - Win rate is improving ({win_rate:.1%}). Keep learning!")
        elif win_rate < 0.7:
            print(f"  - Win rate is good ({win_rate:.1%}). Refine strategies.")
        else:
            print(f"  - Win rate is excellent ({win_rate:.1%}). Mastery achieved!")

        print("=" * 70)

    def get_reward_adjustment_for_conditions(self) -> Dict[str, float]:
        """
        조건별 보상 조정 값 반환

        자주 발생하는 패배 조건은 강한 페널티로 조정
        자주 발생하는 승리 조건은 강한 보상으로 조정

        Returns:
            {"condition": multiplier} 딕셔너리
        """
        adjustments = {}

        # 패배 조건 조정 (자주 발생할수록 강한 페널티)
        for condition, count in self.defeat_counts.items():
            if count >= 5:
                adjustments[condition] = 1.0 + (count * 0.2)  # 20%씩 증가

        # 승리 조건 조정 (자주 발생할수록 강한 보상)
        for condition, count in self.victory_counts.items():
            if count >= 3:
                adjustments[condition] = 1.0 + (count * 0.1)  # 10%씩 증가

        return adjustments
