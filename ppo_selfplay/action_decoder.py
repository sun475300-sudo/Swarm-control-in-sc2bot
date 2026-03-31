"""
Phase 353: Action Decoder
Hierarchical action decoding for SC2 bot with autoregressive decoding,
action masking, and a pointer network for unit selection.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import IntEnum


class ActionType(IntEnum):
    SELECT_UNIT = 0
    MOVE_SCREEN = 1
    BUILD_STRUCTURE = 2
    TRAIN_UNIT = 3
    RESEARCH_UPGRADE = 4
    ATTACK_UNIT = 5
    NO_OP = 6


NUM_ACTION_TYPES = len(ActionType)
NUM_SCREEN_POSITIONS = 64 * 64   # flattened screen grid
NUM_BUILD_IDS = 64
NUM_UNIT_IDS = 128
NUM_UPGRADE_IDS = 32


@dataclass
class DecodedAction:
    action_type: int
    target_unit_idx: Optional[int] = None
    screen_position: Optional[Tuple[int, int]] = None
    build_id: Optional[int] = None
    unit_id: Optional[int] = None
    upgrade_id: Optional[int] = None
    log_prob: float = 0.0


class PointerNetwork(nn.Module):
    """Attention-based pointer over entity embeddings for unit selection."""

    def __init__(self, query_dim: int, key_dim: int):
        super().__init__()
        self.query_proj = nn.Linear(query_dim, key_dim)
        self.key_proj = nn.Linear(key_dim, key_dim)
        self.v = nn.Linear(key_dim, 1, bias=False)

    def forward(self, query: torch.Tensor, keys: torch.Tensor,
                mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        # query: (B, query_dim)  keys: (B, N, key_dim)
        q = self.query_proj(query).unsqueeze(1)          # (B, 1, key_dim)
        k = self.key_proj(keys)                           # (B, N, key_dim)
        scores = self.v(torch.tanh(q + k)).squeeze(-1)   # (B, N)
        if mask is not None:
            scores = scores.masked_fill(mask, float("-inf"))
        return scores


class ActionDecoder(nn.Module):
    """
    Autoregressive action decoder for SC2's hierarchical action space.
    Decodes: action_type → type-specific arguments.
    """

    def __init__(self, state_dim: int = 512, entity_dim: int = 128,
                 hidden_dim: int = 256):
        super().__init__()
        self.state_dim = state_dim
        self.entity_dim = entity_dim

        # Action type head
        self.action_type_head = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, NUM_ACTION_TYPES),
        )
        # Argument heads
        self.select_unit_ptr = PointerNetwork(state_dim, entity_dim)
        self.move_head = nn.Linear(state_dim, NUM_SCREEN_POSITIONS)
        self.build_head = nn.Linear(state_dim, NUM_BUILD_IDS)
        self.train_head = nn.Linear(state_dim, NUM_UNIT_IDS)
        self.research_head = nn.Linear(state_dim, NUM_UPGRADE_IDS)
        self.attack_ptr = PointerNetwork(state_dim, entity_dim)

    def _apply_mask(self, logits: torch.Tensor,
                    mask: Optional[torch.Tensor]) -> torch.Tensor:
        if mask is not None:
            logits = logits.masked_fill(~mask.bool(), float("-inf"))
        return logits

    def forward(
        self,
        state: torch.Tensor,
        entities: Optional[torch.Tensor] = None,
        action_type_mask: Optional[torch.Tensor] = None,
        entity_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[DecodedAction, torch.Tensor]:
        """
        Returns (DecodedAction, total log_prob tensor).
        state:   (B, state_dim)
        entities:(B, N, entity_dim)
        """
        type_logits = self._apply_mask(self.action_type_head(state), action_type_mask)
        type_dist = Categorical(logits=type_logits)
        action_type = type_dist.sample()
        log_prob = type_dist.log_prob(action_type)
        decoded = DecodedAction(action_type=action_type.item())

        atype = action_type.item()
        if atype == ActionType.SELECT_UNIT and entities is not None:
            scores = self.select_unit_ptr(state, entities, entity_mask)
            dist = Categorical(logits=scores)
            idx = dist.sample()
            log_prob = log_prob + dist.log_prob(idx)
            decoded.target_unit_idx = idx.item()

        elif atype == ActionType.MOVE_SCREEN:
            pos_logits = self.move_head(state)
            dist = Categorical(logits=pos_logits)
            flat_pos = dist.sample()
            log_prob = log_prob + dist.log_prob(flat_pos)
            decoded.screen_position = (flat_pos.item() // 64, flat_pos.item() % 64)

        elif atype == ActionType.BUILD_STRUCTURE:
            dist = Categorical(logits=self.build_head(state))
            bid = dist.sample()
            log_prob = log_prob + dist.log_prob(bid)
            decoded.build_id = bid.item()

        elif atype == ActionType.TRAIN_UNIT:
            dist = Categorical(logits=self.train_head(state))
            uid = dist.sample()
            log_prob = log_prob + dist.log_prob(uid)
            decoded.unit_id = uid.item()

        elif atype == ActionType.RESEARCH_UPGRADE:
            dist = Categorical(logits=self.research_head(state))
            upg = dist.sample()
            log_prob = log_prob + dist.log_prob(upg)
            decoded.upgrade_id = upg.item()

        elif atype == ActionType.ATTACK_UNIT and entities is not None:
            scores = self.attack_ptr(state, entities, entity_mask)
            dist = Categorical(logits=scores)
            idx = dist.sample()
            log_prob = log_prob + dist.log_prob(idx)
            decoded.target_unit_idx = idx.item()

        decoded.log_prob = log_prob.item()
        return decoded, log_prob

    def get_valid_action_mask(self, game_info: Dict) -> torch.Tensor:
        """Build action type mask from game_info dict."""
        mask = torch.ones(NUM_ACTION_TYPES, dtype=torch.bool)
        if not game_info.get("can_build", True):
            mask[ActionType.BUILD_STRUCTURE] = False
        if not game_info.get("can_train", True):
            mask[ActionType.TRAIN_UNIT] = False
        if not game_info.get("can_research", False):
            mask[ActionType.RESEARCH_UPGRADE] = False
        if game_info.get("enemy_units", 0) == 0:
            mask[ActionType.ATTACK_UNIT] = False
        return mask
