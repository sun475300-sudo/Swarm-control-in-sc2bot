#!/usr/bin/env python3
"""
빠른 테스트 - Easy 난이도 20게임 (최적화 검증용)
"""

import logging
import os
import sys
import time
from datetime import datetime

from sc2 import maps
from sc2.data import Difficulty, Race, Result
from sc2.main import run_game
from sc2.player import Bot, Computer
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl as WickedZergBotPro

logger = logging.getLogger("QuickTest")


def _ensure_sc2_path():
    """Set SC2PATH environment variable."""
    if sys.platform != "win32":
        return

    if "SC2PATH" in os.environ:
        sc2_path = os.environ["SC2PATH"]
        versions_dir = os.path.join(sc2_path, "Versions")
        if os.path.exists(versions_dir):
            return

    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Blizzard Entertainment\StarCraft II"
        )
        install_path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)

        if os.path.exists(install_path):
            os.environ["SC2PATH"] = install_path
            logger.info(f"Found via Registry: {install_path}")
            return
    except Exception:
        pass

    common_paths = [
        "C:\\Program Files (x86)\\StarCraft II",
        "C:\\Program Files\\StarCraft II",
        "D:\\StarCraft II",
    ]
    for path in common_paths:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            logger.info(f"Using: {path}")
            return


def run_single_game(game_num, total_games):
    """Run a single game and return result."""
    logger.info("\n" + "=" * 70)
    logger.info(f"  OPTIMIZATION TEST - GAME #{game_num}/{total_games}")
    logger.info("=" * 70)

    # Settings
    map_name = "AbyssalReefLE"
    opponent_race = Race.Protoss
    difficulty = Difficulty.Easy

    logger.info(f"  Map: {map_name}")
    logger.info(f"  Opponent: {opponent_race.name}")
    logger.info(f"  Difficulty: {difficulty.name}")
    logger.info("=" * 70)
    # Create bot (train_mode=False for testing)
    bot = Bot(Race.Zerg, WickedZergBotPro(train_mode=False))

    # Run game
    try:
        map_instance = maps.get(map_name)
        if map_instance is None:
            logger.error(f"Map '{map_name}' not found!")
            return None

        result = run_game(
            map_instance, [bot, Computer(opponent_race, difficulty)], realtime=False
        )

        # Get result
        if result is not None:
            is_victory = result == Result.Victory
            logger.info(
                f"\n[RESULT] Game #{game_num}: {'WIN' if is_victory else 'LOSS'}"
            )
            return is_victory
        else:
            logger.info(f"\n[RESULT] Game #{game_num}: UNKNOWN")
            return None

    except Exception as e:
        logger.error(f"Game #{game_num} failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Run quick optimization test."""
    _ensure_sc2_path()

    # Test configuration
    total_games = 20
    target_win_rate = 90.0

    logger.info("\n" + "=" * 70)
    logger.info("  OPTIMIZATION VERIFICATION TEST")
    logger.info("=" * 70)
    logger.info("  Difficulty: Easy")
    logger.info(f"  Total Games: {total_games}")
    logger.info(f"  Target Win Rate: {target_win_rate}%+")
    logger.info("  New Features:")
    logger.info("  - Logic Optimizer (47 systems -> 28 active avg)")
    logger.info("  - Unit Authority Manager (conflict resolution)")
    logger.info("  - Map Memory System (full map awareness)")
    logger.info("=" * 70)
    wins = 0
    losses = 0
    errors = 0

    start_time = time.time()

    for game_num in range(1, total_games + 1):
        game_start = time.time()

        result = run_single_game(game_num, total_games)

        if result is True:
            wins += 1
        elif result is False:
            losses += 1
        else:
            errors += 1

        game_duration = time.time() - game_start
        total_duration = time.time() - start_time

        # Calculate current win rate
        total_completed = wins + losses
        win_rate = (wins / total_completed * 100) if total_completed > 0 else 0

        logger.info("\n" + "-" * 70)
        logger.info(f"  Game Duration: {game_duration:.1f}s")
        logger.error(f"  Current Score: {wins}W - {losses}L - {errors}E")
        logger.info(f"  Win Rate: {win_rate:.1f}% (Target: {target_win_rate}%)")
        logger.info(f"  Total Time: {total_duration/60:.1f} min")

        # Check if target achieved early
        if win_rate >= target_win_rate and total_completed >= 10:
            logger.info(f"  STATUS: Target achieved with {total_completed} games!")
        elif total_completed >= 10:
            diff = target_win_rate - win_rate
            logger.info(f"  STATUS: {diff:.1f}% away from target")

        logger.info("-" * 70)
        # Short delay between games
        time.sleep(1)

    total_duration = time.time() - start_time
    total_completed = wins + losses
    final_win_rate = (wins / total_completed * 100) if total_completed > 0 else 0

    # Final report
    logger.info("\n" + "=" * 70)
    logger.info("  FINAL RESULTS")
    logger.info("=" * 70)
    logger.error(f"  Score: {wins}W - {losses}L - {errors}E")
    logger.info(f"  Win Rate: {final_win_rate:.1f}%")
    logger.info(f"  Target: {target_win_rate}%")
    logger.info(f"  Total Time: {total_duration/60:.1f} minutes")
    logger.info(f"  Avg Game Time: {total_duration/max(total_completed, 1):.1f}s")
    logger.info("-" * 70)

    if final_win_rate >= target_win_rate:
        logger.info("  STATUS: SUCCESS - Target achieved!")
        logger.info("  Ready for next difficulty: Medium")
    else:
        diff = target_win_rate - final_win_rate
        logger.info(f"  STATUS: INCOMPLETE - {diff:.1f}% away from target")
        logger.info("  Action: Further optimization needed")

    logger.info("=" * 70)

    # Save timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"\n[TEST COMPLETE] {timestamp}")


if __name__ == "__main__":
    main()
