# -*- coding: utf-8 -*-
"""
핵심 모듈 유닛 테스트 — upgrade_manager, production_controller, micro_controller

SC2 라이브러리 미설치 환경에서 Mock 기반으로 테스트합니다.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)


def _try_import(module_name, class_name):
    """모듈 임포트를 시도하고, 실패 시 None 반환."""
    try:
        mod = __import__(module_name)
        return getattr(mod, class_name)
    except (ImportError, AttributeError, ModuleNotFoundError):
        return None


EvolutionUpgradeManager = _try_import("upgrade_manager", "EvolutionUpgradeManager")
ProductionController = _try_import("production_controller", "ProductionController")


# ─────────────────────────────────────────────
# 1. EvolutionUpgradeManager Tests
# ─────────────────────────────────────────────


@pytest.mark.skipif(
    EvolutionUpgradeManager is None, reason="upgrade_manager not importable"
)
class TestEvolutionUpgradeManager:
    """upgrade_manager.py 핵심 테스트"""

    @pytest.fixture
    def mock_bot(self):
        bot = MagicMock()
        bot.time = 120.0
        bot.minerals = 300
        bot.vespene = 200
        bot.supply_used = 50
        bot.structures = MagicMock()
        bot.structures.return_value = MagicMock(
            exists=True, ready=MagicMock(exists=True)
        )
        bot.already_pending_upgrade = MagicMock(return_value=0)
        bot.can_afford = MagicMock(return_value=True)
        return bot

    def test_initialization(self, mock_bot):
        mgr = EvolutionUpgradeManager(mock_bot)
        assert mgr.bot is mock_bot
        assert mgr.update_interval == 7
        assert mgr.gas_reserve_threshold == 100
        assert mgr._zergling_speed_started is False
        assert mgr._overlord_speed_started is False

    def test_reserved_upgrades_list(self, mock_bot):
        mgr = EvolutionUpgradeManager(mock_bot)
        assert isinstance(mgr.reserved_upgrades, list)
        assert len(mgr.reserved_upgrades) == 0

    def test_intel_priority_boost(self, mock_bot):
        mgr = EvolutionUpgradeManager(mock_bot)
        assert isinstance(mgr.intel_based_priority_boost, dict)
        mgr.intel_based_priority_boost["melee"] = 2.0
        assert mgr.intel_based_priority_boost["melee"] == 2.0

    def test_evo_chamber_cooldown(self, mock_bot):
        mgr = EvolutionUpgradeManager(mock_bot)
        assert mgr._evo_chamber_cooldown == 20.0
        assert mgr._last_evo_chamber_attempt == 0.0

    def test_gas_reservation_threshold(self, mock_bot):
        mgr = EvolutionUpgradeManager(mock_bot)
        assert mgr.gas_reservation_threshold == 50

    def test_strict_priority_flag(self, mock_bot):
        mgr = EvolutionUpgradeManager(mock_bot)
        assert mgr._strict_priority_active is False
        mgr._strict_priority_active = True
        assert mgr._strict_priority_active is True


# ─────────────────────────────────────────────
# 2. ProductionController Tests
# ─────────────────────────────────────────────


@pytest.mark.skipif(
    ProductionController is None, reason="production_controller not importable"
)
class TestProductionController:
    """production_controller.py 핵심 테스트"""

    @pytest.fixture
    def mock_bot(self):
        bot = MagicMock()
        bot.minerals = 400
        bot.vespene = 200
        bot.supply_left = 10
        bot.supply_cap = 50
        bot.units = MagicMock()
        return bot

    @pytest.fixture
    def mock_blackboard(self):
        bb = MagicMock()
        bb.production_queue = []
        bb.authority_mode = "NORMAL"
        return bb

    def test_initialization(self, mock_bot, mock_blackboard):
        ctrl = ProductionController(mock_bot, mock_blackboard)
        assert ctrl.bot is mock_bot
        assert ctrl.blackboard is mock_blackboard
        assert ctrl.production_failures == 0
        assert ctrl.max_produced_per_frame == 0

    def test_units_produced_tracking(self, mock_bot, mock_blackboard):
        ctrl = ProductionController(mock_bot, mock_blackboard)
        assert isinstance(ctrl.units_produced, dict)
        ctrl.units_produced["ZERGLING"] = 10
        assert ctrl.units_produced["ZERGLING"] == 10

    def test_production_failure_counter(self, mock_bot, mock_blackboard):
        ctrl = ProductionController(mock_bot, mock_blackboard)
        ctrl.production_failures += 3
        assert ctrl.production_failures == 3

    @pytest.mark.asyncio
    async def test_execute_without_blackboard(self, mock_bot):
        ctrl = ProductionController(mock_bot, blackboard=None)
        await ctrl.execute(iteration=1)

    @pytest.mark.asyncio
    async def test_execute_without_bot(self, mock_blackboard):
        ctrl = ProductionController(bot=None, blackboard=mock_blackboard)
        await ctrl.execute(iteration=1)

    def test_init_without_blackboard(self, mock_bot):
        ctrl = ProductionController(mock_bot)
        assert ctrl.blackboard is None
        assert ctrl.bot is mock_bot


# ─────────────────────────────────────────────
# 3. BoidsController Tests (sc2 dependency — may skip)
# ─────────────────────────────────────────────


class TestBoidsController:
    """micro_controller.py 핵심 테스트 (sc2 의존성으로 스킵 가능)"""

    def test_import_attempt(self):
        """BoidsController 임포트를 시도하고 결과를 확인한다."""
        try:
            from micro_controller import BoidsController

            mock_bot = MagicMock()
            mock_bot.game_info = MagicMock()
            mock_bot.game_info.map_size = (200, 200)
            ctrl = BoidsController(mock_bot, use_kd_tree=False)
            assert ctrl.bot is mock_bot
        except (ImportError, ModuleNotFoundError):
            pytest.skip("micro_controller requires sc2 library (combat submodules)")

    def test_submodule_existence(self):
        """combat 서브모듈 파일이 존재하는지 확인한다."""
        base = os.path.join(
            os.path.dirname(__file__), "..", "wicked_zerg_challenger", "combat"
        )
        expected = [
            "boids_swarm_control.py",
            "potential_fields.py",
            "terrain_analysis.py",
            "threat_response.py",
            "formation_tactics.py",
            "targeting.py",
            "stutter_step_kiting.py",
        ]
        for f in expected:
            assert os.path.exists(
                os.path.join(base, f)
            ), f"Missing combat submodule: {f}"
