"""
UnitMorphManager helper tests.

Covers _get_dynamic_ratios — pure logic that adapts morph ratios based on
strategy unit_ratios stored in the blackboard. Verified without sc2.
"""

import sys
from pathlib import Path

import pytest

# unit_morph_manager.py imports `from utils.logger import get_logger`,
# which only resolves when wicked_zerg_challenger/ is on sys.path.
_PKG_ROOT = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

try:
    from unit_morph_manager import UnitMorphManager
except ImportError:
    pytest.skip("unit_morph_manager unavailable", allow_module_level=True)


class _StubBlackboard:
    def __init__(self, ratios=None):
        self._ratios = ratios

    def get(self, key, default=None):
        if key == "unit_ratios":
            return self._ratios
        return default


class _StubBot:
    def __init__(self, blackboard=None):
        self.blackboard = blackboard


def _mgr(blackboard=None):
    return UnitMorphManager(_StubBot(blackboard))


def test_default_ratios_for_known_race():
    mgr = _mgr()
    out = mgr._get_dynamic_ratios("Terran")
    assert out == mgr.morph_ratios["Terran"]


def test_unknown_race_falls_back_to_unknown_ratios():
    mgr = _mgr()
    out = mgr._get_dynamic_ratios("Random")
    assert out == mgr.morph_ratios["Unknown"]


def test_no_blackboard_keeps_static_ratios():
    """If bot.blackboard is None, the manager must not crash; it returns
    a copy of the base ratios."""
    mgr = _mgr(blackboard=None)
    out = mgr._get_dynamic_ratios("Protoss")
    assert out == mgr.morph_ratios["Protoss"]


def test_invalid_unit_ratios_keeps_defaults():
    """Non-dict unit_ratios must not poison the result."""
    mgr = _mgr(_StubBlackboard("not-a-dict"))
    out = mgr._get_dynamic_ratios("Zerg")
    assert out == mgr.morph_ratios["Zerg"]


def test_baneling_ratio_scaled_by_strategy():
    mgr = _mgr(_StubBlackboard({"baneling": 0.15}))
    out = mgr._get_dynamic_ratios("Terran")
    # Strategy 0.15 * 2 = 0.30
    assert out["baneling_ratio"] == 0.30


def test_baneling_ratio_capped_at_05():
    """Strategy ratio > 0.25 should cap at 0.5 to avoid runaway morphing."""
    mgr = _mgr(_StubBlackboard({"baneling": 0.9}))
    out = mgr._get_dynamic_ratios("Terran")
    assert out["baneling_ratio"] == 0.5


def test_zero_baneling_ratio_keeps_default():
    """Strategy ratio == 0 means 'no preference' → keep default."""
    base = UnitMorphManager.morph_ratios = None  # ensure fresh import
    mgr = _mgr(_StubBlackboard({"baneling": 0}))
    expected_default = mgr.morph_ratios["Terran"]["baneling_ratio"]
    out = mgr._get_dynamic_ratios("Terran")
    assert out["baneling_ratio"] == expected_default


def test_multiple_overrides_apply_independently():
    mgr = _mgr(
        _StubBlackboard({"baneling": 0.2, "ravager": 0.1, "lurker": 0.05})
    )
    out = mgr._get_dynamic_ratios("Protoss")
    assert out["baneling_ratio"] == pytest.approx(0.4)
    assert out["ravager_ratio"] == pytest.approx(0.2)
    assert out["lurker_ratio"] == pytest.approx(0.1)
    # broodlord unchanged
    assert out["broodlord_ratio"] == mgr.morph_ratios["Protoss"]["broodlord_ratio"]


def test_returned_dict_is_a_copy_not_a_reference():
    """Mutating the result must not mutate stored defaults."""
    mgr = _mgr()
    out = mgr._get_dynamic_ratios("Terran")
    out["baneling_ratio"] = 999
    assert mgr.morph_ratios["Terran"]["baneling_ratio"] != 999
