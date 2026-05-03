# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

Several test modules in this directory do `from sc2.ids.unit_typeid import UnitTypeId`
at import time with no fallback. When `burnysc2` (which provides the `sc2` package)
fails to install — for example because `mpyq` cannot build a wheel on the runner —
those imports raise `ModuleNotFoundError` during collection and the whole
`SC2 봇 검증 & 테스트` job fails. We turn that hard failure into a graceful skip
so the rest of the suite still produces signal.
"""

import os
from pathlib import Path

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"


def _sc2_available() -> bool:
    """True when the `sc2` package (provided by burnysc2) can actually be imported."""
    try:
        import sc2  # noqa: F401
        from sc2.ids.unit_typeid import UnitTypeId  # noqa: F401
    except Exception:
        # ImportError if not installed; protobuf/runtime errors also count as
        # "unusable" from the test's point of view.
        return False
    return True


def _modules_that_import_sc2() -> list:
    """Filenames in this directory whose top-level imports require `sc2`."""
    here = Path(__file__).parent
    hits = []
    for py in here.glob("test_*.py"):
        try:
            src = py.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "from sc2." in src or "import sc2" in src:
            hits.append(py.name)
    return hits


SC2_AVAILABLE = _sc2_available()

# pytest's documented escape hatch: any path listed in `collect_ignore`
# (resolved relative to this conftest's directory) is silently skipped during
# collection. We use it to drop modules whose top-level `from sc2....` import
# would otherwise raise ModuleNotFoundError and abort the whole test job.
collect_ignore = _modules_that_import_sc2() if not SC2_AVAILABLE else []
