"""
Run 3 games for testing improvements.
개선 사항 테스트를 위한 3게임 실행 스크립트.
"""

import logging
import os
import sys
import time

from sc2 import maps
from sc2.data import Difficulty, Race
from sc2.main import run_game
from sc2.player import Bot, Computer
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl as WickedZergBotPro

logger = logging.getLogger("Test3games")


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


def main():
    """Run 3 test games."""
    _ensure_sc2_path()

    logger.info("\n" + "=" * 70)
    logger.info("  3-GAME TEST SESSION")
    logger.info("=" * 70)
    logger.info("  Testing improvements:")
    logger.info("    [OK] Creep expansion system (target: 3min=5, 5min=15 tumors)")
    logger.error("    [OK] is_flying error fixes")
    logger.info("    [OK] Emergency Zergling trigger optimization")
    logger.info("    [OK] Expansion timing improvements")
    logger.error("    [OK] Curriculum manager error fixes")
    logger.info("=" * 70)
    # Test configuration (using available maps)
    map_pool = ["AbyssalReefLE", "AbyssalReefLE", "AbyssalReefLE"]
    opponent_races = [Race.Protoss, Race.Terran, Race.Zerg]
    difficulty = Difficulty.Easy

    results = []

    for game_num in range(1, 4):
        logger.info("\n" + "=" * 70)
        logger.info(f"  GAME {game_num}/3")
        logger.info("=" * 70)

        map_name = map_pool[(game_num - 1) % len(map_pool)]
        opponent_race = opponent_races[(game_num - 1) % len(opponent_races)]

        logger.info(f"  Map: {map_name}")
        logger.info(f"  Opponent: {opponent_race.name}")
        logger.info(f"  Difficulty: {difficulty.name}")
        logger.info("=" * 70)
        # Create bot with training mode disabled for pure testing
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
                realtime=False,  # Fast mode
            )
            elapsed = time.time() - start_time

            logger.info(f"\n[GAME {game_num} FINISHED] Time: {elapsed:.1f}s")
            results.append(f"Game {game_num}: Completed in {elapsed:.1f}s")

        except Exception as e:
            logger.error(f"\n[GAME {game_num} ERROR] {e}")
            results.append(f"Game {game_num}: ERROR - {e}")

        # Short pause between games
        if game_num < 3:
            logger.info("\nWaiting 3 seconds before next game...")
            time.sleep(3)

    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("  TEST SESSION SUMMARY")
    logger.info("=" * 70)
    for result in results:
        logger.info(f"  {result}")
    logger.info("=" * 70)
    logger.info("  Check logs for:")
    logger.info("    - [CREEP] Tumor counts at 3min and 5min")
    logger.error("    - is_flying errors (should be 0)")
    logger.info("    - [EARLY_DEFENSE] Emergency Zergling triggers")
    logger.info("    - [EXPANSION] Expansion timing and success")
    logger.error("    - [CURRICULUM] No NoneType errors")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
