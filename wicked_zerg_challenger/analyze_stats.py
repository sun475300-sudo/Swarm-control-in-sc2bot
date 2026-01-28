import json
import os
from collections import defaultdict

def analyze_stats():
    file_path = r"d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\scripts\training_session_stats.json"
    
    if not os.path.exists(file_path):
        print("Stats file not found.")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    history = data.get("game_history", [])
    if not history:
        print("No game history found.")
        return

    # Initialize counters
    by_race = defaultdict(lambda: {"wins": 0, "total": 0})
    by_difficulty = defaultdict(lambda: {"wins": 0, "total": 0})
    by_map = defaultdict(lambda: {"wins": 0, "total": 0})

    for game in history:
        race = game.get("opponent_race", "Unknown")
        diff = game.get("difficulty", "Unknown")
        map_name = game.get("map_name", "Unknown")
        result = game.get("result", "")

        is_win = "Victory" in result or "Result.Victory" in result
        
        # Breakdown by Race
        by_race[race]["total"] += 1
        if is_win: by_race[race]["wins"] += 1

        # Breakdown by Difficulty
        by_difficulty[diff]["total"] += 1
        if is_win: by_difficulty[diff]["wins"] += 1

        # Breakdown by Map
        by_map[map_name]["total"] += 1
        if is_win: by_map[map_name]["wins"] += 1

    print("\n=== Statistics Breakdown ===")
    print(f"Total Games Analyzed: {len(history)}")

    print("\n[vs Race]")
    for race, stats in sorted(by_race.items()):
        win_rate = (stats["wins"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"  {race:<10}: {stats['wins']:>3}W {stats['total']-stats['wins']:>3}L ({win_rate:.1f}%)")

    print("\n[vs Difficulty]")
    for diff, stats in sorted(by_difficulty.items()):
        win_rate = (stats["wins"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"  {diff:<15}: {stats['wins']:>3}W {stats['total']-stats['wins']:>3}L ({win_rate:.1f}%)")

    print("\n[on Map]")
    for map_name, stats in sorted(by_map.items()):
        win_rate = (stats["wins"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"  {map_name:<20}: {stats['wins']:>3}W {stats['total']-stats['wins']:>3}L ({win_rate:.1f}%)")

if __name__ == "__main__":
    analyze_stats()
