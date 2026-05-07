#!/usr/bin/env python3
"""
Quick replay extraction test helper.
"""

import logging
from pathlib import Path

logger = logging.getLogger("TestExtraction")


def main() -> None:
    replay_dir = Path("D:/replays/replays")
    replays = list(replay_dir.glob("*.SC2Replay")) if replay_dir.exists() else []
    logger.info(f"Replay directory: {replay_dir}")
    logger.info(f"Replays found: {len(replays)}")

    try:
        import sc2reader

        if replays:
            replay = sc2reader.load_replay(str(replays[0]), load_map=True)
            logger.info(f"Loaded replay: {replay.filename}")
            logger.info(f"Players: {len(replay.players)}")
        else:
            logger.info("No replays to load.")
    except ImportError:
        logger.info("sc2reader not installed. Install with: pip install sc2reader")


if __name__ == "__main__":
    main()
