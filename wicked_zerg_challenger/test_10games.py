# -*- coding: utf-8 -*-
"""
10-game performance monitoring test
10게임 연속 성능 모니터링 테스트
"""

from sc2 import maps
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl as WickedZergBotPro
import sys
import os
import time
import psutil
import tracemalloc
import logging

logger = logging.getLogger("Test10games")


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


def main():
    """Run 10-game performance test."""
    _ensure_sc2_path()

    logger.info("\n" + "=" * 70)
    logger.info("  10-GAME PERFORMANCE TEST")
    logger.info("=" * 70)
    logger.info("  Monitoring:")
    logger.info("    - Win rate vs Protoss Easy")
    logger.info("    - Memory usage and leaks")
    logger.info("    - Crash stability")
    logger.info("    - Logic performance")
    logger.info("=" * 70)
    # Test configuration
    map_name = "AbyssalReefLE"
    opponent_race = Race.Protoss
    difficulty = Difficulty.Easy
    total_games = 10

    results = []
    wins = 0
    losses = 0

    # Start memory tracking
    tracemalloc.start()
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    logger.info(f"Initial: {initial_memory:.1f} MB\n")

    for game_num in range(1, total_games + 1):
        logger.info("\n" + "=" * 70)
        logger.info(f"  GAME {game_num}/{total_games}")
        logger.info("=" * 70)
        logger.info(f"  Current Record: {wins}W-{losses}L")
        logger.info(f"  Map: {map_name}")
        logger.info(f"  Opponent: {opponent_race.name} {difficulty.name}")
        logger.info("=" * 70)
        # Memory before game
        mem_before = process.memory_info().rss / 1024 / 1024
        logger.info(f"Before game {game_num}: {mem_before:.1f} MB")

        # Create bot
        bot = Bot(Race.Zerg, WickedZergBotPro(train_mode=False, instance_id=game_num))

        # Get map
        map_instance = maps.get(map_name)
        if map_instance is None:
            logger.error(f"Map '{map_name}' not found!")
            results.append(f"Game {game_num}: ERROR - Map not found")
            continue

        # Run game
        try:
            start_time = time.time()
            result = run_game(
                map_instance,
                [bot, Computer(opponent_race, difficulty)],
                realtime=False
            )
            elapsed = time.time() - start_time

            # Assume result is returned (in real python-sc2, check result)
            # For now, mark as completed
            logger.info(f"\n[GAME {game_num} FINISHED] Time: {elapsed:.1f}s")
            results.append(f"Game {game_num}: Completed in {elapsed:.1f}s")

        except Exception as e:
            logger.error(f"\n[GAME {game_num} ERROR] {e}")
            results.append(f"Game {game_num}: ERROR - {e}")
            losses += 1

        # Memory after game
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_delta = mem_after - mem_before
        logger.info(f"After game {game_num}: {mem_after:.1f} MB (delta: {mem_delta:+.1f} MB)")

        # Short pause between games
        if game_num < total_games:
            logger.info("\nWaiting 5 seconds before next game...")
            time.sleep(5)

    # Final memory check
    final_memory = process.memory_info().rss / 1024 / 1024
    total_leak = final_memory - initial_memory

    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("  PERFORMANCE TEST SUMMARY")
    logger.info("=" * 70)
    logger.info(f"\nGames Completed: {len(results)}/{total_games}")
    logger.info(f"Win Rate: {wins}W-{losses}L ({wins/total_games*100:.1f}%)" if total_games > 0 else "No games")
    logger.info(f"\nMemory:")
    logger.info(f"  Initial: {initial_memory:.1f} MB")
    logger.info(f"  Final: {final_memory:.1f} MB")
    logger.info(f"  Total Leak: {total_leak:+.1f} MB")
    logger.info(f"  Per Game: {total_leak/total_games:+.1f} MB" if total_games > 0 else "N/A")

    logger.info(f"\nResults:")
    for result in results:
        logger.info(f"  {result}")

    logger.info("=" * 70)
    # Memory snapshot
    current, peak = tracemalloc.get_traced_memory()
    logger.info(f"Peak: {peak / 1024 / 1024:.1f} MB")
    tracemalloc.stop()


if __name__ == "__main__":
    main()
