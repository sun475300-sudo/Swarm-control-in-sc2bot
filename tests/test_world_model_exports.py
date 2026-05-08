# -*- coding: utf-8 -*-
"""Regression tests for world_model package public surface.

A previous regression had world_model/__init__.py re-exporting names
that no longer existed in sc2_world_model (DreamerAgent,
LatentImagination, WorldModel), causing every consumer to crash with
ImportError. This test pins the canonical exports + the back-compat
aliases so the surface can't silently drift again.
"""

from __future__ import annotations

import importlib

import pytest


def test_world_model_canonical_exports():
    mod = importlib.import_module("world_model")
    for name in (
        "RSSM",
        "SC2WorldModel",
        "DreamerActor",
        "DreamerCritic",
        "SC2EnvSimulator",
    ):
        assert hasattr(mod, name), f"world_model is missing canonical export {name}"


def test_world_model_back_compat_aliases():
    mod = importlib.import_module("world_model")
    assert mod.WorldModel is mod.SC2WorldModel
    assert mod.DreamerAgent is mod.DreamerActor


def test_world_model_all_is_consistent():
    mod = importlib.import_module("world_model")
    for name in mod.__all__:
        assert hasattr(mod, name), f"world_model.__all__ lists missing name {name}"


def test_world_model_can_import_class():
    """SC2WorldModel must be importable directly from the submodule."""
    submod = importlib.import_module("world_model.sc2_world_model")
    assert hasattr(submod, "SC2WorldModel")
