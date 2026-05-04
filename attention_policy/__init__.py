# Phase 618: Attention-Based Policy Network for SC2
from .sc2_attention_agent import (
    AttentionPolicyConfig,
    NumpyAttentionPolicy,
    NumpyMultiHeadAttention,
    NumpyPointerNetwork,
    NumpyTransformerBlock,
    PositionalEncoding2D,
    SC2AttentionAgent,
)

# Backwards-compatible aliases (legacy names from pre-NumPy-fallback split).
AttentionPolicy = NumpyAttentionPolicy
MultiHeadAttention = NumpyMultiHeadAttention
TransformerBlock = NumpyTransformerBlock
EntityEncoder = NumpyAttentionPolicy

__all__ = [
    "AttentionPolicyConfig",
    "NumpyAttentionPolicy",
    "NumpyMultiHeadAttention",
    "NumpyPointerNetwork",
    "NumpyTransformerBlock",
    "PositionalEncoding2D",
    "SC2AttentionAgent",
    "AttentionPolicy",
    "MultiHeadAttention",
    "TransformerBlock",
    "EntityEncoder",
]
