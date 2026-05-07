# Phase 618: Attention-Based Policy Network for SC2
#
# The torch implementations (AttentionPolicyNetwork, RelationalEntityEncoder,
# MultiHeadRelationalAttention, TransformerEncoderBlock, …) only exist when
# torch is available. The numpy fallbacks always exist. Re-export the numpy
# classes as the public API and provide backwards-compatible legacy aliases;
# expose torch-only classes lazily via __getattr__.
from .sc2_attention_agent import (
    AttentionPolicyConfig,
    NumpyAttentionPolicy,
    NumpyMultiHeadAttention,
    NumpyPointerNetwork,
    NumpyTransformerBlock,
    PositionalEncoding2D,
    SC2AttentionAgent,
)

# Backwards-compatible aliases (legacy names — prefer the explicit ones above)
AttentionPolicy = NumpyAttentionPolicy
MultiHeadAttention = NumpyMultiHeadAttention
TransformerBlock = NumpyTransformerBlock
EntityEncoder = NumpyAttentionPolicy  # legacy alias; closest available equivalent


def __getattr__(name):
    """Lazy access to torch-only classes; returns None when torch is absent."""
    _torch_only = {
        "SinusoidalPositionalEncoding2D",
        "RelationalEntityEncoder",
        "MultiHeadRelationalAttention",
        "TransformerEncoderBlock",
        "MultiScaleTemporalAttention",
        "PointerNetwork",
        "GlobalAttentionPooling",
        "AttentionPolicyNetwork",
    }
    if name in _torch_only:
        from . import sc2_attention_agent as _impl

        return getattr(_impl, name, None)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
