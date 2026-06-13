# -*- coding: utf-8 -*-
"""utils.unit_helpers 테스트"""

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
    if "bot_unit_helpers" in sys.modules:
        return sys.modules["bot_unit_helpers"]
    spec = importlib.util.spec_from_file_location(
        "bot_unit_helpers", BOT_ROOT / "utils" / "unit_helpers.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bot_unit_helpers"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestHealthRatio:
    def test_none(self):
        assert _load().get_health_ratio(None) == 0.0

    def test_full(self):
        u = MagicMock(); u.health = 100; u.health_max = 100
        assert _load().get_health_ratio(u) == 1.0

    def test_half(self):
        u = MagicMock(); u.health = 50; u.health_max = 100
        assert _load().get_health_ratio(u) == 0.5

    def test_zero_max(self):
        u = MagicMock(); u.health = 50; u.health_max = 0
        assert _load().get_health_ratio(u) == 0.0


class TestShieldRatio:
    def test_none(self):
        assert _load().get_shield_ratio(None) == 0.0

    def test_full(self):
        u = MagicMock(); u.shield = 80; u.shield_max = 80
        assert _load().get_shield_ratio(u) == 1.0

    def test_zero_max(self):
        u = MagicMock(); u.shield = 0; u.shield_max = 0
        assert _load().get_shield_ratio(u) == 0.0


class TestExecuteUnitAction:
    def test_normal(self):
        action = MagicMock(return_value=None)
        assert _load().execute_unit_action(MagicMock(), action, "a") is True

    def test_raises(self):
        def fail(*a):
            raise AttributeError("x")
        assert _load().execute_unit_action(MagicMock(), fail) is False


class TestCalculateSupply:
    def test_empty(self):
        assert _load().calculate_unit_supply([]) == 0

    def test_with_supply_cost(self):
        u1 = MagicMock(); u1.supply_cost = 2
        u2 = MagicMock(); u2.supply_cost = 3
        assert _load().calculate_unit_supply([u1, u2]) == 5


class TestIsUnitIdle:
    def test_none(self):
        assert _load().is_unit_idle(None) is False

    def test_true(self):
        u = MagicMock(); u.is_idle = True
        assert _load().is_unit_idle(u) is True


class TestGetUnitRange:
    def test_none(self):
        assert _load().get_unit_range(None) == 0.0

    def test_ground(self):
        u = MagicMock(); u.ground_range = 5.0
        assert _load().get_unit_range(u) == 5.0


class TestCanUnitAttack:
    def test_none_unit(self):
        assert _load().can_unit_attack(None, MagicMock()) is False

    def test_none_target(self):
        assert _load().can_unit_attack(MagicMock(), None) is False

    def test_no_range(self):
        u = MagicMock(); u.ground_range = 0; u.air_range = 0
        assert _load().can_unit_attack(u, MagicMock()) is False
