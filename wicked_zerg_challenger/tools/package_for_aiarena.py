#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the same complete Arena package as the root packaging command."""

import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from create_arena_package import create_arena_zip


def main() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return create_arena_zip(PROJECT_ROOT / "dist", f"WickedZergBotPro_{timestamp}.zip")


if __name__ == "__main__":
    main()
