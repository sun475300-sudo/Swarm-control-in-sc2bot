"""Root-level pytest conftest.

Ensures wicked_zerg_challenger/ is on sys.path AHEAD of the project root
before each test module is collected, so absolute imports like
`from utils.logger import get_logger` inside the bot resolve to
wicked_zerg_challenger/utils/logger.py (not the unrelated top-level
utils/ package, which has no logger submodule).

This MUST live at project root so pytest picks it up before tests/conftest.py.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
WZC_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
_WZC_STR = str(WZC_ROOT)


def _ensure_wzc_first() -> None:
    """Force wicked_zerg_challenger/ to sys.path[0] and clear stale utils cache."""
    if not WZC_ROOT.is_dir():
        return
    if _WZC_STR in sys.path:
        sys.path.remove(_WZC_STR)
    sys.path.insert(0, _WZC_STR)

    cached_utils = sys.modules.get("utils")
    if cached_utils is not None:
        utils_file = getattr(cached_utils, "__file__", "") or ""
        if "wicked_zerg_challenger" not in utils_file:
            for _modname in [m for m in list(sys.modules) if m == "utils" or m.startswith("utils.")]:
                sys.modules.pop(_modname, None)


# Run once at conftest load.
_ensure_wzc_first()


def pytest_configure(config):  # pragma: no cover - pytest hook
    """Run again at pytest_configure: by this point pytest has finished its
    own sys.path setup (importmode=prepend would have added the rootdir),
    so re-forcing WZC to the front is what makes the path stick across all
    test collection."""
    _ensure_wzc_first()


def pytest_collectstart(collector):  # pragma: no cover - pytest hook
    """Re-prepend on every collection start in case pytest re-shuffles paths."""
    _ensure_wzc_first()


