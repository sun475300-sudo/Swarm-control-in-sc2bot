"""
Phase 352: Observation Encoder
Neural network observation encoder for SC2 game state.
Combines spatial (minimap), entity (units), and scalar (resources) encodings.
"""

from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class SpatialEncoder(nn.Module):
    """CNN encoder for minimap feature planes."""

    def __init__(self, in_channels: int = 17, out_dim: int = 128):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.proj = nn.Linear(128 * 4 * 4, out_dim)

    def forward(self, minimap: torch.Tensor) -> torch.Tensor:
        # minimap: (B, C, H, W)
        x = self.cnn(minimap)
        x = x.flatten(1)
        return F.relu(self.proj(x))


class EntityEncoder(nn.Module):
    """Transformer encoder for unit/entity features."""

    def __init__(
        self,
        entity_dim: int = 64,
        n_heads: int = 4,
        n_layers: int = 2,
        out_dim: int = 128,
        max_entities: int = 512,
    ):
        super().__init__()
        self.input_proj = nn.Linear(entity_dim, out_dim)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=out_dim,
            nhead=n_heads,
            dim_feedforward=out_dim * 4,
            dropout=0.0,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.pool = nn.Linear(out_dim, out_dim)

    def forward(
        self, entities: torch.Tensor, mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        # entities: (B, N, entity_dim)
        x = F.relu(self.input_proj(entities))
        x = self.transformer(x, src_key_padding_mask=mask)
        # Mean pooling over valid entities
        if mask is not None:
            valid = (~mask).unsqueeze(-1).float()
            x = (x * valid).sum(dim=1) / valid.sum(dim=1).clamp(min=1)
        else:
            x = x.mean(dim=1)
        return F.relu(self.pool(x))


class ScalarEncoder(nn.Module):
    """MLP encoder for scalar game state features (resources, supply, time)."""

    SCALAR_FIELDS = [
        "minerals",
        "vespene",
        "supply_used",
        "supply_cap",
        "army_count",
        "worker_count",
        "game_loop",
        "enemy_visible_units",
    ]

    def __init__(self, in_dim: int = 8, out_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 64),
            nn.ReLU(),
            nn.Linear(64, out_dim),
            nn.ReLU(),
        )

    def forward(self, scalars: torch.Tensor) -> torch.Tensor:
        return self.net(scalars)


class SC2ObsEncoder(nn.Module):
    """
    Full SC2 observation encoder combining spatial, entity, and scalar branches.
    Input:  raw game state dict
    Output: encoded tensor of shape (B, encoding_dim)
    """

    def __init__(
        self,
        spatial_channels: int = 17,
        entity_dim: int = 64,
        scalar_dim: int = 8,
        encoding_dim: int = 512,
    ):
        super().__init__()
        spatial_out = 128
        entity_out = 128
        scalar_out = 64
        combined = spatial_out + entity_out + scalar_out

        self.spatial_enc = SpatialEncoder(
            in_channels=spatial_channels, out_dim=spatial_out
        )
        self.entity_enc = EntityEncoder(entity_dim=entity_dim, out_dim=entity_out)
        self.scalar_enc = ScalarEncoder(in_dim=scalar_dim, out_dim=scalar_out)
        self.fusion = nn.Sequential(
            nn.Linear(combined, encoding_dim),
            nn.ReLU(),
            nn.Linear(encoding_dim, encoding_dim),
        )

    def forward(self, obs: Dict[str, torch.Tensor]) -> torch.Tensor:
        """
        obs keys expected:
          - 'minimap':  (B, C, H, W)
          - 'entities': (B, N, entity_dim)
          - 'entity_mask': (B, N) bool, True = padding
          - 'scalars':  (B, scalar_dim)
        """
        spatial_feat = self.spatial_enc(obs["minimap"])
        entity_feat = self.entity_enc(obs["entities"], obs.get("entity_mask"))
        scalar_feat = self.scalar_enc(obs["scalars"])
        combined = torch.cat([spatial_feat, entity_feat, scalar_feat], dim=-1)
        return self.fusion(combined)

    @staticmethod
    def dummy_obs(
        batch_size: int = 1, n_entities: int = 64, map_size: int = 64
    ) -> Dict[str, torch.Tensor]:
        return {
            "minimap": torch.zeros(batch_size, 17, map_size, map_size),
            "entities": torch.zeros(batch_size, n_entities, 64),
            "entity_mask": torch.zeros(batch_size, n_entities, dtype=torch.bool),
            "scalars": torch.zeros(batch_size, 8),
        }
