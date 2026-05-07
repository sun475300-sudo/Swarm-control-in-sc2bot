# Phase 617: World Model (Dreamer-inspired) for SC2 Imagination-Based Planning
from .sc2_world_model import (
    RSSM,
    DreamerActor,
    DreamerCritic,
    LatentVisualizer,
    SC2WorldModel,
    run_demo,
)

# Backward-compat aliases for older imports
WorldModel = SC2WorldModel
DreamerAgent = DreamerActor
LatentImagination = LatentVisualizer
demo = run_demo

__all__ = [
    "RSSM",
    "SC2WorldModel",
    "DreamerActor",
    "DreamerCritic",
    "LatentVisualizer",
    "run_demo",
    # aliases
    "WorldModel",
    "DreamerAgent",
    "LatentImagination",
    "demo",
]
