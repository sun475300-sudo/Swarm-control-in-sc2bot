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
import argparse
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

# CLI parsing should not require the SC2 runtime stack (mpyq/run_game),
# so heavy imports are deferred to `main()` / `run_single_test()`.
from sc2.data import Difficulty, Race

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

RACE_BY_NAME = {
    "Terran": Race.Terran,
    "Protoss": Race.Protoss,
    "Zerg": Race.Zerg,
}

DIFFICULTY_BY_NAME = {
    "VeryEasy": Difficulty.VeryEasy,
    "Easy": Difficulty.Easy,
    "Medium": Difficulty.Medium,
    "MediumHard": Difficulty.MediumHard,
    "Hard": Difficulty.Hard,
    "Harder": Difficulty.Harder,
    "VeryHard": Difficulty.VeryHard,
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run SC2 mass benchmark games")
    parser.add_argument(
        "--opponent",
        choices=sorted(RACE_BY_NAME),
        help="Filter to one opponent race",
    )
    parser.add_argument(
        "--difficulty",
        choices=sorted(DIFFICULTY_BY_NAME),
        help="Filter to one AI difficulty",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=None,
        help="Number of games for the selected matchup",
    )
    parser.add_argument(
        "--maps",
        default=",".join(MAPS),
        help="Comma-separated map list to rotate through",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated matrix without launching SC2",
    )
    return parser.parse_args(argv)


def build_test_cases(args):
    selected_maps = [m.strip() for m in args.maps.split(",") if m.strip()]
    if not selected_maps:
        selected_maps = list(MAPS)

    selected_races = (
        [RACE_BY_NAME[args.opponent]] if args.opponent else list(RACES)
    )
    selected_difficulties = (
        [(DIFFICULTY_BY_NAME[args.difficulty], args.difficulty)]
        if args.difficulty
        else list(DIFFICULTIES)
    )

    if args.games is not None:
        test_cases = []
        games = max(0, args.games)
        for race in selected_races:
            for difficulty, diff_name in selected_difficulties:
                for index in range(games):
                    map_name = selected_maps[index % len(selected_maps)]
                    test_cases.append((map_name, race, difficulty, diff_name))
        return test_cases

    test_cases = []
    for map_name in selected_maps:
        for race in selected_races:
            for difficulty, diff_name in selected_difficulties:
                for _ in range(GAMES_PER_MATCHUP):
                    test_cases.append((map_name, race, difficulty, diff_name))
    return test_cases


def run_single_test(map_name, race, difficulty, diff_name, game_num, total):
    """Run a single test game."""
    # Deferred imports — these pull in mpyq/run_game and are only needed
    # when actually launching a match.
    from sc2 import maps
    from sc2.main import run_game
    from sc2.player import Bot, Computer
    from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

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
        logger.info(f"  Result: {result_str} | Time: {elapsed:.1f}s")

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


def main(argv=None):
    args = parse_args(argv)
    start_time = time.time()

    test_cases = build_test_cases(args)

    total = len(test_cases)
    logger.info(f"\n{'='*70}")
    logger.info(f"  MASS TEST: {total} games")
    logger.info(
        f"  Maps: {len(set(case[0] for case in test_cases))} | "
        f"Races: {len(set(case[1] for case in test_cases))} | "
        f"Difficulties: {len(set(case[3] for case in test_cases))}"
    )
    logger.info(
        f"  GPU: {'YES - ' + torch.cuda.get_device_name(0) if GPU_AVAILABLE else 'CPU only'}"
    )
    logger.info(f"{'='*70}\n")

    if args.dry_run:
        for i, (map_name, race, _difficulty, diff_name) in enumerate(test_cases, 1):
            logger.info("  DRY %02d/%02d: %s vs %s %s", i, total, map_name, race.name, diff_name)
        logger.info("  Dry run complete; no SC2 games launched.")
        return

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
            f"  Progress: {i}/{total} | W:{wins} L:{losses} E:{errors} | WR:{wr:.0f}% | Time:{elapsed/60:.1f}m"
        )

        time.sleep(2)

    # Final summary
    total_time = time.time() - start_time
    logger.info(f"\n{'='*70}")
    logger.info(f"  MASS TEST COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"  Total Games: {total}")
    logger.error(f"  Results: {wins}W / {losses}L / {errors}E")
    if wins + losses > 0:
        logger.info(f"  Win Rate: {wins/(wins+losses)*100:.1f}%")
    logger.info(f"  Total Time: {total_time/60:.1f} minutes")
    logger.info(f"  Avg Time/Game: {total_time/max(len(results),1):.1f}s")

    # Per-difficulty breakdown
    logger.info(f"\n  --- By Difficulty ---")
    for _, diff_name in DIFFICULTIES:
        d_results = [r for r in results if r.get("difficulty") == diff_name]
        d_wins = sum(1 for r in d_results if r.get("won"))
        d_total = sum(1 for r in d_results if r.get("result") != "error")
        wr = d_wins / max(d_total, 1) * 100
        logger.info(f"  {diff_name:12s}: {d_wins}W/{d_total-d_wins}L ({wr:.0f}%)")

    # Per-race breakdown
    logger.info(f"\n  --- By Race ---")
    for race in RACES:
        r_results = [r for r in results if r.get("race") == race.name]
        r_wins = sum(1 for r in r_results if r.get("won"))
        r_total = sum(1 for r in r_results if r.get("result") != "error")
        wr = r_wins / max(r_total, 1) * 100
        logger.info(f"  {race.name:12s}: {r_wins}W/{r_total-r_wins}L ({wr:.0f}%)")

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
