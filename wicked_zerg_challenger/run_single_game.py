# -*- coding: utf-8 -*-
"""
Run a single game for testing.
단일 게임 테스트용 스크립트.
"""

from sc2 import maps
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl as WickedZergBotPro
import argparse
import sys
import os
import logging

logger = logging.getLogger("RunSingleGame")


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
    except Exception as exc:
        logger.debug("%s: %r", "swallowed", exc)

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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single SC2 game for test/training.")
    parser.add_argument("--map", dest="map_name", default="AbyssalReefLE")
    parser.add_argument("--enemy-race", default="Protoss", choices=["Terran", "Protoss", "Zerg", "Random"])
    parser.add_argument("--difficulty", default="Easy")
    return parser.parse_args()


def _parse_race(name: str):
    lookup = {
        "TERRAN": Race.Terran,
        "PROTOSS": Race.Protoss,
        "ZERG": Race.Zerg,
        "RANDOM": Race.Random,
    }
    return lookup.get(name.upper(), Race.Protoss)


def _parse_difficulty(name: str):
    for attr in dir(Difficulty):
        if attr.lower() == name.lower():
            return getattr(Difficulty, attr)
    return Difficulty.Easy


def main():
    """Run a single test game."""
    args = _parse_args()
    _ensure_sc2_path()

    logger.info("\n" + "=" * 60)
    logger.info("  SINGLE GAME TEST")
    logger.info("=" * 60)

    # Settings
    map_name = args.map_name
    opponent_race = _parse_race(args.enemy_race)
    difficulty = _parse_difficulty(args.difficulty)

    logger.info(f"  Map: {map_name}")
    logger.info(f"  Opponent: {opponent_race.name}")
    logger.info(f"  Difficulty: {difficulty.name}")
    logger.info("=" * 60)

    # Create bot
    bot = Bot(Race.Zerg, WickedZergBotPro(train_mode=False))

    # Run game
    map_instance = maps.get(map_name)
    if map_instance is None:
        logger.error(f"Map '{map_name}' not found!")
        return

    run_game(
        map_instance,
        [bot, Computer(opponent_race, difficulty)],
        realtime=False  # False = 빠른 속도로 훈련
    )

    logger.info("\n[GAME FINISHED]")


if __name__ == "__main__":
    main()
