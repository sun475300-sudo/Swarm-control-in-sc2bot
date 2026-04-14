#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parallel Training Runner - 병렬 인스턴스 훈련

각 인스턴스가 다른 종족/난이도 조합으로 동시 훈련.
SC2는 단일 인스턴스만 지원하므로, 순차적 멀티 게임을
빠른 속도로 연속 실행하는 방식으로 병렬화.

GPU 가속 활용 + 빠른 게임 전환.
"""

import sys
import os
import time
import json
import random
import multiprocessing
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))


def _ensure_sc2_path():
    if sys.platform != "win32":
        return
    if "SC2PATH" in os.environ:
        if os.path.exists(os.path.join(os.environ["SC2PATH"], "Versions")):
            return
    for path in ["C:\\Program Files (x86)\\StarCraft II",
                  "C:\\Program Files\\StarCraft II",
                  "D:\\StarCraft II"]:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            return


_ensure_sc2_path()

from sc2 import maps
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

# GPU setup
GPU = False
GPU_NAME = "CPU"
try:
    import torch
    GPU = torch.cuda.is_available()
    if GPU:
        GPU_NAME = torch.cuda.get_device_name(0)
        print(f"[GPU] {GPU_NAME}")
except (ImportError, OSError):
    print("[GPU] Not available, running on CPU")
    torch = None

# Training config
TOTAL_GAMES = 20
MAP_POOL = ["AbyssalReefLE", "AscensiontoAiurLE", "OdysseyLE"]
RACE_POOL = [Race.Protoss, Race.Terran, Race.Zerg]
DIFFICULTY_LADDER = [
    Difficulty.Easy,
    Difficulty.Medium,
    Difficulty.MediumHard,
    Difficulty.Hard,
]


def run_training_game(game_num, total, difficulty_idx=0):
    """Run a single training game with random matchup."""
    map_name = random.choice(MAP_POOL)
    enemy_race = random.choice(RACE_POOL)
    difficulty = DIFFICULTY_LADDER[min(difficulty_idx, len(DIFFICULTY_LADDER) - 1)]
    diff_name = difficulty.name

    print(f"\n{'='*60}")
    print(f"  TRAIN {game_num}/{total} | {map_name} | {enemy_race.name} | {diff_name}")
    print(f"{'='*60}")

    bot = Bot(Race.Zerg, WickedZergBotProImpl(train_mode=True))

    try:
        start = time.time()
        result = run_game(
            maps.get(map_name),
            [bot, Computer(enemy_race, difficulty)],
            realtime=False,
        )
        elapsed = time.time() - start

        won = str(result) == "Result.Victory"
        tag = "WIN" if won else "LOSS"
        print(f"  {tag} in {elapsed:.0f}s | {enemy_race.name} {diff_name}")

        return {
            "game": game_num,
            "map": map_name,
            "race": enemy_race.name,
            "difficulty": diff_name,
            "won": won,
            "time": round(elapsed, 1),
        }
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "game": game_num,
            "map": map_name,
            "race": enemy_race.name,
            "difficulty": diff_name,
            "won": False,
            "error": str(e),
            "time": 0,
        }


def main():
    start_time = time.time()

    print(f"\n{'='*70}")
    print(f"  PARALLEL TRAINING: {TOTAL_GAMES} games")
    print(f"  Maps: {len(MAP_POOL)} | Races: {len(RACE_POOL)}")
    print(f"  Difficulty Ladder: {[d.name for d in DIFFICULTY_LADDER]}")
    print(f"  GPU: {GPU_NAME}")
    print(f"  Mode: Sequential Fast (realtime=False)")
    print(f"{'='*70}\n")

    results = []
    wins = 0
    losses = 0
    streak = 0
    difficulty_idx = 0  # Start at Easy

    for game_num in range(1, TOTAL_GAMES + 1):
        result = run_training_game(game_num, TOTAL_GAMES, difficulty_idx)
        results.append(result)

        if result.get("won"):
            wins += 1
            streak += 1
            # 3연승 시 난이도 상승
            if streak >= 3:
                difficulty_idx = min(difficulty_idx + 1, len(DIFFICULTY_LADDER) - 1)
                print(f"  [LADDER UP] -> {DIFFICULTY_LADDER[difficulty_idx].name}")
                streak = 0
        else:
            losses += 1
            streak = 0
            # 3연패 시 난이도 하락
            recent = results[-3:]
            if len(recent) >= 3 and all(not r.get("won") for r in recent):
                difficulty_idx = max(difficulty_idx - 1, 0)
                print(f"  [LADDER DOWN] -> {DIFFICULTY_LADDER[difficulty_idx].name}")

        elapsed = time.time() - start_time
        wr = wins / max(wins + losses, 1) * 100
        print(f"  [{game_num}/{TOTAL_GAMES}] W:{wins} L:{losses} WR:{wr:.0f}% | "
              f"Diff:{DIFFICULTY_LADDER[difficulty_idx].name} | {elapsed/60:.1f}m")

        time.sleep(2)

    # Final report
    total_time = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"  TRAINING COMPLETE: {TOTAL_GAMES} games in {total_time/60:.1f}min")
    print(f"{'='*70}")
    print(f"  Win Rate: {wins}/{wins+losses} ({wins/max(wins+losses,1)*100:.1f}%)")
    print(f"  Final Difficulty: {DIFFICULTY_LADDER[difficulty_idx].name}")
    print(f"  Avg Game Time: {sum(r.get('time',0) for r in results)/max(len(results),1):.0f}s")

    # Per-race stats
    print(f"\n  --- By Race ---")
    for race in RACE_POOL:
        rr = [r for r in results if r.get("race") == race.name]
        rw = sum(1 for r in rr if r.get("won"))
        print(f"  {race.name:10s}: {rw}/{len(rr)} ({rw/max(len(rr),1)*100:.0f}%)")

    # Save
    report_path = Path(__file__).parent / "training_results.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": TOTAL_GAMES,
            "wins": wins,
            "losses": losses,
            "final_difficulty": DIFFICULTY_LADDER[difficulty_idx].name,
            "games": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved: {report_path}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
