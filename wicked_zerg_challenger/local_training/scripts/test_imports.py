#!/usr/bin/env python3
"""
Import test for local training scripts.
"""

import logging

logger = logging.getLogger("TestImports")


def main() -> None:
    modules = [
        "replay_learning_tracker_sqlite",
        "replay_quality_filter",
        "move_completed_replays",
    ]
    for module in modules:
        try:
            __import__(module)
            logger.info(f"Imported {module}")
        except Exception as exc:
            logger.error(f"Failed to import {module}: {exc}")


if __name__ == "__main__":
    main()
