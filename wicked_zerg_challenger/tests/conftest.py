# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection."""

import os
import warnings

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Silence "Call to deprecated create function" DeprecationWarnings emitted at
# import time by s2clientprotocol's pre-generated *_pb2 modules. They fire
# during collection (before pytest filterwarnings runs), so the filter has to
# be installed here before any sc2 imports.
warnings.filterwarnings(
    "ignore",
    message=r"Call to deprecated create function .*",
    category=DeprecationWarning,
)
