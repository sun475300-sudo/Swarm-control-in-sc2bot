"""Top-level package import smoke tests.

Background
----------
A recurring class of bug in this repo is ``package/__init__.py`` files
re-exporting names that don't exist in the underlying module — e.g.
``from .sc2_world_model import WorldModel`` when only ``SC2WorldModel``
existed. ``import package`` then crashed at import time, every test
that touched it failed, and the cause wasn't obvious from the symptom.

Found and fixed in this branch:
    - ``mappo_marl`` (MAPPOAgent/MAPPOTrainer/SharedCritic/ActorNetwork)
    - ``comm_learning`` (CommChannel/CommNet/TarMAC/CommAgent)
    - ``world_model`` (WorldModel/DreamerAgent/LatentImagination/demo)
    - ``attention_policy`` (AttentionPolicy/EntityEncoder/MultiHeadAttention/TransformerBlock)

This test simply iterates the candidate top-level packages and asserts
``importlib.import_module`` succeeds. Packages whose runtime deps
(torch, pandas, etc.) are not present in the test environment are
skipped via the dependency filter.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Packages we care about pinning. New MARL/RL packages should be added here.
PACKAGES = [
    "attention_policy",
    "comm_learning",
    "imitation_learning",
    "league_training",
    "mappo_marl",
    "model_based_rl",
    "pettingzoo_env",
    "qmix_marl",
    "reward_shaping",
    "world_model",
]


# Errors that indicate a missing optional runtime dependency rather than
# a real packaging bug. Skip those.
_OPTIONAL_DEP_NEEDLES = (
    "No module named 'torch'",
    "No module named 'tensorflow'",
    "No module named 'transformers'",
    "No module named 'gym'",
    "No module named 'pettingzoo'",
    "No module named 'pandas'",
    "No module named 'scipy'",
    "No module named 'sklearn'",
    "No module named 'redis'",
    "No module named 'sqlalchemy'",
    "No module named 'jaxtyping'",
)


@pytest.mark.parametrize("pkg", PACKAGES)
def test_package_imports_cleanly(pkg: str) -> None:
    try:
        importlib.import_module(pkg)
    except ModuleNotFoundError as e:
        if any(needle in str(e) for needle in _OPTIONAL_DEP_NEEDLES):
            pytest.skip(f"optional runtime dep missing for {pkg}: {e}")
        raise
    except ImportError as e:
        # ImportError for a re-export from sibling module is the bug
        # class we're guarding against — re-raise.
        raise AssertionError(
            f"{pkg}/__init__.py re-exports a name that does not exist: {e}"
        ) from e
