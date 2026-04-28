#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick extractor sanity check.
"""

import logging
from pathlib import Path

logger = logging.getLogger("TestExtractorQuick")


def main() -> None:
    replay_dir = Path("D:/replays/replays")
    replays = list(replay_dir.glob("*.SC2Replay")) if replay_dir.exists() else []
    logger.info(f"Replay directory: {replay_dir}")
    logger.info(f"Replays found: {len(replays)}")

    if not replays:
        return

    sample = replays[0]
    logger.info(f"Sample replay: {sample.name}")


if __name__ == "__main__":
    main()
