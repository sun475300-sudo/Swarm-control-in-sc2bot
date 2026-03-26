# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection."""
import os

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
