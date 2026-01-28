# -*- coding: utf-8 -*-
"""
Game Statistics - 맵/난이도/종족별 승률 통계
"""

import json
from pathlib import Path
from datetime import datetime
from sc2.data import Race, Difficulty


class GameStatistics:
    """게임 통계 관리"""

    def __init__(self, stats_file="game_stats.json"):
        self.stats_file = Path(stats_file)
        self.stats = self.load_stats()

    def load_stats(self):
        """통계 로드"""
        if self.stats_file.exists():
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "total_games": 0,
                "total_wins": 0,
                "total_losses": 0,
                "by_map": {},
                "by_difficulty": {},
                "by_race": {},
                "by_map_difficulty": {},
                "by_map_race": {},
                "games": []
            }

    def save_stats(self):
        """통계 저장"""
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)

    def record_game(self, map_name: str, difficulty: str, enemy_race: str, victory: bool):
        """게임 결과 기록"""
        # 전체 통계
        self.stats["total_games"] += 1
        if victory:
            self.stats["total_wins"] += 1
        else:
            self.stats["total_losses"] += 1

        # 맵별 통계
        if map_name not in self.stats["by_map"]:
            self.stats["by_map"][map_name] = {"wins": 0, "losses": 0}
        if victory:
            self.stats["by_map"][map_name]["wins"] += 1
        else:
            self.stats["by_map"][map_name]["losses"] += 1

        # 난이도별 통계
        if difficulty not in self.stats["by_difficulty"]:
            self.stats["by_difficulty"][difficulty] = {"wins": 0, "losses": 0}
        if victory:
            self.stats["by_difficulty"][difficulty]["wins"] += 1
        else:
            self.stats["by_difficulty"][difficulty]["losses"] += 1

        # 종족별 통계
        if enemy_race not in self.stats["by_race"]:
            self.stats["by_race"][enemy_race] = {"wins": 0, "losses": 0}
        if victory:
            self.stats["by_race"][enemy_race]["wins"] += 1
        else:
            self.stats["by_race"][enemy_race]["losses"] += 1

        # 맵+난이도 통계
        map_diff_key = f"{map_name}_{difficulty}"
        if map_diff_key not in self.stats["by_map_difficulty"]:
            self.stats["by_map_difficulty"][map_diff_key] = {"wins": 0, "losses": 0}
        if victory:
            self.stats["by_map_difficulty"][map_diff_key]["wins"] += 1
        else:
            self.stats["by_map_difficulty"][map_diff_key]["losses"] += 1

        # 맵+종족 통계
        map_race_key = f"{map_name}_{enemy_race}"
        if map_race_key not in self.stats["by_map_race"]:
            self.stats["by_map_race"][map_race_key] = {"wins": 0, "losses": 0}
        if victory:
            self.stats["by_map_race"][map_race_key]["wins"] += 1
        else:
            self.stats["by_map_race"][map_race_key]["losses"] += 1

        # 게임 상세 기록
        self.stats["games"].append({
            "timestamp": datetime.now().isoformat(),
            "map": map_name,
            "difficulty": difficulty,
            "enemy_race": enemy_race,
            "result": "Victory" if victory else "Defeat"
        })

        # 최근 100게임만 유지
        if len(self.stats["games"]) > 100:
            self.stats["games"] = self.stats["games"][-100:]

        self.save_stats()

    def print_statistics(self):
        """통계 출력"""
        print("\n" + "="*80)
        print("GAME STATISTICS")
        print("="*80)

        # 전체 통계
        total = self.stats["total_games"]
        wins = self.stats["total_wins"]
        losses = self.stats["total_losses"]
        win_rate = (wins / total * 100) if total > 0 else 0

        print(f"\nTotal Games: {total}")
        print(f"Wins: {wins} | Losses: {losses}")
        print(f"Overall Win Rate: {win_rate:.1f}%")

        # 맵별 통계
        print("\n" + "-"*80)
        print("BY MAP:")
        print("-"*80)
        for map_name, stats in sorted(self.stats["by_map"].items()):
            total_map = stats["wins"] + stats["losses"]
            wr = (stats["wins"] / total_map * 100) if total_map > 0 else 0
            print(f"  {map_name:30} | {stats['wins']:3}W {stats['losses']:3}L ({wr:5.1f}%)")

        # 난이도별 통계
        print("\n" + "-"*80)
        print("BY DIFFICULTY:")
        print("-"*80)
        for diff, stats in sorted(self.stats["by_difficulty"].items()):
            total_diff = stats["wins"] + stats["losses"]
            wr = (stats["wins"] / total_diff * 100) if total_diff > 0 else 0
            print(f"  {diff:20} | {stats['wins']:3}W {stats['losses']:3}L ({wr:5.1f}%)")

        # 종족별 통계
        print("\n" + "-"*80)
        print("BY ENEMY RACE:")
        print("-"*80)
        for race, stats in sorted(self.stats["by_race"].items()):
            total_race = stats["wins"] + stats["losses"]
            wr = (stats["wins"] / total_race * 100) if total_race > 0 else 0
            print(f"  vs {race:15} | {stats['wins']:3}W {stats['losses']:3}L ({wr:5.1f}%)")

        # 맵+난이도 통계
        print("\n" + "-"*80)
        print("BY MAP + DIFFICULTY:")
        print("-"*80)
        for key, stats in sorted(self.stats["by_map_difficulty"].items()):
            total_md = stats["wins"] + stats["losses"]
            wr = (stats["wins"] / total_md * 100) if total_md > 0 else 0
            print(f"  {key:40} | {stats['wins']:3}W {stats['losses']:3}L ({wr:5.1f}%)")

        # 맵+종족 통계
        print("\n" + "-"*80)
        print("BY MAP + RACE:")
        print("-"*80)
        for key, stats in sorted(self.stats["by_map_race"].items()):
            total_mr = stats["wins"] + stats["losses"]
            wr = (stats["wins"] / total_mr * 100) if total_mr > 0 else 0
            print(f"  {key:40} | {stats['wins']:3}W {stats['losses']:3}L ({wr:5.1f}%)")

        print("="*80 + "\n")
