# Phase 617: World Model (Dreamer-inspired) for SC2 Imagination-Based Planning
from .sc2_world_model import (
    RSSM,
    DreamerActor,
    DreamerCritic,
    KLManager,
    LatentVisualizer,
    SC2WorldModel,
)

# Backwards-compatible aliases for the older public API.
WorldModel = SC2WorldModel
DreamerAgent = SC2WorldModel
LatentImagination = LatentVisualizer

__all__ = [
    "RSSM",
    "SC2WorldModel",
    "DreamerActor",
    "DreamerCritic",
    "KLManager",
    "LatentVisualizer",
    # Aliases
    "WorldModel",
    "DreamerAgent",
    "LatentImagination",
]
