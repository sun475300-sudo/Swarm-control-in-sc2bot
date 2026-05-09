# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

Reuses `tests/_sc2_stub` to install a minimal `sc2` module tree when the
real `python-sc2` library is not importable, so that unit tests which do
`from sc2.ids.unit_typeid import UnitTypeId` (and similar) can be
collected without a SC2 install.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TESTS_DIR = _REPO_ROOT / "tests"
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from _sc2_stub import install as _install_sc2_stub  # noqa: E402

_install_sc2_stub()
