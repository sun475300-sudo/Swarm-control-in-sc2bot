# -*- coding: utf-8 -*-
"""Project-root conftest.

Ensures the ``sc2`` namespace is importable everywhere - both in
``tests/`` (root) and ``wicked_zerg_challenger/tests/``. The actual stub
implementation lives in ``wicked_zerg_challenger/conftest.py``; we re-use the
helper here so a single source of truth exists.
"""

from __future__ import annotations

import importlib.util as _import_util
import os
import sys
from pathlib import Path

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

_PROJECT_ROOT = Path(__file__).resolve().parent
_STUB_LOADER = _PROJECT_ROOT / "wicked_zerg_challenger" / "conftest.py"

# Load the sc2 stub installer from the bot's conftest by file path so we don't
# depend on import order. ``find_spec("sc2")`` short-circuits when the real
# package is installed, so this is a no-op in that case.
if _import_util.find_spec("sc2") is None and _STUB_LOADER.exists():
    spec = _import_util.spec_from_file_location("_wicked_zerg_sc2_stub", _STUB_LOADER)
    if spec and spec.loader:
        module = _import_util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
