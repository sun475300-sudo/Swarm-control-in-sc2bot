# Phase 618: Attention-Based Policy Network for SC2
from .sc2_attention_agent import (
    AttentionPolicyConfig,
    PositionalEncoding2D,
    NumpyMultiHeadAttention,
    NumpyTransformerBlock,
    NumpyPointerNetwork,
    NumpyAttentionPolicy,
    SC2AttentionAgent,
)

# Backwards-compatible aliases (older API names)
AttentionPolicy = NumpyAttentionPolicy
EntityEncoder = NumpyTransformerBlock
MultiHeadAttention = NumpyMultiHeadAttention
TransformerBlock = NumpyTransformerBlock

__all__ = [
    "AttentionPolicyConfig",
    "PositionalEncoding2D",
    "NumpyMultiHeadAttention",
    "NumpyTransformerBlock",
    "NumpyPointerNetwork",
    "NumpyAttentionPolicy",
    "SC2AttentionAgent",
    "AttentionPolicy",
    "EntityEncoder",
    "MultiHeadAttention",
    "TransformerBlock",
]
