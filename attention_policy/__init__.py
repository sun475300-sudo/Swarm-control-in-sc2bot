# Phase 618: Attention-Based Policy Network for SC2
#
# The names re-exported here must match top-level symbols in
# sc2_attention_agent.py. Previously this file imported
# AttentionPolicy/EntityEncoder/MultiHeadAttention/TransformerBlock —
# none of which existed — so `import attention_policy` raised
# ImportError.
from .sc2_attention_agent import (
    AttentionPolicyConfig,
    PositionalEncoding2D,
    NumpyMultiHeadAttention,
    NumpyTransformerBlock,
    NumpyPointerNetwork,
    NumpyAttentionPolicy,
    SC2AttentionAgent,
)

__all__ = [
    "AttentionPolicyConfig",
    "PositionalEncoding2D",
    "NumpyMultiHeadAttention",
    "NumpyTransformerBlock",
    "NumpyPointerNetwork",
    "NumpyAttentionPolicy",
    "SC2AttentionAgent",
]
