# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection."""

import os
import sys
from pathlib import Path

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# 프로젝트 루트를 sys.path 에 노출시켜 ``from tests._sc2_stub import ...`` 가능하게 한다.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# 또한 ``wicked_zerg_challenger`` 모듈들이 import-time 에 ``from bot_step_integration ...`` 같은
# 사이드 임포트를 하는데 이를 위해 그 디렉토리도 path 에 둔다.
_PKG_DIR = _PROJECT_ROOT / "wicked_zerg_challenger"
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

# burnysc2 미설치 환경에서 sc2 스텁 주입 (실제 sc2 가 있으면 no-op).
try:
    import sc2  # type: ignore  # noqa: F401
except ImportError:
    from tests._sc2_stub import install_sc2_stub  # type: ignore

    install_sc2_stub()
