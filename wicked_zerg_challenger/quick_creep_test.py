# -*- coding: utf-8 -*-
"""
Quick creep test - 1분 빠른 점막 검증
"""

import logging
import os
import sys

from sc2.data import Difficulty, Race

# Heavy imports deferred to main() so this module is importable in CI/tests.

logger = logging.getLogger("QuickCreepTest")


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
    """Run quick creep verification test."""
    from sc2 import maps
    from sc2.main import run_game
    from sc2.player import Bot, Computer
    from wicked_zerg_bot_pro_impl import WickedZergBotProImpl as WickedZergBotPro

    _ensure_sc2_path()

    logger.info("\n" + "=" * 70)
    logger.info("  QUICK CREEP TEST (1 minute)")
    logger.info("=" * 70)
    logger.info("  Testing:")
    logger.info("    - Dedicated creep queen assignment")
    logger.info("    - Creep spread during defense")
    logger.info("    - Target: 3min = 5 tumors minimum")
    logger.info("=" * 70)
    map_name = "AbyssalReefLE"
    opponent_race = Race.Protoss
    difficulty = Difficulty.Easy

    logger.info(f"  Map: {map_name}")
    logger.info(f"  Opponent: {opponent_race.name}")
    logger.info(f"  Difficulty: {difficulty.name}")
    logger.info("=" * 70)
    # Create bot
    bot = Bot(Race.Zerg, WickedZergBotPro(train_mode=False))

    # Get map
    map_instance = maps.get(map_name)
    if map_instance is None:
        logger.error(f"Map '{map_name}' not found!")
        return

    # Run game
    try:
        run_game(
            map_instance, [bot, Computer(opponent_race, difficulty)], realtime=False
        )
        logger.info("\n[TEST FINISHED]")
    except Exception as e:
        logger.error(f"\n[TEST ERROR] {e}")


if __name__ == "__main__":
    main()
