# -*- coding: utf-8 -*-
"""Regression tests for MARL package imports.

History: ``mappo_marl/sc2_mappo_agent.py`` and ``qmix_marl/sc2_qmix_agent.py``
declared module-level ``class XxxxTorch(nn.Module)`` references that broke
import in environments where PyTorch is unavailable. Once that error is
re-introduced, every dependent test silently turns into "import error /
collection error", which in CI looks like an unrelated failure.

These tests pin down the contract:

* the *submodule* must be importable with PyTorch absent
* the *package* (``__init__.py``) must not raise on import either
* a couple of well-known config classes must round-trip via ``importlib``

They run without PyTorch installed (and pass with it installed too).
"""

from __future__ import annotations

import importlib
import importlib.util

import pytest

_HAS_NUMPY = importlib.util.find_spec("numpy") is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import(name: str):
    """importlib.import_module that surfaces a clear failure message."""
    try:
        return importlib.import_module(name)
    except Exception as exc:  # noqa: BLE001 - we *do* want to capture all
        pytest.fail(f"{name!r} failed to import: {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Submodule import — guarantees module level is parse-clean
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy required")
class TestMARLSubmoduleImports:
    """If these fail, somebody re-introduced a torch-dependent symbol at
    module level (the ``class FooTorch(nn.Module)`` regression)."""

    def test_qmix_submodule_imports(self):
        mod = _import("qmix_marl.sc2_qmix_agent")
        assert hasattr(mod, "QMIXConfig")
        assert hasattr(
            mod, "AgentQNetTorch"
        )  # class defined; instantiation may need torch
        assert hasattr(mod, "AgentQNetNumpy")  # always works
        assert hasattr(mod, "SC2QMIXAgent")

    def test_mappo_submodule_imports(self):
        mod = _import("mappo_marl.sc2_mappo_agent")
        assert hasattr(mod, "MAPPOConfig")
        assert hasattr(mod, "DecentralizedActorTorch")
        assert hasattr(mod, "DecentralizedActorNumpy")
        assert hasattr(mod, "SC2MAPPOAgent")

    def test_comm_learning_submodule_imports(self):
        mod = _import("comm_learning.sc2_comm_agent")
        assert hasattr(mod, "CommConfig")
        assert hasattr(mod, "SC2CommAgent")


# ---------------------------------------------------------------------------
# Package-level __init__.py — must be safe even with broken re-exports
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy required")
class TestMARLPackageImports:
    """Imports through the package's ``__init__`` should not raise even if
    one of the legacy aliases is renamed in the submodule again."""

    def test_qmix_package(self):
        pkg = _import("qmix_marl")
        # Forward names should still resolve (set up via aliases in __init__)
        assert hasattr(pkg, "QMIXConfig")

    def test_mappo_package(self):
        pkg = _import("mappo_marl")
        # Either MAPPOConfig direct or via the legacy alias path
        assert hasattr(pkg, "MAPPOConfig") or hasattr(pkg, "MAPPOAgent")

    def test_comm_learning_package(self):
        pkg = _import("comm_learning")
        assert hasattr(pkg, "CommConfig") or hasattr(pkg, "CommAgent")


# ---------------------------------------------------------------------------
# Smoke: instantiating the NumPy-only types must succeed without PyTorch
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy required")
class TestMARLNumpyFallbacks:
    """The NumPy fallback path is the *contract* for environments without
    PyTorch — it must instantiate without optional deps."""

    def test_qmix_config_instantiable(self):
        from qmix_marl.sc2_qmix_agent import QMIXConfig

        cfg = QMIXConfig()
        # Defaults exist
        assert getattr(cfg, "n_agents", None) is not None

    def test_mappo_config_instantiable(self):
        from mappo_marl.sc2_mappo_agent import MAPPOConfig

        cfg = MAPPOConfig()
        assert getattr(cfg, "n_agents", None) is not None

    def test_comm_config_instantiable(self):
        from comm_learning.sc2_comm_agent import CommConfig

        cfg = CommConfig()
        assert cfg is not None
