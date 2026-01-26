# -*- coding: utf-8 -*-
"""
Reinforcement Learner - 강화 학습 시스템

모든 학습 패턴을 3번 이상 반복 확인하여 신뢰도 높은 지식만 적용
"""

import json
import os
from typing import Dict, List, Any
from collections import defaultdict
import statistics


class ReinforcementLearner:
    """
    강화 학습 시스템

    핵심 원리:
    1. 최소 샘플 수 (MIN_SAMPLES = 3) - 3번 이상 관찰된 패턴만 학습
    2. 학습 가중치 (Confidence Weight) - 샘플이 많을수록 높은 가중치
    3. 반복 강화 (Reinforcement) - 같은 패턴 반복 시 신뢰도 증가
    4. 성공 패턴 우선 (Success Bias) - 승리 게임의 패턴에 더 높은 가중치
    """

    MIN_SAMPLES = 3  # 최소 3번 이상 관찰
    SUCCESS_MULTIPLIER = 2.0  # 승리 게임 가중치 2배
    CONFIDENCE_THRESHOLD = 0.6  # 60% 이상 신뢰도만 적용

    def __init__(self, games_dir: str = "data/games"):
        self.games_dir = games_dir
        self.games_data = []
        self.learning_stats = {
            "total_patterns": 0,
            "learned_patterns": 0,
            "rejected_patterns": 0,
            "confidence_avg": 0.0
        }

    def load_games(self):
        """게임 데이터 로드"""
        if not os.path.exists(self.games_dir):
            return []

        self.games_data = []
        for filename in os.listdir(self.games_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.games_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        game = json.load(f)
                        self.games_data.append(game)
                except Exception as e:
                    print(f"[REINFORCE] Error loading {filename}: {e}")

        print(f"[REINFORCE] Loaded {len(self.games_data)} games for reinforcement learning")
        return self.games_data

    def learn_with_reinforcement(self) -> Dict:
        """강화 학습 실행 - 모든 패턴을 3번씩 반복 확인"""
        if len(self.games_data) < self.MIN_SAMPLES:
            print(f"[REINFORCE] Not enough games ({len(self.games_data)}/{self.MIN_SAMPLES})")
            return {}

        learned_knowledge = {
            "reinforcement_meta": {
                "total_games": len(self.games_data),
                "min_samples": self.MIN_SAMPLES,
                "success_multiplier": self.SUCCESS_MULTIPLIER
            },
            "learned_timings": {},
            "learned_compositions": {},
            "learned_harassment": {},
            "learned_defense": {},
            "learned_map_control": {},
            "enemy_counter_patterns": {}
        }

        print("\n[REINFORCE] Starting reinforcement learning...")
        print("="*60)

        # 1. 타이밍 강화 학습
        timing_knowledge = self._reinforce_timings()
        learned_knowledge["learned_timings"] = timing_knowledge

        # 2. 유닛 구성비 강화 학습
        composition_knowledge = self._reinforce_compositions()
        learned_knowledge["learned_compositions"] = composition_knowledge

        # 3. 하라스 패턴 강화 학습
        harassment_knowledge = self._reinforce_harassment()
        learned_knowledge["learned_harassment"] = harassment_knowledge

        # 4. 방어 패턴 강화 학습
        defense_knowledge = self._reinforce_defense()
        learned_knowledge["learned_defense"] = defense_knowledge

        # 5. 맵 장악 패턴 강화 학습
        map_control_knowledge = self._reinforce_map_control()
        learned_knowledge["learned_map_control"] = map_control_knowledge

        # 6. 적 카운터 패턴 강화 학습
        counter_knowledge = self._reinforce_counters()
        learned_knowledge["enemy_counter_patterns"] = counter_knowledge

        # 학습 통계
        self._print_learning_stats()

        return learned_knowledge

    def _reinforce_timings(self) -> Dict:
        """타이밍 강화 학습 (3번 이상 반복 확인)"""
        print("\n[TIMING] Reinforcement learning for timings...")

        timing_samples = defaultdict(lambda: {"values": [], "wins": 0, "losses": 0})

        for game in self.games_data:
            result = game["game_result"].get("result", "Unknown")
            weight = self.SUCCESS_MULTIPLIER if result == "Victory" else 1.0

            # 확장 타이밍
            for expansion in game.get("expansions", []):
                exp_num = expansion.get("expansion_number", 0)
                time = expansion.get("time", 0)
                key = f"expansion_{exp_num}"

                timing_samples[key]["values"].append((time, weight))
                if result == "Victory":
                    timing_samples[key]["wins"] += 1
                else:
                    timing_samples[key]["losses"] += 1

            # 테크 타이밍
            for tech in game.get("tech_upgrades", []):
                building = tech.get("building", "Unknown")
                time = tech.get("time", 0)
                key = f"tech_{building}"

                timing_samples[key]["values"].append((time, weight))
                if result == "Victory":
                    timing_samples[key]["wins"] += 1
                else:
                    timing_samples[key]["losses"] += 1

        # 강화 학습 적용
        learned_timings = {}
        for key, data in timing_samples.items():
            if len(data["values"]) >= self.MIN_SAMPLES:
                # 가중 평균 계산
                weighted_sum = sum(time * weight for time, weight in data["values"])
                weight_total = sum(weight for _, weight in data["values"])
                avg_time = weighted_sum / weight_total if weight_total > 0 else 0

                # 신뢰도 계산
                confidence = self._calculate_confidence(data["wins"], data["losses"], len(data["values"]))

                if confidence >= self.CONFIDENCE_THRESHOLD:
                    learned_timings[key] = {
                        "avg_time": round(avg_time, 1),
                        "samples": len(data["values"]),
                        "confidence": round(confidence, 3),
                        "winrate": round(data["wins"] / (data["wins"] + data["losses"]) * 100, 1) if (data["wins"] + data["losses"]) > 0 else 0
                    }
                    self.learning_stats["learned_patterns"] += 1
                    print(f"  ✓ {key}: {round(avg_time, 1)}s (conf: {round(confidence, 2)})")
                else:
                    self.learning_stats["rejected_patterns"] += 1

        self.learning_stats["total_patterns"] += len(timing_samples)
        return learned_timings

    def _reinforce_compositions(self) -> Dict:
        """유닛 구성비 강화 학습"""
        print("\n[COMPOSITION] Reinforcement learning for unit compositions...")

        composition_samples = defaultdict(lambda: {"samples": [], "wins": 0, "losses": 0})

        for game in self.games_data:
            result = game["game_result"].get("result", "Unknown")
            weight = self.SUCCESS_MULTIPLIER if result == "Victory" else 1.0

            for comp_snapshot in game.get("unit_composition", []):
                time = comp_snapshot.get("time", 0)
                composition = comp_snapshot.get("composition", {})

                # 시간대별로 분류 (early: 0-5min, mid: 5-10min, late: 10min+)
                if time < 300:
                    phase = "early"
                elif time < 600:
                    phase = "mid"
                else:
                    phase = "late"

                composition_samples[phase]["samples"].append((composition, weight))
                if result == "Victory":
                    composition_samples[phase]["wins"] += 1
                else:
                    composition_samples[phase]["losses"] += 1

        # 강화 학습 적용
        learned_compositions = {}
        for phase, data in composition_samples.items():
            if len(data["samples"]) >= self.MIN_SAMPLES:
                # 가중 평균 구성비 계산
                unit_ratios = self._calculate_weighted_composition(data["samples"])
                confidence = self._calculate_confidence(data["wins"], data["losses"], len(data["samples"]))

                if confidence >= self.CONFIDENCE_THRESHOLD:
                    learned_compositions[phase] = {
                        "unit_ratios": unit_ratios,
                        "samples": len(data["samples"]),
                        "confidence": round(confidence, 3),
                        "winrate": round(data["wins"] / (data["wins"] + data["losses"]) * 100, 1) if (data["wins"] + data["losses"]) > 0 else 0
                    }
                    self.learning_stats["learned_patterns"] += 1
                    print(f"  ✓ {phase}: {len(unit_ratios)} unit types (conf: {round(confidence, 2)})")

        return learned_compositions

    def _reinforce_harassment(self) -> Dict:
        """하라스 패턴 강화 학습"""
        print("\n[HARASSMENT] Reinforcement learning for harassment...")

        harassment_data = {"attempts": 0, "successes": 0, "avg_timing": []}

        for game in self.games_data:
            result = game["game_result"].get("result", "Unknown")
            harassments = game.get("harassment", [])

            for harass in harassments:
                time = harass.get("time", 0)
                harassment_data["attempts"] += 1
                harassment_data["avg_timing"].append(time)

                if result == "Victory":
                    harassment_data["successes"] += 1

        if harassment_data["attempts"] >= self.MIN_SAMPLES:
            success_rate = harassment_data["successes"] / harassment_data["attempts"]
            avg_timing = statistics.mean(harassment_data["avg_timing"]) if harassment_data["avg_timing"] else 0

            return {
                "avg_harassment_timing": round(avg_timing, 1),
                "success_rate": round(success_rate * 100, 1),
                "total_attempts": harassment_data["attempts"],
                "confidence": self._calculate_confidence(harassment_data["successes"], harassment_data["attempts"] - harassment_data["successes"], harassment_data["attempts"])
            }

        return {}

    def _reinforce_defense(self) -> Dict:
        """방어 패턴 강화 학습"""
        print("\n[DEFENSE] Reinforcement learning for defense...")

        defense_samples = {"events": 0, "successful": 0, "failed": 0}

        for game in self.games_data:
            result = game["game_result"].get("result", "Unknown")
            defense_events = game.get("defense_events", [])

            for event in defense_events:
                defense_samples["events"] += 1
                if result == "Victory":
                    defense_samples["successful"] += 1
                else:
                    defense_samples["failed"] += 1

        if defense_samples["events"] >= self.MIN_SAMPLES:
            success_rate = defense_samples["successful"] / defense_samples["events"] if defense_samples["events"] > 0 else 0

            return {
                "total_defense_events": defense_samples["events"],
                "success_rate": round(success_rate * 100, 1),
                "confidence": self._calculate_confidence(defense_samples["successful"], defense_samples["failed"], defense_samples["events"])
            }

        return {}

    def _reinforce_map_control(self) -> Dict:
        """맵 장악 패턴 강화 학습"""
        print("\n[MAP_CONTROL] Reinforcement learning for map control...")

        map_control_data = {"samples": [], "wins": 0, "losses": 0}

        for game in self.games_data:
            result = game["game_result"].get("result", "Unknown")
            map_controls = game.get("map_control", [])

            for control in map_controls:
                center_ratio = control.get("center_control", {}).get("control_ratio", 0)
                expansions = control.get("controlled_expansions", 0)

                map_control_data["samples"].append({
                    "center_ratio": center_ratio,
                    "expansions": expansions
                })

                if result == "Victory":
                    map_control_data["wins"] += 1
                else:
                    map_control_data["losses"] += 1

        if len(map_control_data["samples"]) >= self.MIN_SAMPLES:
            avg_center = statistics.mean([s["center_ratio"] for s in map_control_data["samples"]])
            avg_expansions = statistics.mean([s["expansions"] for s in map_control_data["samples"]])

            return {
                "avg_center_control": round(avg_center, 2),
                "avg_controlled_expansions": round(avg_expansions, 1),
                "samples": len(map_control_data["samples"]),
                "winrate": round(map_control_data["wins"] / (map_control_data["wins"] + map_control_data["losses"]) * 100, 1) if (map_control_data["wins"] + map_control_data["losses"]) > 0 else 0
            }

        return {}

    def _reinforce_counters(self) -> Dict:
        """적 카운터 패턴 강화 학습"""
        print("\n[COUNTERS] Reinforcement learning for enemy counters...")

        # 현재는 기본 구현 - 적 유닛 대응 패턴 학습
        # TODO: 실제 교전 결과 기반 카운터 학습

        return {
            "note": "Counter patterns require more engagement data"
        }

    def _calculate_confidence(self, wins: int, losses: int, total_samples: int) -> float:
        """신뢰도 계산"""
        # 샘플 수가 많을수록 높은 신뢰도
        sample_confidence = min(total_samples / (self.MIN_SAMPLES * 3), 1.0)

        # 승률이 높을수록 높은 신뢰도
        total_games = wins + losses
        winrate_confidence = wins / total_games if total_games > 0 else 0.5

        # 종합 신뢰도 (샘플 신뢰도 70%, 승률 신뢰도 30%)
        confidence = (sample_confidence * 0.7) + (winrate_confidence * 0.3)

        return confidence

    def _calculate_weighted_composition(self, samples: List[tuple]) -> Dict:
        """가중 평균 유닛 구성비 계산"""
        unit_totals = defaultdict(lambda: {"weighted_sum": 0.0, "weight_sum": 0.0})

        for composition, weight in samples:
            for unit_type, data in composition.items():
                ratio = data.get("ratio", 0)
                unit_totals[unit_type]["weighted_sum"] += ratio * weight
                unit_totals[unit_type]["weight_sum"] += weight

        # 가중 평균 계산
        weighted_ratios = {}
        for unit_type, totals in unit_totals.items():
            if totals["weight_sum"] > 0:
                weighted_ratios[unit_type] = round(totals["weighted_sum"] / totals["weight_sum"], 3)

        return weighted_ratios

    def _print_learning_stats(self):
        """학습 통계 출력"""
        print("\n" + "="*60)
        print("REINFORCEMENT LEARNING STATISTICS")
        print("="*60)
        print(f"Total patterns analyzed: {self.learning_stats['total_patterns']}")
        print(f"Patterns learned (>=60% confidence): {self.learning_stats['learned_patterns']}")
        print(f"Patterns rejected (<60% confidence): {self.learning_stats['rejected_patterns']}")

        if self.learning_stats['total_patterns'] > 0:
            learn_rate = self.learning_stats['learned_patterns'] / self.learning_stats['total_patterns'] * 100
            print(f"Learning rate: {round(learn_rate, 1)}%")

        print("="*60 + "\n")


def main():
    """메인 실행"""
    learner = ReinforcementLearner()
    learner.load_games()
    learned_knowledge = learner.learn_with_reinforcement()

    # 결과 저장
    output_file = "learned_knowledge_reinforced.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(learned_knowledge, f, indent=2, ensure_ascii=False)

    print(f"\n[REINFORCE] Learned knowledge saved to: {output_file}")


if __name__ == "__main__":
    main()
