#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
빠른 테스트 - Easy 난이도 20게임 (최적화 검증용)
"""

from sc2 import maps
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty, Result
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl as WickedZergBotPro
import sys
import os
import time
from datetime import datetime


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
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Blizzard Entertainment\StarCraft II")
        install_path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)

        if os.path.exists(install_path):
            os.environ["SC2PATH"] = install_path
            print(f"[SC2] Found via Registry: {install_path}")
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
            print(f"[SC2] Using: {path}")
            return


def run_single_game(game_num, total_games):
    """Run a single game and return result."""
    print("\n" + "=" * 70)
    print(f"  OPTIMIZATION TEST - GAME #{game_num}/{total_games}")
    print("=" * 70)

    # Settings
    map_name = "AbyssalReefLE"
    opponent_race = Race.Protoss
    difficulty = Difficulty.Easy

    print(f"  Map: {map_name}")
    print(f"  Opponent: {opponent_race.name}")
    print(f"  Difficulty: {difficulty.name}")
    print("=" * 70)
    print()

    # Create bot (train_mode=False for testing)
    bot = Bot(Race.Zerg, WickedZergBotPro(train_mode=False))

    # Run game
    try:
        map_instance = maps.get(map_name)
        if map_instance is None:
            print(f"[ERROR] Map '{map_name}' not found!")
            return None

        result = run_game(
            map_instance,
            [bot, Computer(opponent_race, difficulty)],
            realtime=False
        )

        # Get result
        if result is not None:
            is_victory = (result == Result.Victory)
            print(f"\n[RESULT] Game #{game_num}: {'WIN' if is_victory else 'LOSS'}")
            return is_victory
        else:
            print(f"\n[RESULT] Game #{game_num}: UNKNOWN")
            return None

    except Exception as e:
        print(f"[ERROR] Game #{game_num} failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run quick optimization test."""
    _ensure_sc2_path()

    # Test configuration
    total_games = 20
    target_win_rate = 90.0

    print("\n" + "=" * 70)
    print("  OPTIMIZATION VERIFICATION TEST")
    print("=" * 70)
    print(f"  Difficulty: Easy")
    print(f"  Total Games: {total_games}")
    print(f"  Target Win Rate: {target_win_rate}%+")
    print()
    print("  New Features:")
    print("  - Logic Optimizer (47 systems -> 28 active avg)")
    print("  - Unit Authority Manager (conflict resolution)")
    print("  - Map Memory System (full map awareness)")
    print("=" * 70)
    print()

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

        print("\n" + "-" * 70)
        print(f"  Game Duration: {game_duration:.1f}s")
        print(f"  Current Score: {wins}W - {losses}L - {errors}E")
        print(f"  Win Rate: {win_rate:.1f}% (Target: {target_win_rate}%)")
        print(f"  Total Time: {total_duration/60:.1f} min")

        # Check if target achieved early
        if win_rate >= target_win_rate and total_completed >= 10:
            print(f"  STATUS: Target achieved with {total_completed} games!")
        elif total_completed >= 10:
            diff = target_win_rate - win_rate
            print(f"  STATUS: {diff:.1f}% away from target")

        print("-" * 70)
        print()

        # Short delay between games
        time.sleep(1)

    total_duration = time.time() - start_time
    total_completed = wins + losses
    final_win_rate = (wins / total_completed * 100) if total_completed > 0 else 0

    # Final report
    print("\n" + "=" * 70)
    print("  FINAL RESULTS")
    print("=" * 70)
    print(f"  Score: {wins}W - {losses}L - {errors}E")
    print(f"  Win Rate: {final_win_rate:.1f}%")
    print(f"  Target: {target_win_rate}%")
    print(f"  Total Time: {total_duration/60:.1f} minutes")
    print(f"  Avg Game Time: {total_duration/max(total_completed, 1):.1f}s")
    print("-" * 70)

    if final_win_rate >= target_win_rate:
        print(f"  STATUS: SUCCESS - Target achieved!")
        print(f"  Ready for next difficulty: Medium")
    else:
        diff = target_win_rate - final_win_rate
        print(f"  STATUS: INCOMPLETE - {diff:.1f}% away from target")
        print(f"  Action: Further optimization needed")

    print("=" * 70)

    # Save timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[TEST COMPLETE] {timestamp}")


if __name__ == "__main__":
    main()
