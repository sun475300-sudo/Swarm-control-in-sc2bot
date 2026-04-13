"""
Phase 618: Multi-Head Attention Policy Network for SC2
Transformer-based policy with entity-level attention, pointer networks,
relational reasoning, fog-of-war masking, and multi-scale temporal attention.
"""

from __future__ import annotations

import math
import random
import time
import os
import sys
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.checkpoint import checkpoint as torch_checkpoint
    import numpy as np
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    import numpy as np


# ============================================================
# Configuration
# ============================================================

@dataclass
class AttentionPolicyConfig:
    """Hyperparameters for the attention-based policy network."""
    # Entity features
    entity_dim: int = 64          # Per-unit feature dimension
    max_entities: int = 128       # Max units tracked simultaneously
    pos_encoding_dim: int = 16    # Positional encoding channels
    map_size: int = 200           # Map dimension (square)

    # Transformer
    d_model: int = 128            # Hidden dimension
    n_heads: int = 8              # Attention heads
    n_layers: int = 3             # Transformer encoder layers
    d_ff: int = 256               # Feed-forward hidden size
    dropout: float = 0.1
    use_gradient_checkpointing: bool = True

    # Temporal
    temporal_window: int = 16     # Recent observations to keep
    temporal_scales: List[int] = field(default_factory=lambda: [1, 4, 16])

    # Action / value heads
    n_action_types: int = 10      # Discrete action type count
    pointer_heads: int = 4        # Pointer network heads

    # Training
    lr: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_eps: float = 0.2
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 0.5
    batch_size: int = 32


# ============================================================
# NumPy Fallback Helpers
# ============================================================

def np_softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    e = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e / (e.sum(axis=axis, keepdims=True) + 1e-12)


def np_layer_norm(x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    mu = x.mean(axis=-1, keepdims=True)
    sigma = x.std(axis=-1, keepdims=True)
    return (x - mu) / (sigma + eps)


def np_gelu(x: np.ndarray) -> np.ndarray:
    return 0.5 * x * (1.0 + np.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x ** 3)))


def np_linear(x: np.ndarray, W: np.ndarray, b: Optional[np.ndarray] = None) -> np.ndarray:
    out = x @ W.T
    if b is not None:
        out = out + b
    return out


# ============================================================
# Positional Encoding (sinusoidal for 2-D map coordinates)
# ============================================================

def build_sinusoidal_2d(max_len: int, d: int) -> np.ndarray:
    """Create sinusoidal table for 1-D positions, applied per axis."""
    pe = np.zeros((max_len, d), dtype=np.float32)
    pos = np.arange(max_len, dtype=np.float32).reshape(-1, 1)
    div = np.exp(np.arange(0, d, 2, dtype=np.float32) * -(math.log(10000.0) / d))
    pe[:, 0::2] = np.sin(pos * div)
    pe[:, 1::2] = np.cos(pos * div[: d // 2])  # handle odd d
    return pe


class PositionalEncoding2D:
    """Encode (x, y) map position into a fixed-length vector."""

    def __init__(self, d: int, map_size: int):
        half = d // 2
        self.table = build_sinusoidal_2d(map_size, half)
        self.half = half

    def encode_np(self, xy: np.ndarray) -> np.ndarray:
        """xy: (..., 2) integer coordinates -> (..., d) encoding."""
        x = np.clip(xy[..., 0].astype(int), 0, len(self.table) - 1)
        y = np.clip(xy[..., 1].astype(int), 0, len(self.table) - 1)
        return np.concatenate([self.table[x], self.table[y]], axis=-1)


# ============================================================
# NumPy-only Attention Policy (fallback)
# ============================================================

class NumpyMultiHeadAttention:
    """Minimal multi-head attention with optional mask (NumPy)."""

    def __init__(self, d_model: int, n_heads: int, rng: np.random.RandomState):
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        scale = 1.0 / math.sqrt(d_model)
        self.Wq = rng.randn(d_model, d_model).astype(np.float32) * scale
        self.Wk = rng.randn(d_model, d_model).astype(np.float32) * scale
        self.Wv = rng.randn(d_model, d_model).astype(np.float32) * scale
        self.Wo = rng.randn(d_model, d_model).astype(np.float32) * scale
        self.bq = np.zeros(d_model, dtype=np.float32)
        self.bk = np.zeros(d_model, dtype=np.float32)
        self.bv = np.zeros(d_model, dtype=np.float32)
        self.bo = np.zeros(d_model, dtype=np.float32)

    def __call__(self, q: np.ndarray, k: np.ndarray, v: np.ndarray,
                 mask: Optional[np.ndarray] = None) -> np.ndarray:
        """q,k,v: (batch, seq, d_model), mask: (batch, 1, 1, seq) or broadcastable."""
        B, Sq, _ = q.shape
        Sk = k.shape[1]
        H, D = self.n_heads, self.head_dim

        Q = np_linear(q, self.Wq, self.bq).reshape(B, Sq, H, D).transpose(0, 2, 1, 3)
        K = np_linear(k, self.Wk, self.bk).reshape(B, Sk, H, D).transpose(0, 2, 1, 3)
        V = np_linear(v, self.Wv, self.bv).reshape(B, Sk, H, D).transpose(0, 2, 1, 3)

        scores = (Q @ K.transpose(0, 1, 3, 2)) / math.sqrt(D)
        if mask is not None:
            scores = scores + mask * (-1e9)

        attn = np_softmax(scores, axis=-1)
        ctx = (attn @ V).transpose(0, 2, 1, 3).reshape(B, Sq, self.d_model)
        return np_linear(ctx, self.Wo, self.bo)


class NumpyTransformerBlock:
    """Single transformer encoder block (NumPy)."""

    def __init__(self, d_model: int, n_heads: int, d_ff: int, rng: np.random.RandomState):
        self.mha = NumpyMultiHeadAttention(d_model, n_heads, rng)
        scale = 1.0 / math.sqrt(d_model)
        self.W1 = rng.randn(d_ff, d_model).astype(np.float32) * scale
        self.b1 = np.zeros(d_ff, dtype=np.float32)
        self.W2 = rng.randn(d_model, d_ff).astype(np.float32) * scale
        self.b2 = np.zeros(d_model, dtype=np.float32)

    def __call__(self, x: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        h = np_layer_norm(x + self.mha(x, x, x, mask))
        ff = np_gelu(np_linear(h, self.W1, self.b1))
        return np_layer_norm(h + np_linear(ff, self.W2, self.b2))


class NumpyPointerNetwork:
    """Pointer network for selecting target entities (NumPy)."""

    def __init__(self, d_model: int, n_heads: int, rng: np.random.RandomState):
        scale = 1.0 / math.sqrt(d_model)
        self.Wq = rng.randn(d_model, d_model).astype(np.float32) * scale
        self.Wk = rng.randn(d_model, d_model).astype(np.float32) * scale
        self.n_heads = n_heads

    def __call__(self, query: np.ndarray, keys: np.ndarray,
                 mask: Optional[np.ndarray] = None) -> np.ndarray:
        """query: (B, d), keys: (B, N, d) -> logits (B, N)."""
        Q = np_linear(query[:, None, :], self.Wq)  # (B, 1, d)
        K = np_linear(keys, self.Wk)                # (B, N, d)
        logits = (Q @ K.transpose(0, 2, 1)).squeeze(1) / math.sqrt(Q.shape[-1])
        if mask is not None:
            logits = logits + mask * (-1e9)
        return logits


class NumpyAttentionPolicy:
    """Full attention-based policy/value network (NumPy fallback)."""

    def __init__(self, cfg: AttentionPolicyConfig, seed: int = 42):
        self.cfg = cfg
        self.rng = np.random.RandomState(seed)
        self.pos_enc = PositionalEncoding2D(cfg.pos_encoding_dim, cfg.map_size)

        input_dim = cfg.entity_dim + cfg.pos_encoding_dim
        scale = 1.0 / math.sqrt(input_dim)
        self.W_proj = self.rng.randn(cfg.d_model, input_dim).astype(np.float32) * scale
        self.b_proj = np.zeros(cfg.d_model, dtype=np.float32)

        # Relational embeddings: friendly (0) vs enemy (1)
        self.relation_embed = self.rng.randn(2, cfg.d_model).astype(np.float32) * 0.02

        self.blocks = [
            NumpyTransformerBlock(cfg.d_model, cfg.n_heads, cfg.d_ff, self.rng)
            for _ in range(cfg.n_layers)
        ]

        # Temporal aggregation weights per scale
        self.temporal_W = [
            self.rng.randn(cfg.d_model, cfg.d_model).astype(np.float32) * scale
            for _ in cfg.temporal_scales
        ]
        self.temporal_gate = self.rng.randn(len(cfg.temporal_scales), cfg.d_model).astype(np.float32) * 0.02

        # Action type head
        scale_h = 1.0 / math.sqrt(cfg.d_model)
        self.W_action = self.rng.randn(cfg.n_action_types, cfg.d_model).astype(np.float32) * scale_h
        self.b_action = np.zeros(cfg.n_action_types, dtype=np.float32)

        # Pointer network for target selection
        self.pointer = NumpyPointerNetwork(cfg.d_model, cfg.pointer_heads, self.rng)

        # Value head
        self.W_val1 = self.rng.randn(cfg.d_model, cfg.d_model).astype(np.float32) * scale_h
        self.b_val1 = np.zeros(cfg.d_model, dtype=np.float32)
        self.W_val2 = self.rng.randn(1, cfg.d_model).astype(np.float32) * scale_h
        self.b_val2 = np.zeros(1, dtype=np.float32)

    # ---- observation encoding ----

    def _encode_entities(self, entity_features: np.ndarray, positions: np.ndarray,
                         allegiances: np.ndarray) -> np.ndarray:
        """Encode entity observations into d_model embeddings.
        entity_features: (B, N, entity_dim)
        positions:       (B, N, 2) map coordinates
        allegiances:     (B, N) 0=friendly, 1=enemy
        """
        pos_emb = self.pos_enc.encode_np(positions)   # (B, N, pos_dim)
        x = np.concatenate([entity_features, pos_emb], axis=-1)
        x = np_linear(x, self.W_proj, self.b_proj)    # (B, N, d_model)
        # Add relational bias
        rel = self.relation_embed[allegiances.astype(int)]  # (B, N, d_model)
        return x + rel

    def _build_fog_mask(self, visibility: np.ndarray) -> np.ndarray:
        """visibility: (B, N) bool, True=visible. Returns additive mask for attention."""
        # Unseen entities get masked out as keys
        mask = (1.0 - visibility.astype(np.float32))  # 1 where hidden
        return mask[:, None, None, :]  # broadcastable (B, 1, 1, N)

    def _temporal_aggregate(self, history: List[np.ndarray]) -> np.ndarray:
        """Multi-scale temporal attention over historical observations.
        history: list of (B, d_model) global representations, newest first.
        """
        cfg = self.cfg
        B = history[0].shape[0]
        d = cfg.d_model
        T = len(history)

        aggregated = np.zeros((B, d), dtype=np.float32)
        gate_logits = []
        scale_feats = []

        for si, scale in enumerate(cfg.temporal_scales):
            # Average over frames at this scale
            indices = list(range(0, min(T, scale * 4), max(1, scale)))
            if not indices:
                indices = [0]
            frames = np.stack([history[min(i, T - 1)] for i in indices], axis=1)  # (B, K, d)
            pooled = frames.mean(axis=1)  # (B, d)
            projected = np_linear(pooled, self.temporal_W[si])  # (B, d)
            scale_feats.append(projected)
            gate_logits.append((projected * self.temporal_gate[si]).sum(axis=-1, keepdims=True))  # (B, 1)

        gate_logits = np.concatenate(gate_logits, axis=-1)  # (B, n_scales)
        gates = np_softmax(gate_logits, axis=-1)  # (B, n_scales)

        for si, feat in enumerate(scale_feats):
            aggregated += gates[:, si:si+1] * feat

        return aggregated

    # ---- forward pass ----

    def forward(self, entity_features: np.ndarray, positions: np.ndarray,
                allegiances: np.ndarray, visibility: np.ndarray,
                history: Optional[List[np.ndarray]] = None
                ) -> Dict[str, np.ndarray]:
        """
        Full forward pass.
        Returns dict with: action_logits, pointer_logits, value, global_repr
        """
        B, N, _ = entity_features.shape

        # Encode entities
        x = self._encode_entities(entity_features, positions, allegiances)

        # Build fog-of-war mask
        fog_mask = self._build_fog_mask(visibility)

        # Transformer blocks
        for block in self.blocks:
            x = block(x, mask=fog_mask)

        # Global representation via attention pooling
        # Use mean of visible entity embeddings
        vis_float = visibility.astype(np.float32)[:, :, None]  # (B, N, 1)
        vis_count = vis_float.sum(axis=1, keepdims=True).clip(1.0, None)  # (B, 1, 1)
        global_repr = (x * vis_float).sum(axis=1) / vis_count.squeeze(-1)  # (B, d_model)

        # Temporal fusion
        if history and len(history) > 0:
            temporal_ctx = self._temporal_aggregate(history)
            global_repr = global_repr + temporal_ctx

        # Action type logits
        action_logits = np_linear(global_repr, self.W_action, self.b_action)  # (B, n_actions)

        # Pointer network: target selection
        pointer_logits = self.pointer(global_repr, x, mask=fog_mask.squeeze(1).squeeze(1) if fog_mask is not None else None)

        # Value head
        v_hidden = np_gelu(np_linear(global_repr, self.W_val1, self.b_val1))
        value = np_linear(v_hidden, self.W_val2, self.b_val2).squeeze(-1)  # (B,)

        return {
            "action_logits": action_logits,
            "pointer_logits": pointer_logits,
            "value": value,
            "global_repr": global_repr,
        }

    def select_action(self, entity_features: np.ndarray, positions: np.ndarray,
                      allegiances: np.ndarray, visibility: np.ndarray,
                      history: Optional[List[np.ndarray]] = None,
                      deterministic: bool = False
                      ) -> Dict[str, Any]:
        out = self.forward(entity_features, positions, allegiances, visibility, history)
        action_probs = np_softmax(out["action_logits"], axis=-1)
        pointer_probs = np_softmax(out["pointer_logits"], axis=-1)

        if deterministic:
            action = np.argmax(action_probs, axis=-1)
            target = np.argmax(pointer_probs, axis=-1)
        else:
            action = np.array([
                self.rng.choice(len(p), p=p) for p in action_probs
            ])
            target = np.array([
                self.rng.choice(len(p), p=p) for p in pointer_probs
            ])

        return {
            "action": action,
            "target": target,
            "action_probs": action_probs,
            "pointer_probs": pointer_probs,
            "value": out["value"],
            "global_repr": out["global_repr"],
        }


# ============================================================
# PyTorch Modules
# ============================================================

if TORCH_AVAILABLE:

    class SinusoidalPositionalEncoding2D(nn.Module):
        """Learnable-free 2-D positional encoding via sinusoidal tables."""

        def __init__(self, d: int, map_size: int):
            super().__init__()
            half = d // 2
            table = torch.from_numpy(build_sinusoidal_2d(map_size, half))
            self.register_buffer("table", table)
            self.half = half

        def forward(self, xy: torch.Tensor) -> torch.Tensor:
            """xy: (..., 2) int coords -> (..., d)."""
            x = xy[..., 0].long().clamp(0, self.table.size(0) - 1)
            y = xy[..., 1].long().clamp(0, self.table.size(0) - 1)
            return torch.cat([self.table[x], self.table[y]], dim=-1)

    class RelationalEntityEncoder(nn.Module):
        """Project raw entity features + positional encoding + allegiance."""

        def __init__(self, cfg: AttentionPolicyConfig):
            super().__init__()
            input_dim = cfg.entity_dim + cfg.pos_encoding_dim
            self.proj = nn.Linear(input_dim, cfg.d_model)
            self.relation_embed = nn.Embedding(2, cfg.d_model)  # 0=friend, 1=enemy
            self.pos_enc = SinusoidalPositionalEncoding2D(cfg.pos_encoding_dim, cfg.map_size)
            self.norm = nn.LayerNorm(cfg.d_model)

        def forward(self, features: torch.Tensor, positions: torch.Tensor,
                    allegiances: torch.Tensor) -> torch.Tensor:
            pos_emb = self.pos_enc(positions)
            x = torch.cat([features, pos_emb], dim=-1)
            x = self.proj(x)
            x = x + self.relation_embed(allegiances.long())
            return self.norm(x)

    class MultiHeadRelationalAttention(nn.Module):
        """Multi-head attention with relative relational bias."""

        def __init__(self, d_model: int, n_heads: int, dropout: float = 0.1):
            super().__init__()
            self.n_heads = n_heads
            self.head_dim = d_model // n_heads
            self.scale = math.sqrt(self.head_dim)
            self.qkv = nn.Linear(d_model, 3 * d_model)
            self.out_proj = nn.Linear(d_model, d_model)
            self.dropout = nn.Dropout(dropout)
            # Pairwise relation bias: 4 types (friend-friend, friend-enemy, enemy-friend, enemy-enemy)
            self.relation_bias = nn.Embedding(4, n_heads)

        def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None,
                    allegiances: Optional[torch.Tensor] = None) -> torch.Tensor:
            B, N, D = x.shape
            H, Dh = self.n_heads, self.head_dim

            qkv = self.qkv(x).reshape(B, N, 3, H, Dh).permute(2, 0, 3, 1, 4)
            Q, K, V = qkv[0], qkv[1], qkv[2]

            scores = (Q @ K.transpose(-2, -1)) / self.scale  # (B, H, N, N)

            # Relational bias
            if allegiances is not None:
                # Build pairwise relation index: 2*a_i + a_j
                a = allegiances.long()  # (B, N)
                pair_idx = 2 * a.unsqueeze(2) + a.unsqueeze(1)  # (B, N, N)
                rel_bias = self.relation_bias(pair_idx)  # (B, N, N, H)
                scores = scores + rel_bias.permute(0, 3, 1, 2)

            if mask is not None:
                scores = scores.masked_fill(mask.bool(), float("-inf"))

            attn = self.dropout(F.softmax(scores, dim=-1))
            ctx = (attn @ V).transpose(1, 2).reshape(B, N, D)
            return self.out_proj(ctx)

    class TransformerEncoderBlock(nn.Module):
        """Pre-norm transformer block with relational attention."""

        def __init__(self, d_model: int, n_heads: int, d_ff: int, dropout: float = 0.1):
            super().__init__()
            self.norm1 = nn.LayerNorm(d_model)
            self.attn = MultiHeadRelationalAttention(d_model, n_heads, dropout)
            self.norm2 = nn.LayerNorm(d_model)
            self.ff = nn.Sequential(
                nn.Linear(d_model, d_ff),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_ff, d_model),
                nn.Dropout(dropout),
            )

        def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None,
                    allegiances: Optional[torch.Tensor] = None) -> torch.Tensor:
            x = x + self.attn(self.norm1(x), mask=mask, allegiances=allegiances)
            x = x + self.ff(self.norm2(x))
            return x

    class MultiScaleTemporalAttention(nn.Module):
        """Aggregate historical global representations at multiple time scales."""

        def __init__(self, d_model: int, scales: List[int]):
            super().__init__()
            self.scales = scales
            self.projections = nn.ModuleList([
                nn.Linear(d_model, d_model) for _ in scales
            ])
            self.gate = nn.Linear(d_model * len(scales), len(scales))
            self.norm = nn.LayerNorm(d_model)

        def forward(self, current: torch.Tensor,
                    history: List[torch.Tensor]) -> torch.Tensor:
            """current: (B, d), history: list of (B, d) newest-first."""
            T = len(history)
            if T == 0:
                return current

            scale_feats = []
            for si, scale in enumerate(self.scales):
                indices = list(range(0, min(T, scale * 4), max(1, scale)))
                if not indices:
                    indices = [0]
                frames = torch.stack([history[min(i, T - 1)] for i in indices], dim=1)
                pooled = frames.mean(dim=1)
                scale_feats.append(self.projections[si](pooled))

            concat = torch.cat(scale_feats, dim=-1)  # (B, d * n_scales)
            gates = F.softmax(self.gate(concat), dim=-1)  # (B, n_scales)

            aggregated = torch.zeros_like(current)
            for si, feat in enumerate(scale_feats):
                aggregated = aggregated + gates[:, si:si + 1] * feat

            return self.norm(current + aggregated)

    class PointerNetwork(nn.Module):
        """Pointer network head for target entity selection."""

        def __init__(self, d_model: int, n_heads: int = 4):
            super().__init__()
            self.n_heads = n_heads
            self.head_dim = d_model // n_heads
            self.query_proj = nn.Linear(d_model, d_model)
            self.key_proj = nn.Linear(d_model, d_model)
            self.head_merge = nn.Linear(n_heads, 1, bias=False)

        def forward(self, query: torch.Tensor, keys: torch.Tensor,
                    mask: Optional[torch.Tensor] = None) -> torch.Tensor:
            """query: (B, d), keys: (B, N, d) -> logits: (B, N)."""
            B, N, D = keys.shape
            H, Dh = self.n_heads, self.head_dim

            Q = self.query_proj(query).unsqueeze(1).reshape(B, 1, H, Dh).transpose(1, 2)
            K = self.key_proj(keys).reshape(B, N, H, Dh).transpose(1, 2)

            scores = (Q @ K.transpose(-2, -1)).squeeze(-2) / math.sqrt(Dh)  # (B, H, N)
            scores = scores.permute(0, 2, 1)  # (B, N, H)
            logits = self.head_merge(scores).squeeze(-1)  # (B, N)

            if mask is not None:
                logits = logits.masked_fill(mask.bool().squeeze(1).squeeze(1), float("-inf"))
            return logits

    class GlobalAttentionPooling(nn.Module):
        """Attention-weighted pooling over entity embeddings for value head."""

        def __init__(self, d_model: int):
            super().__init__()
            self.attn_weight = nn.Linear(d_model, 1)
            self.norm = nn.LayerNorm(d_model)

        def forward(self, x: torch.Tensor,
                    mask: Optional[torch.Tensor] = None) -> torch.Tensor:
            """x: (B, N, d) -> (B, d)."""
            scores = self.attn_weight(x).squeeze(-1)  # (B, N)
            if mask is not None:
                flat_mask = mask.squeeze(1).squeeze(1) if mask.dim() == 4 else mask
                scores = scores.masked_fill(flat_mask.bool(), float("-inf"))
            weights = F.softmax(scores, dim=-1).unsqueeze(-1)  # (B, N, 1)
            return self.norm((weights * x).sum(dim=1))

    class AttentionPolicyNetwork(nn.Module):
        """Full transformer-based policy/value network for SC2."""

        def __init__(self, cfg: AttentionPolicyConfig):
            super().__init__()
            self.cfg = cfg
            self.entity_encoder = RelationalEntityEncoder(cfg)

            self.transformer_blocks = nn.ModuleList([
                TransformerEncoderBlock(cfg.d_model, cfg.n_heads, cfg.d_ff, cfg.dropout)
                for _ in range(cfg.n_layers)
            ])

            self.temporal_attn = MultiScaleTemporalAttention(
                cfg.d_model, cfg.temporal_scales
            )

            self.global_pool = GlobalAttentionPooling(cfg.d_model)

            # Action type head
            self.action_head = nn.Sequential(
                nn.Linear(cfg.d_model, cfg.d_model),
                nn.GELU(),
                nn.Linear(cfg.d_model, cfg.n_action_types),
            )

            # Pointer network for target selection
            self.pointer_head = PointerNetwork(cfg.d_model, cfg.pointer_heads)

            # Value head
            self.value_head = nn.Sequential(
                nn.Linear(cfg.d_model, cfg.d_model),
                nn.GELU(),
                nn.Linear(cfg.d_model, 1),
            )

            self.use_checkpointing = cfg.use_gradient_checkpointing

        def _build_fog_mask(self, visibility: torch.Tensor) -> torch.Tensor:
            """visibility: (B, N) bool -> (B, 1, 1, N) additive mask."""
            mask = ~visibility  # True where hidden
            return mask.unsqueeze(1).unsqueeze(1)  # (B, 1, 1, N)

        def _run_block(self, block: TransformerEncoderBlock, x: torch.Tensor,
                       mask: torch.Tensor, allegiances: torch.Tensor) -> torch.Tensor:
            return block(x, mask=mask, allegiances=allegiances)

        def forward(self, entity_features: torch.Tensor, positions: torch.Tensor,
                    allegiances: torch.Tensor, visibility: torch.Tensor,
                    history: Optional[List[torch.Tensor]] = None
                    ) -> Dict[str, torch.Tensor]:
            B, N, _ = entity_features.shape

            x = self.entity_encoder(entity_features, positions, allegiances)
            fog_mask = self._build_fog_mask(visibility)

            for block in self.transformer_blocks:
                if self.use_checkpointing and self.training:
                    x = torch_checkpoint(self._run_block, block, x, fog_mask, allegiances,
                                         use_reentrant=False)
                else:
                    x = block(x, mask=fog_mask, allegiances=allegiances)

            global_repr = self.global_pool(x, mask=fog_mask)

            if history and len(history) > 0:
                global_repr = self.temporal_attn(global_repr, history)

            action_logits = self.action_head(global_repr)
            pointer_logits = self.pointer_head(global_repr, x, mask=fog_mask)
            value = self.value_head(global_repr).squeeze(-1)

            return {
                "action_logits": action_logits,
                "pointer_logits": pointer_logits,
                "value": value,
                "global_repr": global_repr,
                "entity_embeddings": x,
            }


# ============================================================
# SC2 Attention Agent
# ============================================================

class SC2AttentionAgent:
    """High-level agent wrapping the attention policy for SC2 gameplay.

    Handles observation preprocessing, action selection, temporal history,
    and PPO-style training updates.
    """

    ACTION_NAMES = [
        "no_op", "attack", "move", "build_worker", "build_supply",
        "build_army", "build_tech", "expand", "scout", "defend",
    ]

    def __init__(self, cfg: Optional[AttentionPolicyConfig] = None, seed: int = 42):
        self.cfg = cfg or AttentionPolicyConfig()
        self.seed = seed
        self.history: List[Any] = []
        self.step_count = 0

        if TORCH_AVAILABLE:
            torch.manual_seed(seed)
            self.network = AttentionPolicyNetwork(self.cfg)
            self.optimizer = torch.optim.Adam(self.network.parameters(), lr=self.cfg.lr)
            self.use_torch = True
        else:
            self.network = NumpyAttentionPolicy(self.cfg, seed=seed)
            self.use_torch = False

        self._trajectory: List[Dict[str, Any]] = []

    @property
    def param_count(self) -> int:
        if self.use_torch:
            return sum(p.numel() for p in self.network.parameters())
        return 0  # numpy variant does not expose count easily

    # ---- observation helpers ----

    @staticmethod
    def _dummy_observation(batch_size: int, n_entities: int,
                           cfg: AttentionPolicyConfig) -> Dict[str, np.ndarray]:
        """Generate a synthetic observation for testing."""
        rng = np.random.RandomState(0)
        return {
            "entity_features": rng.randn(batch_size, n_entities, cfg.entity_dim).astype(np.float32),
            "positions": rng.randint(0, cfg.map_size, (batch_size, n_entities, 2)).astype(np.float32),
            "allegiances": (rng.rand(batch_size, n_entities) > 0.5).astype(np.float32),
            "visibility": (rng.rand(batch_size, n_entities) > 0.2).astype(np.float32),
        }

    def _preprocess_game_state(self, game_state: Dict[str, Any]) -> Dict[str, np.ndarray]:
        """Convert a raw SC2 game state dict into model-ready arrays.

        Expected keys in game_state:
          units: list of dicts with {type_id, x, y, health, shield, energy, is_friendly, is_visible, ...}
          minerals, vespene, supply_used, supply_cap: scalars
        """
        cfg = self.cfg
        units = game_state.get("units", [])
        n = min(len(units), cfg.max_entities)

        features = np.zeros((1, cfg.max_entities, cfg.entity_dim), dtype=np.float32)
        positions = np.zeros((1, cfg.max_entities, 2), dtype=np.float32)
        allegiances = np.zeros((1, cfg.max_entities), dtype=np.float32)
        visibility = np.zeros((1, cfg.max_entities), dtype=np.float32)

        for i in range(n):
            u = units[i]
            features[0, i, 0] = u.get("type_id", 0) / 300.0
            features[0, i, 1] = u.get("health", 0) / 500.0
            features[0, i, 2] = u.get("shield", 0) / 200.0
            features[0, i, 3] = u.get("energy", 0) / 200.0
            features[0, i, 4] = u.get("weapon_cooldown", 0) / 50.0
            features[0, i, 5] = 1.0 if u.get("is_flying", False) else 0.0
            positions[0, i, 0] = u.get("x", 0)
            positions[0, i, 1] = u.get("y", 0)
            allegiances[0, i] = 0.0 if u.get("is_friendly", True) else 1.0
            visibility[0, i] = 1.0 if u.get("is_visible", True) else 0.0

        # Global features injected as a virtual entity at slot n
        if n < cfg.max_entities:
            features[0, n, 0] = game_state.get("minerals", 0) / 1000.0
            features[0, n, 1] = game_state.get("vespene", 0) / 1000.0
            features[0, n, 2] = game_state.get("supply_used", 0) / 200.0
            features[0, n, 3] = game_state.get("supply_cap", 0) / 200.0
            visibility[0, n] = 1.0

        return {
            "entity_features": features,
            "positions": positions,
            "allegiances": allegiances,
            "visibility": visibility,
        }

    # ---- action selection ----

    def act(self, observation: Dict[str, np.ndarray],
            deterministic: bool = False) -> Dict[str, Any]:
        """Select an action given preprocessed observation arrays."""
        hist = self.history[-self.cfg.temporal_window:] if self.history else None

        if self.use_torch:
            self.network.eval()
            with torch.no_grad():
                tensors = {k: torch.from_numpy(v) for k, v in observation.items()}
                torch_hist = [torch.from_numpy(h) for h in hist] if hist else None
                out = self.network(
                    tensors["entity_features"], tensors["positions"],
                    tensors["allegiances"], tensors["visibility"],
                    history=torch_hist,
                )
                action_probs = F.softmax(out["action_logits"], dim=-1)
                pointer_probs = F.softmax(out["pointer_logits"], dim=-1)

                if deterministic:
                    action = action_probs.argmax(dim=-1)
                    target = pointer_probs.argmax(dim=-1)
                else:
                    action = torch.multinomial(action_probs, 1).squeeze(-1)
                    target = torch.multinomial(pointer_probs, 1).squeeze(-1)

                result = {
                    "action": action.cpu().numpy(),
                    "target": target.cpu().numpy(),
                    "action_probs": action_probs.cpu().numpy(),
                    "pointer_probs": pointer_probs.cpu().numpy(),
                    "value": out["value"].cpu().numpy(),
                    "global_repr": out["global_repr"].cpu().numpy(),
                }
        else:
            result = self.network.select_action(
                observation["entity_features"], observation["positions"],
                observation["allegiances"], observation["visibility"],
                history=hist, deterministic=deterministic,
            )

        # Update history
        self.history.append(result["global_repr"].copy())
        if len(self.history) > self.cfg.temporal_window * 2:
            self.history = self.history[-self.cfg.temporal_window:]

        self.step_count += 1
        return result

    def act_on_game_state(self, game_state: Dict[str, Any],
                          deterministic: bool = False) -> Dict[str, Any]:
        """Convenience: raw game state -> action decision."""
        obs = self._preprocess_game_state(game_state)
        result = self.act(obs, deterministic=deterministic)
        action_idx = int(result["action"][0])
        target_idx = int(result["target"][0])
        return {
            "action_type": self.ACTION_NAMES[action_idx],
            "action_idx": action_idx,
            "target_entity_idx": target_idx,
            "value_estimate": float(result["value"][0]),
            "action_probs": {
                name: float(result["action_probs"][0, i])
                for i, name in enumerate(self.ACTION_NAMES)
            },
        }

    # ---- PPO training step ----

    def store_transition(self, obs: Dict[str, np.ndarray], action: int, target: int,
                         reward: float, done: bool, log_prob: float, value: float):
        """Store a transition for PPO update."""
        self._trajectory.append({
            "obs": {k: v.copy() for k, v in obs.items()},
            "action": action, "target": target,
            "reward": reward, "done": done,
            "log_prob": log_prob, "value": value,
        })

    def _compute_gae(self, rewards: List[float], values: List[float],
                     dones: List[bool], last_value: float) -> Tuple[np.ndarray, np.ndarray]:
        """Compute GAE advantages and returns."""
        T = len(rewards)
        advantages = np.zeros(T, dtype=np.float32)
        gae = 0.0
        gamma, lam = self.cfg.gamma, self.cfg.gae_lambda
        for t in reversed(range(T)):
            next_val = last_value if t == T - 1 else values[t + 1]
            next_non_terminal = 0.0 if dones[t] else 1.0
            delta = rewards[t] + gamma * next_val * next_non_terminal - values[t]
            gae = delta + gamma * lam * next_non_terminal * gae
            advantages[t] = gae
        returns = advantages + np.array(values, dtype=np.float32)
        return advantages, returns

    def update(self) -> Dict[str, float]:
        """Run PPO update on stored trajectory. Returns loss metrics."""
        if not self.use_torch or len(self._trajectory) == 0:
            self._trajectory.clear()
            return {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}

        rewards = [t["reward"] for t in self._trajectory]
        values = [t["value"] for t in self._trajectory]
        dones = [t["done"] for t in self._trajectory]
        old_log_probs = np.array([t["log_prob"] for t in self._trajectory], dtype=np.float32)

        advantages, returns = self._compute_gae(rewards, values, dones, values[-1])
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        self.network.train()
        adv_t = torch.from_numpy(advantages)
        ret_t = torch.from_numpy(returns)
        old_lp_t = torch.from_numpy(old_log_probs)

        total_pl, total_vl, total_ent = 0.0, 0.0, 0.0
        n_updates = 0

        for _ in range(4):  # PPO epochs
            for start in range(0, len(self._trajectory), self.cfg.batch_size):
                end = min(start + self.cfg.batch_size, len(self._trajectory))
                batch = self._trajectory[start:end]
                bs = len(batch)

                obs_batch = {
                    k: torch.from_numpy(np.concatenate([t["obs"][k] for t in batch], axis=0))
                    for k in batch[0]["obs"]
                }
                out = self.network(
                    obs_batch["entity_features"], obs_batch["positions"],
                    obs_batch["allegiances"], obs_batch["visibility"],
                )

                action_dist = torch.distributions.Categorical(logits=out["action_logits"])
                actions_t = torch.tensor([t["action"] for t in batch])
                new_log_probs = action_dist.log_prob(actions_t)

                ratio = torch.exp(new_log_probs - old_lp_t[start:end])
                adv_slice = adv_t[start:end]
                surr1 = ratio * adv_slice
                surr2 = torch.clamp(ratio, 1 - self.cfg.clip_eps, 1 + self.cfg.clip_eps) * adv_slice
                policy_loss = -torch.min(surr1, surr2).mean()

                value_loss = F.mse_loss(out["value"], ret_t[start:end])
                entropy = action_dist.entropy().mean()

                loss = policy_loss + self.cfg.value_coef * value_loss - self.cfg.entropy_coef * entropy

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.network.parameters(), self.cfg.max_grad_norm)
                self.optimizer.step()

                total_pl += policy_loss.item()
                total_vl += value_loss.item()
                total_ent += entropy.item()
                n_updates += 1

        self._trajectory.clear()
        n_updates = max(n_updates, 1)
        return {
            "policy_loss": total_pl / n_updates,
            "value_loss": total_vl / n_updates,
            "entropy": total_ent / n_updates,
        }

    # ---- save / load ----

    def save(self, path: str):
        if self.use_torch:
            torch.save({
                "network": self.network.state_dict(),
                "optimizer": self.optimizer.state_dict(),
                "cfg": self.cfg,
                "step_count": self.step_count,
            }, path)

    def load(self, path: str):
        if self.use_torch:
            ckpt = torch.load(path, map_location="cpu", weights_only=False)
            self.network.load_state_dict(ckpt["network"])
            self.optimizer.load_state_dict(ckpt["optimizer"])
            self.step_count = ckpt.get("step_count", 0)

    # ---- diagnostics ----

    def attention_map(self, observation: Dict[str, np.ndarray]) -> Optional[np.ndarray]:
        """Extract attention weights from the last transformer layer (torch only)."""
        if not self.use_torch:
            return None

        self.network.eval()
        with torch.no_grad():
            tensors = {k: torch.from_numpy(v) for k, v in observation.items()}
            x = self.network.entity_encoder(
                tensors["entity_features"], tensors["positions"],
                tensors["allegiances"],
            )
            fog_mask = self.network._build_fog_mask(tensors["visibility"])
            for block in self.network.transformer_blocks:
                x = block(x, mask=fog_mask, allegiances=tensors["allegiances"])

            # Re-run last layer's attention to extract weights
            last_block = self.network.transformer_blocks[-1]
            norm_x = last_block.norm1(x)
            attn_mod = last_block.attn
            B, N, D = norm_x.shape
            H = attn_mod.n_heads
            Dh = attn_mod.head_dim
            qkv = attn_mod.qkv(norm_x).reshape(B, N, 3, H, Dh).permute(2, 0, 3, 1, 4)
            Q, K = qkv[0], qkv[1]
            scores = (Q @ K.transpose(-2, -1)) / attn_mod.scale
            if fog_mask is not None:
                scores = scores.masked_fill(fog_mask.bool(), float("-inf"))
            weights = F.softmax(scores, dim=-1)
            return weights.cpu().numpy()

    def summary(self) -> str:
        lines = [
            "SC2AttentionAgent Summary",
            f"  Backend:        {'PyTorch' if self.use_torch else 'NumPy'}",
            f"  d_model:        {self.cfg.d_model}",
            f"  n_heads:        {self.cfg.n_heads}",
            f"  n_layers:       {self.cfg.n_layers}",
            f"  max_entities:   {self.cfg.max_entities}",
            f"  n_action_types: {self.cfg.n_action_types}",
            f"  temporal_scales:{self.cfg.temporal_scales}",
            f"  checkpointing:  {self.cfg.use_gradient_checkpointing}",
            f"  steps_taken:    {self.step_count}",
        ]
        if self.use_torch:
            lines.append(f"  parameters:     {self.param_count:,}")
        return "\n".join(lines)


# ============================================================
# CLI Demo
# ============================================================

def _demo_numpy_forward():
    """Demonstrate the NumPy fallback path."""
    print("=" * 60)
    print("NumPy Fallback Demo")
    print("=" * 60)

    cfg = AttentionPolicyConfig(max_entities=16, d_model=64, n_heads=4,
                                n_layers=2, d_ff=128, pos_encoding_dim=8)
    policy = NumpyAttentionPolicy(cfg, seed=42)

    B, N = 2, 16
    rng = np.random.RandomState(7)
    entity_features = rng.randn(B, N, cfg.entity_dim).astype(np.float32)
    positions = rng.randint(0, cfg.map_size, (B, N, 2)).astype(np.float32)
    allegiances = (rng.rand(B, N) > 0.5).astype(np.float32)
    visibility = (rng.rand(B, N) > 0.15).astype(np.float32)

    t0 = time.time()
    result = policy.select_action(entity_features, positions, allegiances, visibility)
    dt = time.time() - t0

    print(f"  Batch size:     {B}")
    print(f"  Entities:       {N}")
    print(f"  Action shape:   {result['action'].shape}")
    print(f"  Target shape:   {result['target'].shape}")
    print(f"  Value shape:    {result['value'].shape}")
    print(f"  Latency:        {dt*1000:.1f} ms")
    print(f"  Actions chosen: {result['action']}")
    print(f"  Targets chosen: {result['target']}")
    print(f"  Values:         {result['value']}")
    print()

    # Temporal history test
    history = [rng.randn(B, cfg.d_model).astype(np.float32) for _ in range(8)]
    result2 = policy.select_action(entity_features, positions, allegiances,
                                   visibility, history=history)
    print(f"  With history ({len(history)} frames):")
    print(f"    Actions:      {result2['action']}")
    print(f"    Values:       {result2['value']}")


def _demo_torch_forward():
    """Demonstrate the PyTorch path."""
    print("=" * 60)
    print("PyTorch Demo")
    print("=" * 60)

    cfg = AttentionPolicyConfig(max_entities=32, d_model=128, n_heads=8,
                                n_layers=3, d_ff=256, pos_encoding_dim=16)
    agent = SC2AttentionAgent(cfg, seed=42)
    print(agent.summary())
    print()

    obs = SC2AttentionAgent._dummy_observation(4, 32, cfg)

    # Warm-up
    _ = agent.act(obs)

    t0 = time.time()
    for _ in range(10):
        result = agent.act(obs)
    dt = (time.time() - t0) / 10

    print(f"  Avg latency:    {dt*1000:.1f} ms")
    print(f"  Actions:        {result['action']}")
    print(f"  Targets:        {result['target']}")
    print(f"  Values:         {result['value']}")
    print(f"  History length: {len(agent.history)}")
    print()

    # Attention map extraction
    attn_map = agent.attention_map(obs)
    if attn_map is not None:
        print(f"  Attention map shape: {attn_map.shape}")
        print(f"  Attention sparsity:  {(attn_map < 0.01).mean():.1%}")
    print()

    # Simulated game state
    game_state = {
        "units": [
            {"type_id": 84, "x": 50, "y": 50, "health": 45, "shield": 0,
             "energy": 0, "is_friendly": True, "is_visible": True},
            {"type_id": 105, "x": 80, "y": 60, "health": 150, "shield": 50,
             "energy": 0, "is_friendly": False, "is_visible": True},
            {"type_id": 48, "x": 30, "y": 40, "health": 35, "shield": 0,
             "energy": 0, "is_friendly": True, "is_visible": True},
        ],
        "minerals": 450, "vespene": 200, "supply_used": 44, "supply_cap": 60,
    }
    decision = agent.act_on_game_state(game_state)
    print("  Game state decision:")
    print(f"    Action:  {decision['action_type']}")
    print(f"    Target:  entity #{decision['target_entity_idx']}")
    print(f"    Value:   {decision['value_estimate']:.4f}")
    print(f"    Probs:   { {k: f'{v:.3f}' for k, v in decision['action_probs'].items()} }")

    # PPO update smoke test
    print("\n  PPO update smoke test:")
    for step in range(8):
        obs_s = SC2AttentionAgent._dummy_observation(1, 32, cfg)
        res = agent.act(obs_s)
        log_p = float(np.log(res["action_probs"][0, res["action"][0]] + 1e-8))
        agent.store_transition(obs_s, int(res["action"][0]), int(res["target"][0]),
                               reward=random.uniform(-1, 1), done=(step == 7),
                               log_prob=log_p, value=float(res["value"][0]))
    metrics = agent.update()
    print(f"    Policy loss: {metrics['policy_loss']:.4f}")
    print(f"    Value loss:  {metrics['value_loss']:.4f}")
    print(f"    Entropy:     {metrics['entropy']:.4f}")


def _demo_fog_of_war():
    """Demonstrate fog-of-war masking behavior."""
    print("=" * 60)
    print("Fog-of-War Masking Demo")
    print("=" * 60)

    cfg = AttentionPolicyConfig(max_entities=8, d_model=64, n_heads=4,
                                n_layers=2, d_ff=128, pos_encoding_dim=8)
    agent = SC2AttentionAgent(cfg, seed=42)

    rng = np.random.RandomState(99)
    obs_full = {
        "entity_features": rng.randn(1, 8, cfg.entity_dim).astype(np.float32),
        "positions": rng.randint(0, cfg.map_size, (1, 8, 2)).astype(np.float32),
        "allegiances": np.array([[0, 0, 0, 0, 1, 1, 1, 1]], dtype=np.float32),
        "visibility": np.ones((1, 8), dtype=np.float32),
    }
    res_full = agent.act(obs_full, deterministic=True)

    obs_fog = {k: v.copy() for k, v in obs_full.items()}
    obs_fog["visibility"] = np.array([[1, 1, 1, 1, 0, 0, 0, 0]], dtype=np.float32)
    agent.history.clear()
    res_fog = agent.act(obs_fog, deterministic=True)

    print(f"  Full visibility action: {res_full['action']} target: {res_full['target']}")
    print(f"  Fog  visibility action: {res_fog['action']} target: {res_fog['target']}")
    print(f"  Values differ: {abs(res_full['value'][0] - res_fog['value'][0]):.4f}")
    print(f"  Pointer probs (full): {np.round(res_full['pointer_probs'][0, :8], 3)}")
    print(f"  Pointer probs (fog):  {np.round(res_fog['pointer_probs'][0, :8], 3)}")


def main():
    print("Phase 618: Multi-Head Attention Policy for SC2")
    print(f"Backend: {'PyTorch' if TORCH_AVAILABLE else 'NumPy (fallback)'}")
    print()

    _demo_numpy_forward()
    print()

    if TORCH_AVAILABLE:
        _demo_torch_forward()
        print()
        _demo_fog_of_war()
    else:
        print("PyTorch not available; torch demos skipped.")
        print()
        # Run fog demo with numpy
        cfg = AttentionPolicyConfig(max_entities=8, d_model=64, n_heads=4,
                                    n_layers=2, d_ff=128, pos_encoding_dim=8)
        agent = SC2AttentionAgent(cfg, seed=42)
        obs = SC2AttentionAgent._dummy_observation(1, 8, cfg)
        result = agent.act(obs)
        print(f"  NumPy agent action: {result['action']}, target: {result['target']}")

    print()
    print("Phase 618 demo complete.")


if __name__ == "__main__":
    main()
