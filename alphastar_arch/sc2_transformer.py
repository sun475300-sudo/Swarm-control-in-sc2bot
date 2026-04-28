"""
Phase 357: AlphaStar Inspired Architecture
SC2 Transformer with scatter network, core LSTM, pointer network, and auxiliary tasks.
"""

from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical

# --- Scatter / Entity Encoder ---


class ScatterEncoder(nn.Module):
    """
    Projects entity features and scatters onto a spatial grid (entity → screen).
    Inspired by AlphaStar's entity encoder scatter operation.
    """

    def __init__(self, entity_dim: int, spatial_dim: int, grid_size: int = 32):
        super().__init__()
        self.grid_size = grid_size
        self.entity_proj = nn.Linear(entity_dim, spatial_dim)
        self.spatial_dim = spatial_dim

    def forward(self, entities: torch.Tensor, positions: torch.Tensor) -> torch.Tensor:
        """
        entities:  (B, N, entity_dim)
        positions: (B, N, 2) normalized [0,1] (x, y)
        Returns scattered map: (B, spatial_dim, grid_size, grid_size)
        """
        B, N, _ = entities.shape
        proj = self.entity_proj(entities)  # (B, N, spatial_dim)
        grid = torch.zeros(
            B, self.spatial_dim, self.grid_size, self.grid_size, device=entities.device
        )
        gx = (
            (positions[..., 0] * (self.grid_size - 1))
            .long()
            .clamp(0, self.grid_size - 1)
        )
        gy = (
            (positions[..., 1] * (self.grid_size - 1))
            .long()
            .clamp(0, self.grid_size - 1)
        )
        for b in range(B):
            for n in range(N):
                grid[b, :, gy[b, n], gx[b, n]] += proj[b, n]
        return grid


# --- Core LSTM ---


class CoreLSTM(nn.Module):
    """Temporal reasoning core with LayerNorm LSTM."""

    def __init__(self, input_dim: int, hidden_dim: int, n_layers: int = 3):
        super().__init__()
        self.lstm = nn.LSTM(
            input_dim, hidden_dim, num_layers=n_layers, batch_first=True
        )
        self.norm = nn.LayerNorm(hidden_dim)

    def forward(
        self, x: torch.Tensor, state: Optional[Tuple[torch.Tensor, torch.Tensor]] = None
    ) -> Tuple[torch.Tensor, Tuple]:
        out, new_state = self.lstm(x, state)
        return self.norm(out), new_state


# --- Pointer Network ---


class SC2PointerNetwork(nn.Module):
    """Pointer network for selecting target units/locations."""

    def __init__(self, query_dim: int, key_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.query_proj = nn.Linear(query_dim, hidden_dim)
        self.key_proj = nn.Linear(key_dim, hidden_dim)
        self.score = nn.Linear(hidden_dim, 1, bias=False)

    def forward(
        self,
        query: torch.Tensor,
        keys: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        q = self.query_proj(query).unsqueeze(1)
        k = self.key_proj(keys)
        scores = self.score(torch.tanh(q + k)).squeeze(-1)
        if mask is not None:
            scores = scores.masked_fill(mask, float("-inf"))
        return scores


# --- Auxiliary Heads ---


class BuildOrderHead(nn.Module):
    """Predicts next build order step (auxiliary task)."""

    def __init__(self, hidden_dim: int, n_build_ids: int = 64):
        super().__init__()
        self.head = nn.Linear(hidden_dim, n_build_ids)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        return self.head(h)


class NextUnitHead(nn.Module):
    """Predicts the type of next unit to be produced (auxiliary task)."""

    def __init__(self, hidden_dim: int, n_unit_types: int = 128):
        super().__init__()
        self.head = nn.Linear(hidden_dim, n_unit_types)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        return self.head(h)


# --- Full SC2 Transformer ---


class SC2Transformer(nn.Module):
    """
    AlphaStar-inspired full architecture for SC2:
      1. ScatterEncoder: entity → spatial map
      2. CNN: process spatial map
      3. CoreLSTM: temporal reasoning
      4. PointerNetwork: action target selection
      5. Auxiliary: build order + next unit prediction
    """

    def __init__(
        self,
        entity_dim: int = 64,
        spatial_dim: int = 32,
        hidden_dim: int = 384,
        action_dim: int = 256,
        grid_size: int = 32,
        n_build_ids: int = 64,
        n_unit_types: int = 128,
    ):
        super().__init__()
        self.scatter = ScatterEncoder(entity_dim, spatial_dim, grid_size)
        self.cnn = nn.Sequential(
            nn.Conv2d(spatial_dim, 64, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        cnn_out = 128 * 4 * 4
        self.cnn_proj = nn.Linear(cnn_out, hidden_dim)
        self.core = CoreLSTM(hidden_dim, hidden_dim, n_layers=3)
        self.policy_head = nn.Linear(hidden_dim, action_dim)
        self.value_head = nn.Linear(hidden_dim, 1)
        self.pointer = SC2PointerNetwork(hidden_dim, entity_dim)
        self.build_order_head = BuildOrderHead(hidden_dim, n_build_ids)
        self.next_unit_head = NextUnitHead(hidden_dim, n_unit_types)

    def forward(
        self,
        entities: torch.Tensor,
        positions: torch.Tensor,
        lstm_state: Optional[Tuple] = None,
        entity_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        entities:  (B, N, entity_dim)
        positions: (B, N, 2)
        Returns dict with: policy_logits, value, pointer_logits,
                           build_order_logits, next_unit_logits, lstm_state
        """
        B = entities.shape[0]
        spatial_map = self.scatter(entities, positions)  # (B, S, G, G)
        cnn_feat = self.cnn(spatial_map).flatten(1)  # (B, cnn_out)
        x = F.relu(self.cnn_proj(cnn_feat)).unsqueeze(1)  # (B, 1, H)
        h, new_state = self.core(x, lstm_state)
        h = h.squeeze(1)  # (B, H)

        policy_logits = self.policy_head(h)
        value = self.value_head(h).squeeze(-1)
        pointer_logits = self.pointer(h, entities, entity_mask)
        build_logits = self.build_order_head(h)
        next_unit_logits = self.next_unit_head(h)

        return {
            "policy_logits": policy_logits,
            "value": value,
            "pointer_logits": pointer_logits,
            "build_order_logits": build_logits,
            "next_unit_logits": next_unit_logits,
            "lstm_state": new_state,
        }

    def init_lstm_state(
        self, batch_size: int, hidden_dim: int = 384, n_layers: int = 3
    ) -> Tuple:
        """Initialize zero LSTM hidden/cell state tensors."""
        h = torch.zeros(n_layers, batch_size, hidden_dim)
        c = torch.zeros(n_layers, batch_size, hidden_dim)
        return (h, c)
