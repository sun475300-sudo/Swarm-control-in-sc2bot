# -*- coding: utf-8 -*-
"""Regression tests for WickedZergBotProImpl._reset_all_managers.

Train-mode runs the bot across many episodes in the same process, so any
per-game state that is not explicitly reset between episodes will leak.
These tests pin the contract that `_reset_all_managers` zeros out the
small set of dict/set/list/int attributes that previously accumulated.
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "wicked_zerg_challenger"))


def _get_reset_method():
    """Extract `_reset_all_managers` from the source file via importlib.

    Importing the bot module directly pulls in dozens of sibling modules
    that reference sc2 enums at import time. We side-step that by
    compiling just the method body and binding it to a SimpleNamespace,
    so the test exercises the actual code without the import zoo.
    """
    import ast
    import textwrap

    src_path = ROOT / "wicked_zerg_challenger" / "wicked_zerg_bot_pro_impl.py"
    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_reset_all_managers":
            # Wrap the method body in a standalone function with `self` as arg.
            wrapped = ast.FunctionDef(
                name="_reset_all_managers",
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg="self")],
                    kwonlyargs=[], kw_defaults=[], defaults=[],
                ),
                body=node.body,
                decorator_list=[],
                returns=None,
            )
            mod = ast.Module(body=[wrapped], type_ignores=[])
            ast.fix_missing_locations(mod)
            ns = {}
            exec(compile(mod, str(src_path), "exec"), ns)
            return ns["_reset_all_managers"]
    raise RuntimeError("_reset_all_managers method not found in bot impl")


@pytest.fixture
def bot():
    """A lightweight stand-in carrying the same per-episode attributes."""
    reset_fn = _get_reset_method()
    impl = types.SimpleNamespace()
    impl._reset_all_managers = lambda: reset_fn(impl)
    # Minimum surface area that _reset_all_managers touches.
    impl.logger = types.SimpleNamespace(
        info=lambda *a, **k: None,
        warning=lambda *a, **k: None,
        debug=lambda *a, **k: None,
        error=lambda *a, **k: None,
    )
    impl.manager_factory = None
    impl.data_cache = None
    # Seed dirty per-episode state.
    impl._units_lost = [{"unit_type": "DRONE", "game_time_seconds": 30.0}]
    impl._build_order_log = [{"structure": "SPAWNINGPOOL", "game_time_seconds": 60.0}]
    impl._tracked_structure_tags = {1, 2, 3}
    impl._known_unit_tags = {42: {"type": "DRONE"}}
    impl._workers_created = 17
    impl._expansions_built = 4
    impl._game_ended = True
    impl._gg_replied = True
    impl._step_integrator = object()
    return impl


def test_reset_clears_per_episode_lists(bot):
    bot._reset_all_managers()
    assert bot._units_lost == []
    assert bot._build_order_log == []


def test_reset_clears_tag_caches(bot):
    bot._reset_all_managers()
    assert bot._tracked_structure_tags == set()
    assert bot._known_unit_tags == {}


def test_reset_zeroes_counters(bot):
    bot._reset_all_managers()
    assert bot._workers_created == 0
    assert bot._expansions_built == 0


def test_reset_clears_one_shot_flags(bot):
    bot._reset_all_managers()
    # Both flags should be removed so the next episode can set them fresh.
    assert not hasattr(bot, "_game_ended")
    assert not hasattr(bot, "_gg_replied")


def test_reset_nulls_step_integrator(bot):
    bot._reset_all_managers()
    assert bot._step_integrator is None


def test_reset_idempotent(bot):
    bot._reset_all_managers()
    bot._reset_all_managers()  # Should not raise even though state already clean.
    assert bot._workers_created == 0
    assert bot._tracked_structure_tags == set()
