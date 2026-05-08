# Phase 617: World Model (Dreamer-inspired) for SC2 Imagination-Based Planning
from .sc2_world_model import (
    RSSM,
    DreamerActor,
    DreamerCritic,
    SC2EnvSimulator,
    SC2WorldModel,
)

# Back-compat aliases for the historical public surface.
WorldModel = SC2WorldModel
DreamerAgent = DreamerActor

__all__ = [
    "RSSM",
    "SC2WorldModel",
    "WorldModel",
    "DreamerActor",
    "DreamerAgent",
    "DreamerCritic",
    "SC2EnvSimulator",
]
