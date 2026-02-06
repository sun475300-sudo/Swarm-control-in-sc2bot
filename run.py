#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Arena entry point for WickedZergBotPro.

AI Arena invokes:
    python run.py --LadderServer --GamePort PORT --StartPort PORT

This file must be at the repository root.
No Windows-specific imports (winreg, taskkill) are used.
"""

import sys
import os
from pathlib import Path

# Add bot package to path
bot_dir = Path(__file__).parent / "wicked_zerg_challenger"
sys.path.insert(0, str(bot_dir))

from sc2.player import Bot  # type: ignore
from sc2.data import Race  # type: ignore
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl


def main():
    bot_instance = WickedZergBotProImpl(train_mode=False)
    bot = Bot(Race.Zerg, bot_instance)

    if "--LadderServer" in sys.argv:
        # AI Arena ladder mode
        from sc2.main import run_ladder_game  # type: ignore
        run_ladder_game(bot)
    else:
        # Local fallback
        print("[run.py] No --LadderServer flag detected.")
        print("[run.py] For local training, use: python run_with_training.py")
        print("[run.py] For Arena mode, use:     python run.py --LadderServer --GamePort PORT --StartPort PORT")
        sys.exit(1)


if __name__ == "__main__":
    main()
