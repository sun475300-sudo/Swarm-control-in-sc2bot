# -*- coding: utf-8 -*-
"""Regression tests for package-level imports.

Several top-level packages historically had ``__init__.py`` files that
imported names that no longer existed in the module — e.g. before the
NumPy-fallback split they re-exported ``ActorNetwork`` / ``CommAgent`` /
``DreamerAgent`` / ``AttentionPolicy`` etc. Those imports silently broke
``import package`` and only surfaced when callers tried to use the
package.

These tests exercise plain ``importlib.import_module`` for every package
we know should be importable in a torch-less / sc2-less environment, and
spot-check the legacy aliases that were re-introduced after the split.
"""

import importlib

import pytest

# Packages that must import cleanly on every supported environment
# (NumPy-only fallbacks). Adding a new top-level package?  List it here.
TOP_LEVEL_PACKAGES = [
    "qmix_marl",
    "mappo_marl",
    "maddpg_marl",
    "comm_learning",
    "league_training",
    "curriculum_rl",
    "pbt_optimizer",
    "reward_shaping",
    "strategy_evaluator",
    "attention_policy",
    "world_model",
]


@pytest.mark.parametrize("package", TOP_LEVEL_PACKAGES)
def test_package_imports_cleanly(package: str) -> None:
    """``import <package>`` must succeed without ImportError / NameError."""
    mod = importlib.import_module(package)
    assert mod is not None


# ---------------------------------------------------------------------------
# Legacy alias spot checks. Each pair is (package, attribute_name).
# These aliases are kept for backwards compatibility with older tests and
# external callers that imported pre-fallback class names.
# ---------------------------------------------------------------------------

LEGACY_ALIASES = [
    ("mappo_marl", "ActorNetwork"),
    ("mappo_marl", "SharedCritic"),
    ("mappo_marl", "MAPPOAgent"),
    ("mappo_marl", "MAPPOTrainer"),
    ("comm_learning", "CommAgent"),
    ("comm_learning", "CommChannel"),
    ("comm_learning", "CommNet"),
    ("comm_learning", "TarMAC"),
    ("attention_policy", "AttentionPolicy"),
    ("attention_policy", "MultiHeadAttention"),
    ("attention_policy", "TransformerBlock"),
    ("attention_policy", "EntityEncoder"),
    ("world_model", "WorldModel"),
    ("world_model", "DreamerAgent"),
    ("world_model", "LatentImagination"),
    ("world_model", "demo"),
]


@pytest.mark.parametrize("package,attr", LEGACY_ALIASES)
def test_legacy_alias_resolves(package: str, attr: str) -> None:
    """Legacy alias names must be reachable on the package."""
    mod = importlib.import_module(package)
    resolved = getattr(mod, attr, None)
    assert resolved is not None, f"{package}.{attr} is missing"


# ---------------------------------------------------------------------------
# Torch-guard regression: the *Torch classes that live behind `if HAS_TORCH:`
# should be ``None`` (not raise NameError) when torch isn't installed, but
# the corresponding NumPy fallback class must always be importable.
# ---------------------------------------------------------------------------


def test_qmix_torch_classes_present_or_none() -> None:
    from qmix_marl import sc2_qmix_agent as q

    # NumPy fallbacks always work.
    assert q.AgentQNetNumpy is not None
    assert q.QMIXMixingNetNumpy is not None
    assert q.VDNMixerNumpy is not None
    # Torch sentinels exist as either a class (torch installed) or None.
    assert hasattr(q, "AgentQNetTorch")
    assert hasattr(q, "QMIXMixingNetTorch")
    assert hasattr(q, "VDNMixerTorch")


def test_mappo_torch_classes_present_or_none() -> None:
    from mappo_marl import sc2_mappo_agent as m

    assert m.SharedObsEncoderNumpy is not None
    assert m.CentralizedCriticNumpy is not None
    assert m.DecentralizedActorNumpy is not None
    assert hasattr(m, "SharedObsEncoderTorch")
    assert hasattr(m, "CentralizedCriticTorch")
    assert hasattr(m, "DecentralizedActorTorch")


# ---------------------------------------------------------------------------
# check_proxy must be safe to import on any platform — its body used to
# call sys.exit(1) at module scope on a hardcoded Windows path.
# ---------------------------------------------------------------------------


def test_check_proxy_safe_to_import() -> None:
    mod = importlib.import_module("wicked_zerg_challenger.check_proxy")
    assert callable(getattr(mod, "main", None))
