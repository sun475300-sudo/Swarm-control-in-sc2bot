# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection."""

import importlib.util
import os
import sys

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Install the in-tree sc2 stub when burnysc2 isn't available.
# CI runners that cannot build the native ``mpyq`` dependency fall through
# to the stub so tests can still import ``from sc2 import ...``.
#
# The root tests/conftest.py installs the stub eagerly via
# ``importlib.util.spec_from_file_location`` which gives the stub modules a
# ``None`` __spec__. ``importlib.util.find_spec("sc2")`` then raises
# ``ValueError`` on those modules, so we guard against it.
_have_sc2 = "sc2" in sys.modules
if not _have_sc2:
    try:
        _have_sc2 = importlib.util.find_spec("sc2") is not None
    except (ValueError, ModuleNotFoundError):
        _have_sc2 = False


def _load_local_stub():
    # Load by absolute path so this works whether pytest is invoked from
    # the repo root (where ``tests`` is the root-level package) or from
    # ``wicked_zerg_challenger/``.
    stub_path = os.path.join(os.path.dirname(__file__), "_sc2_stub", "__init__.py")
    spec = importlib.util.spec_from_file_location("wicked_sc2_stub", stub_path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)


if not _have_sc2:
    _load_local_stub()
elif os.environ.get("FORCE_SC2_STUB") == "1":
    for name in list(sys.modules):
        if name == "sc2" or name.startswith("sc2."):
            del sys.modules[name]
    _load_local_stub()
