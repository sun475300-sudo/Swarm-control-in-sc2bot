# -*- coding: utf-8 -*-
"""utils.common_helpers 테스트"""

import sys
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BOT_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))


def _load():
    if "bot_common_helpers" in sys.modules:
        return sys.modules["bot_common_helpers"]
    spec = importlib.util.spec_from_file_location(
        "bot_common_helpers", BOT_ROOT / "utils" / "common_helpers.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bot_common_helpers"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestHasUnits:
    def test_none(self):
        assert _load().has_units(None) is False

    def test_empty(self):
        assert _load().has_units([]) is False

    def test_nonempty(self):
        assert _load().has_units([1, 2]) is True

    def test_sc2_exists_true(self):
        u = MagicMock(); u.exists = True
        assert _load().has_units(u) is True

    def test_sc2_exists_false(self):
        u = MagicMock(); u.exists = False
        assert _load().has_units(u) is False


class TestSafeFirst:
    def test_none(self):
        assert _load().safe_first(None) is None

    def test_list(self):
        assert _load().safe_first([10, 20]) == 10

    def test_sc2_first(self):
        u = MagicMock(); u.exists = True; u.first = "f"
        assert _load().safe_first(u) == "f"


class TestSafeAmount:
    def test_none(self):
        assert _load().safe_amount(None) == 0

    def test_list(self):
        assert _load().safe_amount([1, 2, 3]) == 3

    def test_sc2_amount(self):
        u = MagicMock(); u.exists = True; u.amount = 7
        assert _load().safe_amount(u) == 7


class TestClamp:
    def test_within(self):
        assert _load().clamp(5, 0, 10) == 5

    def test_below(self):
        assert _load().clamp(-5, 0, 10) == 0

    def test_above(self):
        assert _load().clamp(15, 0, 10) == 10


class TestPercentage:
    def test_half(self):
        assert _load().percentage(50, 100) == 0.5

    def test_zero_total(self):
        assert _load().percentage(50, 0) == 0.0

    def test_over_clamps(self):
        assert _load().percentage(150, 100) == 1.0
