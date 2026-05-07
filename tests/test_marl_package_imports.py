"""
Regression tests for the MARL / world-model / attention package surface.

These packages all share a torch-optional design. Earlier the package
``__init__`` files referenced names that either (a) only exist when torch is
installed, or (b) never existed in the underlying module. The result was that
``import qmix_marl`` (etc.) raised at import time even on the supported
NumPy-only path. This file pins down the public import surface so the
regression cannot return.
"""

from __future__ import annotations

import importlib

import pytest

PACKAGES = [
    "qmix_marl",
    "mappo_marl",
    "maddpg_marl",
    "comm_learning",
    "attention_policy",
    "world_model",
]


@pytest.mark.parametrize("pkg", PACKAGES)
def test_package_imports_without_torch(pkg):
    """Every MARL/world-model package must import on the NumPy-only path."""
    mod = importlib.import_module(pkg)
    assert mod is not None


# ── Per-package smoke tests for the public NumPy classes ─────────────────


def test_qmix_numpy_classes_present():
    import qmix_marl

    assert qmix_marl.QMIXConfig is not None
    assert qmix_marl.AgentQNetNumpy is not None
    assert qmix_marl.QMIXMixingNetNumpy is not None
    # Legacy aliases still work:
    assert qmix_marl.AgentQNetwork is qmix_marl.AgentQNetNumpy
    assert qmix_marl.QMIXMixingNetwork is qmix_marl.QMIXMixingNetNumpy


def test_mappo_numpy_classes_present():
    import mappo_marl

    assert mappo_marl.MAPPOConfig is not None
    assert mappo_marl.SharedObsEncoderNumpy is not None
    assert mappo_marl.CentralizedCriticNumpy is not None
    assert mappo_marl.DecentralizedActorNumpy is not None
    # Legacy aliases:
    assert mappo_marl.ActorNetwork is mappo_marl.DecentralizedActorNumpy
    assert mappo_marl.SharedCritic is mappo_marl.CentralizedCriticNumpy
    assert mappo_marl.MAPPOAgent is mappo_marl.SC2MAPPOAgent


def test_maddpg_numpy_classes_present():
    import maddpg_marl

    assert maddpg_marl.MADDPGConfig is not None
    assert maddpg_marl.OUNoise is not None
    assert maddpg_marl.MultiAgentReplayBuffer is not None


def test_comm_learning_numpy_classes_present():
    import comm_learning

    assert comm_learning.CommConfig is not None
    assert comm_learning.NumpyCommNet is not None
    assert comm_learning.NumpyTarMAC is not None
    assert comm_learning.ProtocolAnalyzer is not None
    # Legacy aliases:
    assert comm_learning.CommAgent is comm_learning.SC2CommAgent
    assert comm_learning.CommNet is comm_learning.NumpyCommNet
    assert comm_learning.TarMAC is comm_learning.NumpyTarMAC


def test_attention_policy_numpy_classes_present():
    import attention_policy

    assert attention_policy.AttentionPolicyConfig is not None
    assert attention_policy.NumpyAttentionPolicy is not None
    assert attention_policy.NumpyMultiHeadAttention is not None
    assert attention_policy.NumpyTransformerBlock is not None
    # Legacy aliases:
    assert attention_policy.AttentionPolicy is attention_policy.NumpyAttentionPolicy
    assert (
        attention_policy.MultiHeadAttention is attention_policy.NumpyMultiHeadAttention
    )
    assert attention_policy.TransformerBlock is attention_policy.NumpyTransformerBlock


def test_world_model_classes_present():
    import world_model

    assert world_model.RSSM is not None
    assert world_model.SC2WorldModel is not None
    assert world_model.DreamerActor is not None
    assert world_model.DreamerCritic is not None
    # Legacy aliases:
    assert world_model.WorldModel is world_model.SC2WorldModel
    assert world_model.DreamerAgent is world_model.SC2WorldModel


# ── Lazy torch attribute access ──────────────────────────────────────────


def test_comm_learning_torch_attr_accessible():
    """Lazy __getattr__ must not raise even when torch is absent."""
    import comm_learning

    # The attribute access path itself must not raise; the value can be None.
    val = comm_learning.CommNetModule  # noqa: F841


def test_attention_policy_torch_attr_accessible():
    import attention_policy

    val = attention_policy.AttentionPolicyNetwork  # noqa: F841


def test_comm_learning_unknown_attr_still_raises():
    import comm_learning

    with pytest.raises(AttributeError):
        _ = comm_learning.this_attribute_definitely_does_not_exist


def test_attention_policy_unknown_attr_still_raises():
    import attention_policy

    with pytest.raises(AttributeError):
        _ = attention_policy.no_such_attr_at_all


# ── Torch-stub safety net (qmix/mappo) ───────────────────────────────────


def test_qmix_torch_stub_blocks_silent_use():
    """When torch is absent, instantiating *Torch classes must fail loudly."""
    import qmix_marl.sc2_qmix_agent as mod

    if mod.HAS_TORCH:
        pytest.skip("torch installed — stub is not active")
    with pytest.raises(RuntimeError, match="PyTorch is not installed"):
        mod.AgentQNetTorch(obs_dim=4, action_dim=2, hidden_dim=8)


def test_mappo_torch_stub_blocks_silent_use():
    import mappo_marl.sc2_mappo_agent as mod

    if mod.HAS_TORCH:
        pytest.skip("torch installed — stub is not active")
    # SharedObsEncoderTorch subclasses our nn.Module stub, so super().__init__
    # raises RuntimeError before the constructor reaches its own arg parsing.
    # Pass dummy values so we don't trip on TypeError (which would mean the
    # stub never fired).
    with pytest.raises(RuntimeError, match="PyTorch is not installed"):
        mod.SharedObsEncoderTorch(obs_dim=4, encoder_dim=8, hidden_dim=8)
