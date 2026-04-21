# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

Delegates to the project-root sc2 stub installer so both ``tests/`` and
``wicked_zerg_challenger/tests/`` share the same fallback surface.
"""
import os
import sys
from pathlib import Path

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from _sc2_testing_stub import install_sc2_stub  # noqa: E402

install_sc2_stub()
