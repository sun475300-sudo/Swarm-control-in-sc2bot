# -*- coding: utf-8 -*-
"""
Run a single game for testing.
?⑥씪 寃뚯엫 ?뚯뒪?몄슜 ?ㅽ겕由쏀듃.
"""

import argparse
import logging
import os
import subprocess
import sys
import time

from sc2 import maps
from sc2.data import Difficulty, Race
from sc2.main import run_game
from sc2.player import Bot, Computer
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl as WickedZergBotPro

logger = logging.getLogger("RunSingleGame")


def _configure_logging():
    """Ensure local runner logs are visible in terminal executions."""
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


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
    except (OSError, FileNotFoundError, AttributeError):
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a single SC2 game for test/training."
    )
    parser.add_argument("--map", dest="map_name", default="AbyssalReefLE")
    parser.add_argument(
        "--enemy-race",
        default="Protoss",
        choices=["Terran", "Protoss", "Zerg", "Random"],
    )
    parser.add_argument("--difficulty", default="Easy")
    parser.add_argument(
        "--time-limit",
        dest="time_limit",
        type=int,
        default=420,
        help="Maximum in-game seconds before forced end",
    )
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


def _cleanup_sc2_processes():
    """Best-effort cleanup for stale SC2 processes before websocket connect."""
    if sys.platform != "win32":
        return
    for exe in ("SC2_x64.exe", "SC2.exe"):
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", exe],
                capture_output=True,
                timeout=3,
            )
        except (OSError, subprocess.SubprocessError):
            pass


def main():
    """Run a single test game."""
    _configure_logging()
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
    logger.info(f"  Time Limit: {args.time_limit}s")
    logger.info("=" * 60)

    map_instance = maps.get(map_name)
    if map_instance is None:
        logger.error(f"Map '{map_name}' not found!")
        return 1

    # Retry once for transient websocket startup failures.
    last_error = None
    for attempt in range(1, 3):
        _cleanup_sc2_processes()
        bot = Bot(Race.Zerg, WickedZergBotPro(train_mode=False))
        try:
            run_game(
                map_instance,
                [bot, Computer(opponent_race, difficulty)],
                realtime=False,  # False = faster simulation mode
                game_time_limit=args.time_limit,
            )
            logger.info("\n[GAME FINISHED]")
            _cleanup_sc2_processes()
            return 0
        except Exception as e:
            last_error = e
            error_text = str(e).lower()
            is_connection_error = (
                "websocket" in error_text
                or "connection already closed" in error_text
                or "closing transport" in error_text
            )
            if is_connection_error and attempt < 2:
                logger.warning(
                    f"Connection issue during simulator start; retrying ({attempt}/2): {e}"
                )
                time.sleep(2)
                continue
            break

    logger.error(f"[GAME FAILED] {last_error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

