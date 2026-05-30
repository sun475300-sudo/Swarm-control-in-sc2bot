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
if importlib.util.find_spec("sc2") is None:
    from tests import _sc2_stub  # noqa: F401  (registers sys.modules entries)
elif os.environ.get("FORCE_SC2_STUB") == "1":
    for name in list(sys.modules):
        if name == "sc2" or name.startswith("sc2."):
            del sys.modules[name]
    from tests import _sc2_stub  # noqa: F401
