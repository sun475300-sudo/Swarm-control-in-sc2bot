# -*- coding: utf-8 -*-
"""
Knowledge Updater - 학습 데이터 분석 및 지식 베이스 업데이트

수집된 게임 데이터를 분석하여 commander_knowledge.json을 자동 업데이트
"""

import json
import os
from typing import Dict, List, Tuple
from collections import defaultdict
import statistics


class KnowledgeUpdater:
    """
    학습 데이터 분석기

    기능:
    1. 맵별 승률 분석 → 맵별 최적 빌드 오더 추천
    2. 타이밍 분석 → 평균 확장/테크 타이밍 계산
    3. 카운터 분석 → 교전 결과 기반 유닛 카운터 학습
    4. 자원 효율 분석 → 최적 자원 사용 패턴
    """

    def __init__(self, games_dir: str = "data/games", knowledge_file: str = "commander_knowledge.json"):
        self.games_dir = games_dir
        self.knowledge_file = knowledge_file
        self.games_data = []

    def load_all_games(self):
        """모든 게임 데이터 로드"""
        if not os.path.exists(self.games_dir):
            print(f"[KNOWLEDGE] Games directory not found: {self.games_dir}")
            return

        self.games_data = []

        for filename in os.listdir(self.games_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.games_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        game_data = json.load(f)
                        self.games_data.append(game_data)
                except Exception as e:
                    print(f"[KNOWLEDGE] Error loading {filename}: {e}")

        print(f"[KNOWLEDGE] Loaded {len(self.games_data)} games")

    def analyze_and_update(self):
        """전체 분석 및 업데이트"""
        if not self.games_data:
            print("[KNOWLEDGE] No games to analyze")
            return

        print("[KNOWLEDGE] Starting analysis...")

        # 지식 베이스 로드
        knowledge = self._load_knowledge()

        # 1. 맵별 승률 분석
        map_stats = self._analyze_map_winrates()
        knowledge["map_statistics"] = map_stats

        # 2. 타이밍 분석
        timing_stats = self._analyze_timings()
        knowledge["learned_timings"] = timing_stats

        # 3. 확장 패턴 학습
        expansion_patterns = self._analyze_expansions()
        knowledge["expansion_patterns"] = expansion_patterns

        # 4. 빌드 오더 패턴 추출
        build_patterns = self._extract_build_patterns()
        knowledge["learned_builds"] = build_patterns

        # 5. 교전 분석
        engagement_stats = self._analyze_engagements()
        knowledge["engagement_statistics"] = engagement_stats

        # 저장
        self._save_knowledge(knowledge)

        print("[KNOWLEDGE] Analysis complete!")
        self._print_summary(knowledge)

    def _load_knowledge(self) -> Dict:
        """기존 지식 베이스 로드"""
        if os.path.exists(self.knowledge_file):
            with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_knowledge(self, knowledge: Dict):
        """지식 베이스 저장"""
        with open(self.knowledge_file, 'w', encoding='utf-8') as f:
            json.dump(knowledge, f, indent=2, ensure_ascii=False)

    def _analyze_map_winrates(self) -> Dict:
        """맵별 승률 분석"""
        map_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "games": 0})

        for game in self.games_data:
            map_name = game["meta"].get("map_name", "Unknown")
            result = game["game_result"].get("result", "Unknown")

            map_stats[map_name]["games"] += 1

            if result == "Victory":
                map_stats[map_name]["wins"] += 1
            elif result == "Defeat":
                map_stats[map_name]["losses"] += 1

        # 승률 계산
        for map_name, stats in map_stats.items():
            if stats["games"] > 0:
                stats["winrate"] = round(stats["wins"] / stats["games"] * 100, 1)
            else:
                stats["winrate"] = 0.0

        return dict(map_stats)

    def _analyze_timings(self) -> Dict:
        """타이밍 분석 (평균 확장 시간, 테크 시간)"""
        timings = {
            "expansion": defaultdict(list),
            "tech": defaultdict(list)
        }

        for game in self.games_data:
            # 확장 타이밍
            for expansion in game.get("expansions", []):
                exp_num = expansion.get("expansion_number", 0)
                time = expansion.get("time", 0)
                timings["expansion"][f"base_{exp_num}"].append(time)

            # 테크 타이밍
            for tech in game.get("tech_upgrades", []):
                building = tech.get("building", "Unknown")
                time = tech.get("time", 0)
                timings["tech"][building].append(time)

        # 평균 계산
        result = {
            "expansion_avg": {},
            "tech_avg": {}
        }

        for exp_type, times in timings["expansion"].items():
            if times:
                result["expansion_avg"][exp_type] = {
                    "avg": round(statistics.mean(times), 1),
                    "min": round(min(times), 1),
                    "max": round(max(times), 1),
                    "samples": len(times)
                }

        for tech_type, times in timings["tech"].items():
            if times:
                result["tech_avg"][tech_type] = {
                    "avg": round(statistics.mean(times), 1),
                    "min": round(min(times), 1),
                    "max": round(max(times), 1),
                    "samples": len(times)
                }

        return result

    def _analyze_expansions(self) -> Dict:
        """확장 패턴 분석"""
        expansion_data = []

        for game in self.games_data:
            result = game["game_result"].get("result", "Unknown")
            expansions = game.get("expansions", [])

            if expansions:
                expansion_data.append({
                    "result": result,
                    "expansion_times": [e["time"] for e in expansions],
                    "final_bases": len(expansions)
                })

        # 승리 게임의 평균 확장 패턴
        winning_expansions = [e for e in expansion_data if e["result"] == "Victory"]

        if winning_expansions:
            avg_bases = statistics.mean([e["final_bases"] for e in winning_expansions])
            avg_2nd_base = statistics.mean([e["expansion_times"][0] for e in winning_expansions if len(e["expansion_times"]) > 0])
            avg_3rd_base = statistics.mean([e["expansion_times"][1] for e in winning_expansions if len(e["expansion_times"]) > 1])

            return {
                "winning_pattern": {
                    "avg_bases_at_10min": round(avg_bases, 1),
                    "avg_2nd_base_timing": round(avg_2nd_base, 1),
                    "avg_3rd_base_timing": round(avg_3rd_base, 1) if winning_expansions else None,
                    "samples": len(winning_expansions)
                }
            }

        return {}

    def _extract_build_patterns(self) -> Dict:
        """빌드 오더 패턴 추출"""
        build_patterns = defaultdict(list)

        for game in self.games_data:
            result = game["game_result"].get("result", "Unknown")
            build_order = game.get("build_order", [])

            if result == "Victory" and len(build_order) >= 5:
                # 처음 5개 빌드만 추출
                pattern = [
                    f"{b['supply']}_{b['unit_type']}"
                    for b in build_order[:5]
                ]
                pattern_str = " -> ".join(pattern)
                build_patterns[pattern_str].append(game["meta"].get("map_name", "Unknown"))

        # 빈도순 정렬
        sorted_patterns = sorted(build_patterns.items(), key=lambda x: len(x[1]), reverse=True)

        return {
            "successful_patterns": [
                {
                    "pattern": pattern,
                    "frequency": len(maps),
                    "maps": list(set(maps))[:5]  # 최대 5개 맵만
                }
                for pattern, maps in sorted_patterns[:10]  # 상위 10개만
            ]
        }

    def _analyze_engagements(self) -> Dict:
        """교전 분석"""
        total_engagements = 0
        total_supply_lost = 0

        for game in self.games_data:
            engagements = game.get("engagements", [])
            total_engagements += len(engagements)
            total_supply_lost += sum(e.get("supply_lost", 0) for e in engagements)

        avg_loss_per_engagement = total_supply_lost / total_engagements if total_engagements > 0 else 0

        return {
            "total_engagements": total_engagements,
            "avg_supply_lost_per_engagement": round(avg_loss_per_engagement, 1),
            "total_games_analyzed": len(self.games_data)
        }

    def _print_summary(self, knowledge: Dict):
        """분석 결과 요약 출력"""
        print("\n" + "="*60)
        print("KNOWLEDGE BASE UPDATE SUMMARY")
        print("="*60)

        # 맵 통계
        if "map_statistics" in knowledge:
            print("\nMAP STATISTICS:")
            for map_name, stats in knowledge["map_statistics"].items():
                print(f"  {map_name}: {stats['winrate']}% ({stats['wins']}W-{stats['losses']}L)")

        # 타이밍 통계
        if "learned_timings" in knowledge:
            expansions = knowledge["learned_timings"].get("expansion_avg", {})
            if expansions:
                print("\nEXPANSION TIMINGS:")
                for base, timing in expansions.items():
                    print(f"  {base}: {timing['avg']}s (avg)")

        # 교전 통계
        if "engagement_statistics" in knowledge:
            eng_stats = knowledge["engagement_statistics"]
            print(f"\nENGAGEMENTS: {eng_stats['total_engagements']} battles analyzed")
            print(f"  Avg supply lost: {eng_stats['avg_supply_lost_per_engagement']}")

        print("="*60 + "\n")


def main():
    """메인 실행"""
    updater = KnowledgeUpdater()
    updater.load_all_games()
    updater.analyze_and_update()


if __name__ == "__main__":
    main()
