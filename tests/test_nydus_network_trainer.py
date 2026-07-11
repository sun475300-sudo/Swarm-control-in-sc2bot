# -*- coding: utf-8 -*-
"""
Regression test for NydusNetworkTrainer._manage_nydus_operations.

_manage_nydus_operations used to call self._command_deployed_units(), a
method that was never defined anywhere on the class -- every periodic
nydus-management tick (once per ~5s, whenever a ready Nydus Network
exists) raised AttributeError, silently swallowed by the broad
except-Exception handler in on_step(). Deployed-unit commanding is
already handled every frame by _manage_active_worms() ->
_command_worm_units(), so the dead call was removed rather than
implemented.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    pytest.skip("sc2 library not available", allow_module_level=True)

import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

from nydus_network_trainer import NydusNetworkTrainer


def _make_bot():
    bot = MagicMock()
    bot.time = 100.0
    bot.units = MagicMock()
    bot.units.filter.return_value = MagicMock(
        __bool__=lambda self: False, take=lambda n: []
    )
    bot.do = MagicMock()
    return bot


@pytest.mark.asyncio
async def test_manage_nydus_operations_does_not_raise():
    trainer = NydusNetworkTrainer(_make_bot())
    trainer._plan_new_worm = AsyncMock()
    trainer._load_units_into_network = AsyncMock()

    network = MagicMock()
    # Should complete without AttributeError from a call to a
    # never-defined self._command_deployed_units().
    await trainer._manage_nydus_operations(network, game_time=100.0)

    trainer._load_units_into_network.assert_awaited_once_with(network)


def test_no_calls_to_undefined_command_deployed_units():
    import ast

    source_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "wicked_zerg_challenger",
        "nydus_network_trainer.py",
    )
    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=source_path)
    defined = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "self"
    }

    assert "_command_deployed_units" not in called, (
        "self._command_deployed_units() was reintroduced but is not "
        "defined anywhere on NydusNetworkTrainer"
    )
    undefined_self_calls = called - defined
    assert (
        not undefined_self_calls
    ), f"NydusNetworkTrainer calls undefined self methods: {undefined_self_calls}"
