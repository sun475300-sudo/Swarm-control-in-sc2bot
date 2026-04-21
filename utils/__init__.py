# utils package
# This root-level utils package extends its __path__ to include
# wicked_zerg_challenger/utils so that imports like
# `from utils.logger import get_logger` work correctly in both
# the test environment and the bot runtime.

import sys
from pathlib import Path

_bot_utils = str(Path(__file__).parent.parent / "wicked_zerg_challenger" / "utils")
if _bot_utils not in __path__:
    __path__.append(_bot_utils)
