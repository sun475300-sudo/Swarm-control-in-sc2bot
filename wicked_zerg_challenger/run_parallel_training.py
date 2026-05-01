#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parallel Training Runner - 병렬 인스턴스 훈련

각 인스턴스가 다른 종족/난이도 조합으로 동시 훈련.
SC2는 단일 인스턴스만 지원하므로, 순차적 멀티 게임을
빠른 속도로 연속 실행하는 방식으로 병렬화.

GPU 가속 활용 + 빠른 게임 전환.
"""

import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("RunParallelTraining")

sys.path.insert(0, str(Path(__file__).parent))


def _ensure_sc2_path():
    if sys.platform != "win32":
        return
    if "SC2PATH" in os.environ:
        if os.path.exists(os.path.join(os.environ["SC2PATH"], "Versions")):
            return
    for path in [
        "C:\\Program Files (x86)\\StarCraft II",
        "C:\\Program Files\\StarCraft II",
        "D:\\StarCraft II",
    ]:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            return


_ensure_sc2_path()

# Imports below must come after _ensure_sc2_path() so the SC2PATH env var is
# set before sc2's package-level resolution kicks in.
from sc2 import maps  # noqa: E402
from sc2.data import Difficulty, Race  # noqa: E402
from sc2.main import run_game  # noqa: E402
from sc2.player import Bot, Computer  # noqa: E402
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl  # noqa: E402

# GPU setup
GPU = False
GPU_NAME = "CPU"
try:
    import torch

    GPU = torch.cuda.is_available()
    if GPU:
        GPU_NAME = torch.cuda.get_device_name(0)
        logger.info(f"{GPU_NAME}")
except (ImportError, OSError):
    logger.info("Not available, running on CPU")
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

    logger.info(f"\n{'='*60}")
    logger.info(
        f"  TRAIN {game_num}/{total} | {map_name} | {enemy_race.name} | {diff_name}"
    )
    logger.info(f"{'='*60}")

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
        logger.info(f"  {tag} in {elapsed:.0f}s | {enemy_race.name} {diff_name}")

        return {
            "game": game_num,
            "map": map_name,
            "race": enemy_race.name,
            "difficulty": diff_name,
            "won": won,
            "time": round(elapsed, 1),
        }
    except Exception as e:
        logger.error(f"  ERROR: {e}")
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

    logger.info(f"\n{'='*70}")
    logger.info(f"  PARALLEL TRAINING: {TOTAL_GAMES} games")
    logger.info(f"  Maps: {len(MAP_POOL)} | Races: {len(RACE_POOL)}")
    logger.info(f"  Difficulty Ladder: {[d.name for d in DIFFICULTY_LADDER]}")
    logger.info(f"  GPU: {GPU_NAME}")
    logger.info("  Mode: Sequential Fast (realtime=False)")
    logger.info(f"{'='*70}\n")

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
                logger.info(
                    f"  [LADDER UP] -> {DIFFICULTY_LADDER[difficulty_idx].name}"
                )
                streak = 0
        else:
            losses += 1
            streak = 0
            # 3연패 시 난이도 하락
            recent = results[-3:]
            if len(recent) >= 3 and all(not r.get("won") for r in recent):
                difficulty_idx = max(difficulty_idx - 1, 0)
                logger.info(
                    f"  [LADDER DOWN] -> {DIFFICULTY_LADDER[difficulty_idx].name}"
                )

        elapsed = time.time() - start_time
        wr = wins / max(wins + losses, 1) * 100
        logger.info(
            f"  [{game_num}/{TOTAL_GAMES}] W:{wins} L:{losses} WR:{wr:.0f}% | "
            f"Diff:{DIFFICULTY_LADDER[difficulty_idx].name} | {elapsed/60:.1f}m"
        )

        time.sleep(2)

    # Final report
    total_time = time.time() - start_time
    logger.info(f"\n{'='*70}")
    logger.info(f"  TRAINING COMPLETE: {TOTAL_GAMES} games in {total_time/60:.1f}min")
    logger.info(f"{'='*70}")
    logger.info(
        f"  Win Rate: {wins}/{wins+losses} ({wins/max(wins+losses,1)*100:.1f}%)"
    )
    logger.info(f"  Final Difficulty: {DIFFICULTY_LADDER[difficulty_idx].name}")
    logger.info(
        f"  Avg Game Time: {sum(r.get('time',0) for r in results)/max(len(results),1):.0f}s"
    )

    # Per-race stats
    logger.info("\n  --- By Race ---")
    for race in RACE_POOL:
        rr = [r for r in results if r.get("race") == race.name]
        rw = sum(1 for r in rr if r.get("won"))
        logger.info(f"  {race.name:10s}: {rw}/{len(rr)} ({rw/max(len(rr),1)*100:.0f}%)")

    # Save
    report_path = Path(__file__).parent / "training_results.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "total": TOTAL_GAMES,
                "wins": wins,
                "losses": losses,
                "final_difficulty": DIFFICULTY_LADDER[difficulty_idx].name,
                "games": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    logger.info(f"\n  Saved: {report_path}")
    logger.info(f"{'='*70}")


if __name__ == "__main__":
    main()
