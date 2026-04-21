# -*- coding: utf-8 -*-
"""
Root-level utils.logger stub - forwards to wicked_zerg_challenger.utils.logger.

This file exists to prevent the root-level utils/ package from shadowing
the wicked_zerg_challenger/utils/ package when running pytest from project root.
"""
import logging
import sys
from pathlib import Path

# Ensure the bot's utils is importable
_bot_dir = str(Path(__file__).parent.parent / "wicked_zerg_challenger")
if _bot_dir not in sys.path:
    sys.path.insert(0, _bot_dir)

try:
    from wicked_zerg_challenger.utils.logger import get_logger, setup_logger
except ImportError:
    # Fallback: minimal logger
    def get_logger(name: str = "WickedZergBot") -> logging.Logger:
        return logging.getLogger(name)

    def setup_logger(name="WickedZergBot", **kwargs) -> logging.Logger:
        return logging.getLogger(name)
