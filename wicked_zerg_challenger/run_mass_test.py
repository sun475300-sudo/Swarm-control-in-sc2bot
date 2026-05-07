#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mass Testing Script - 난이도/종족별 대규모 인게임 테스트

All difficulties x All races = comprehensive test matrix
GPU acceleration enabled for all computations.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("RunMassTest")

sys.path.insert(0, str(Path(__file__).parent))


# SC2 path auto-setup
def _ensure_sc2_path():
    if sys.platform != "win32":
        return
    if "SC2PATH" in os.environ:
        if os.path.exists(os.path.join(os.environ["SC2PATH"], "Versions")):
            return
    common_paths = [
        "C:\\Program Files (x86)\\StarCraft II",
        "C:\\Program Files\\StarCraft II",
        "D:\\StarCraft II",
    ]
    for path in common_paths:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            return


_ensure_sc2_path()

from sc2 import maps
from sc2.data import Difficulty, Race
from sc2.main import run_game
from sc2.player import Bot, Computer
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

# GPU setup
try:
    import torch

    GPU_AVAILABLE = torch.cuda.is_available()
    if GPU_AVAILABLE:
        torch.set_default_device("cuda")
        logger.info(f"{torch.cuda.get_device_name(0)} - CUDA {torch.version.cuda}")
except ImportError:
    GPU_AVAILABLE = False

# Test matrix
MAPS = ["AbyssalReefLE", "AscensiontoAiurLE", "OdysseyLE"]
RACES = [Race.Protoss, Race.Terran, Race.Zerg]
DIFFICULTIES = [
    (Difficulty.VeryEasy, "VeryEasy"),
    (Difficulty.Easy, "Easy"),
    (Difficulty.Medium, "Medium"),
    (Difficulty.MediumHard, "MediumHard"),
]

GAMES_PER_MATCHUP = 1  # 1 game per combination = 36 total games


def run_single_test(map_name, race, difficulty, diff_name, game_num, total):
    """Run a single test game."""
    race_name = race.name
    logger.info(f"\n{'='*60}")
    logger.info(f"  GAME {game_num}/{total}")
    logger.info(f"  Map: {map_name} | Race: {race_name} | Difficulty: {diff_name}")
    logger.info(f"{'='*60}")

    bot = Bot(Race.Zerg, WickedZergBotProImpl(train_mode=False))

    try:
        map_instance = maps.get(map_name)
        if map_instance is None:
            logger.error(f"  [ERROR] Map '{map_name}' not found!")
            return {"result": "error", "error": "map_not_found"}

        start = time.time()
        result = run_game(
            map_instance, [bot, Computer(race, difficulty)], realtime=False
        )
        elapsed = time.time() - start

        won = str(result) == "Result.Victory"
        result_str = "WIN" if won else "LOSS"
        logger.info("  Result: {result_str} | Time: {elapsed:.1f}s")

        return {
            "result": result_str,
            "map": map_name,
            "race": race_name,
            "difficulty": diff_name,
            "time_seconds": round(elapsed, 1),
            "won": won,
        }
    except Exception as e:
        logger.error(f"  [ERROR] {e}")
        return {
            "result": "error",
            "map": map_name,
            "race": race_name,
            "difficulty": diff_name,
            "error": str(e),
            "won": False,
        }


def main():
    start_time = time.time()

    # Build test matrix
    test_cases = []
    for map_name in MAPS:
        for race in RACES:
            for difficulty, diff_name in DIFFICULTIES:
                for _ in range(GAMES_PER_MATCHUP):
                    test_cases.append((map_name, race, difficulty, diff_name))

    total = len(test_cases)
    logger.info(f"\n{'='*70}")
    logger.info(f"  MASS TEST: {total} games")
    logger.info(
        f"  Maps: {len(MAPS)} | Races: {len(RACES)} | Difficulties: {len(DIFFICULTIES)}"
    )
    logger.info(
        f"  GPU: {'YES - ' + torch.cuda.get_device_name(0) if GPU_AVAILABLE else 'CPU only'}"
    )
    logger.info(f"{'='*70}\n")

    results = []
    wins = 0
    losses = 0
    errors = 0

    for i, (map_name, race, difficulty, diff_name) in enumerate(test_cases, 1):
        result = run_single_test(map_name, race, difficulty, diff_name, i, total)
        results.append(result)

        if result.get("won"):
            wins += 1
        elif result.get("result") == "error":
            errors += 1
        else:
            losses += 1

        # Progress
        elapsed = time.time() - start_time
        wr = wins / max(wins + losses, 1) * 100
        logger.error(
            "  Progress: {i}/{total} | W:{wins} L:{losses} E:{errors} | WR:{wr:.0f}% | Time:{elapsed/60:.1f}m"
        )

        time.sleep(2)

    # Final summary
    total_time = time.time() - start_time
    logger.info(f"\n{'='*70}")
    logger.info("  MASS TEST COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"  Total Games: {total}")
    logger.error(f"  Results: {wins}W / {losses}L / {errors}E")
    if wins + losses > 0:
        logger.info("  Win Rate: {wins/(wins+losses)*100:.1f}%")
    logger.info("  Total Time: {total_time/60:.1f} minutes")
    logger.info("  Avg Time/Game: {total_time/max(len(results),1):.1f}s")

    # Per-difficulty breakdown
    logger.info("\n  --- By Difficulty ---")
    for _, diff_name in DIFFICULTIES:
        d_results = [r for r in results if r.get("difficulty") == diff_name]
        d_wins = sum(1 for r in d_results if r.get("won"))
        d_total = sum(1 for r in d_results if r.get("result") != "error")
        wr = d_wins / max(d_total, 1) * 100
        logger.info("  {diff_name:12s}: {d_wins}W/{d_total-d_wins}L ({wr:.0f}%)")

    # Per-race breakdown
    logger.info("\n  --- By Race ---")
    for race in RACES:
        r_results = [r for r in results if r.get("race") == race.name]
        r_wins = sum(1 for r in r_results if r.get("won"))
        r_total = sum(1 for r in r_results if r.get("result") != "error")
        wr = r_wins / max(r_total, 1) * 100
        logger.info("  {race.name:12s}: {r_wins}W/{r_total-r_wins}L ({wr:.0f}%)")

    logger.info(f"{'='*70}")

    # Save results to JSON
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_games": total,
        "wins": wins,
        "losses": losses,
        "errors": errors,
        "win_rate": wins / max(wins + losses, 1) * 100,
        "total_time_minutes": round(total_time / 60, 1),
        "gpu": torch.cuda.get_device_name(0) if GPU_AVAILABLE else "CPU",
        "games": results,
    }

    report_path = Path(__file__).parent / "mass_test_results.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"\n  Results saved to: {report_path}")


if __name__ == "__main__":
    main()
