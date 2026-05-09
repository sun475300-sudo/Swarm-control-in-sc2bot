# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection."""

import os
import sys
from pathlib import Path

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# 프로젝트 루트를 sys.path에 추가하여 ``tests/_sc2_stub`` import가 가능하도록 한다.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# sc2 라이브러리가 설치되어 있지 않은 환경(예: CI 샌드박스)에서도 wicked_zerg_challenger
# 테스트가 collection 단계에서 import 오류로 실패하지 않도록 가벼운 스텁을 등록한다.
try:
    from tests._sc2_stub import install as _install_sc2_stub
except Exception:
    _install_sc2_stub = None  # type: ignore[assignment]

if _install_sc2_stub is not None:
    _install_sc2_stub()
