# -*- coding: utf-8 -*-
"""utils.game_constants 테스트"""

import sys
import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BOT_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))


def _load():
    if "bot_game_constants" in sys.modules:
        return sys.modules["bot_game_constants"]
    spec = importlib.util.spec_from_file_location(
        "bot_game_constants", BOT_ROOT / "utils" / "game_constants.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bot_game_constants"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestGameFrequencies:
    def test_fps(self):
        assert _load().GameFrequencies.GAME_FPS == 22.4

    def test_every_second(self):
        assert _load().GameFrequencies.EVERY_SECOND == 22

    def test_progression(self):
        gf = _load().GameFrequencies
        assert gf.EVERY_2_SECONDS > gf.EVERY_SECOND
        assert gf.EVERY_10_SECONDS > gf.EVERY_5_SECONDS


class TestEconomyConstants:
    def test_workers(self):
        ec = _load().EconomyConstants
        assert ec.OPTIMAL_WORKERS_PER_BASE == 16
        assert ec.MAX_WORKERS_PER_BASE > ec.OPTIMAL_WORKERS_PER_BASE


class TestCombatConstants:
    def test_hp_in_range(self):
        cc = _load().CombatConstants
        assert 0.0 < cc.RETREAT_HP_THRESHOLD < 1.0
        assert 0.0 < cc.FULL_HP_THRESHOLD < 1.0

    def test_hp_ordering(self):
        cc = _load().CombatConstants
        assert cc.RETREAT_HP_THRESHOLD <= cc.FULL_HP_THRESHOLD


class TestClassesExist:
    def test_all_constant_classes(self):
        mod = _load()
        for name in ("UpgradeConstants", "StrategyConstants", "UnitPriority",
                     "AbilityConstants", "DebugConstants"):
            assert hasattr(mod, name)
