# -*- coding: utf-8 -*-
"""
logic_tuning 모듈 단위 테스트.

이 모듈은 실제 SC2 의존성을 끌고 오지 않도록 mock 객체를 사용한다.
"""

from types import SimpleNamespace

import pytest
from wicked_zerg_challenger.logic_tuning import (
    tune_combat_params,
    tune_economy_params,
)


class TestTuneCombatParams:
    def test_lowers_min_army_for_attack_by_5_percent(self):
        cm = SimpleNamespace(
            _min_army_for_attack=20,
            task_priorities={"base_defense": 100, "main_attack": 40},
        )
        applied = tune_combat_params(cm)
        # 20 * 0.95 = 19
        assert cm._min_army_for_attack == 19
        assert applied["_min_army_for_attack"] == (20, 19)

    def test_clamps_min_army_to_floor(self):
        cm = SimpleNamespace(
            _min_army_for_attack=5,
            task_priorities={"base_defense": 100},
        )
        tune_combat_params(cm)
        # 5*0.95 ~= 5, but floor is 8
        assert cm._min_army_for_attack == 8

    def test_sets_default_base_defense_priority(self):
        """tune sets a *durable* default that per-step reset re-reads."""
        cm = SimpleNamespace(
            _min_army_for_attack=12,
            task_priorities={"base_defense": 100, "main_attack": 40},
        )
        applied = tune_combat_params(cm)
        assert cm._default_base_defense_priority == 110
        assert applied["_default_base_defense_priority"] == (100, 110)

    def test_skips_when_attributes_missing(self):
        cm = SimpleNamespace()  # nothing set
        applied = tune_combat_params(cm)
        # Even with no other attributes, _default_base_defense_priority is set.
        assert applied == {"_default_base_defense_priority": (100, 110)}
        assert cm._default_base_defense_priority == 110


class TestTuneEconomyParams:
    def test_clamps_threshold_to_max_1000(self):
        em = SimpleNamespace(
            gas_overflow_prevention_threshold=2000,
            gas_worker_adjustment_interval=33,
        )
        tune_economy_params(em)
        assert em.gas_overflow_prevention_threshold == 1000

    def test_clamps_threshold_to_min_700(self):
        em = SimpleNamespace(
            gas_overflow_prevention_threshold=500,
            gas_worker_adjustment_interval=33,
        )
        tune_economy_params(em)
        assert em.gas_overflow_prevention_threshold == 700

    def test_keeps_threshold_in_band(self):
        em = SimpleNamespace(
            gas_overflow_prevention_threshold=800,
            gas_worker_adjustment_interval=33,
        )
        tune_economy_params(em)
        assert em.gas_overflow_prevention_threshold == 800

    def test_clamps_adjustment_interval(self):
        em = SimpleNamespace(
            gas_overflow_prevention_threshold=800,
            gas_worker_adjustment_interval=10,  # too tight
        )
        tune_economy_params(em)
        assert em.gas_worker_adjustment_interval == 30

    def test_skips_when_attributes_missing(self):
        em = SimpleNamespace()
        applied = tune_economy_params(em)
        assert applied == {}


class TestRealManagerCompat:
    """logic_tuning이 실제 EconomyManager 인스턴스에서도 깨지지 않는지 검증."""

    def test_tunes_real_economy_manager(self):
        try:
            from wicked_zerg_challenger.economy_manager import EconomyManager
        except (ImportError, TypeError):
            pytest.skip("EconomyManager not importable in this env")

        from unittest.mock import Mock

        bot = Mock()
        bot.larva = []
        bot.workers = Mock()
        bot.workers.amount = 30
        bot.gas_buildings = Mock()
        bot.gas_buildings.ready = []

        try:
            em = EconomyManager(bot)
        except Exception:
            pytest.skip("EconomyManager construction needs more setup")

        applied = tune_economy_params(em)
        # The real manager has both attributes, so both should be applied.
        assert "gas_overflow_prevention_threshold" in applied
        assert 700 <= em.gas_overflow_prevention_threshold <= 1000


class TestStartupWireUp:
    """logic_tuning이 wicked_zerg_bot_pro_impl on_start에 실제로 호출되는지 정적 검증."""

    def test_on_start_imports_logic_tuning(self):
        from pathlib import Path

        bot_impl = (
            Path(__file__).parent.parent
            / "wicked_zerg_challenger"
            / "wicked_zerg_bot_pro_impl.py"
        )
        text = bot_impl.read_text(encoding="utf-8")
        assert "from wicked_zerg_challenger.logic_tuning import" in text
        assert "tune_combat_params" in text
        assert "tune_economy_params" in text

    def test_on_start_guards_missing_managers(self):
        """If self.combat / self.economy is None, logic_tuning must not be called."""
        from pathlib import Path

        bot_impl = (
            Path(__file__).parent.parent
            / "wicked_zerg_challenger"
            / "wicked_zerg_bot_pro_impl.py"
        )
        text = bot_impl.read_text(encoding="utf-8")
        # Guard pattern presence - protects against tune_*(None) -> AttributeError.
        assert 'getattr(self, "combat", None) is not None' in text
        assert 'getattr(self, "economy", None) is not None' in text


class TestCombatManagerReadsDefaultPriority:
    """combat_manager._execute_multitasking이 _default_base_defense_priority를 읽는지 정적 검증."""

    def test_per_step_reset_reads_default(self):
        from pathlib import Path

        cm_path = (
            Path(__file__).parent.parent
            / "wicked_zerg_challenger"
            / "combat_manager.py"
        )
        text = cm_path.read_text(encoding="utf-8")
        # 매 step의 priority reset이 외부에서 조정 가능한 default를 읽도록 만들었는지.
        assert (
            'getattr(\n            self, "_default_base_defense_priority", 100\n        )'
            in text
            or 'getattr(self, "_default_base_defense_priority", 100)' in text
        )
