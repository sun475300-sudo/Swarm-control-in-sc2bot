# Phase 617: World Model (Dreamer-inspired) for SC2 Imagination-Based Planning
from .sc2_world_model import (
    RSSM,
    RSSMState,
    SC2WorldModel,
    DreamerActor,
    DreamerCritic,
    KLManager,
    SequenceBuffer,
    TimeStep,
    ObservationDecoder,
    RewardPredictor,
    ContinuePredictor,
    LatentVisualizer,
    SC2EnvSimulator,
    run_demo,
)

# Backwards-compatible aliases (older API names)
WorldModel = SC2WorldModel
DreamerAgent = SC2WorldModel
LatentImagination = LatentVisualizer
demo = run_demo

__all__ = [
    "RSSM",
    "RSSMState",
    "SC2WorldModel",
    "DreamerActor",
    "DreamerCritic",
    "KLManager",
    "SequenceBuffer",
    "TimeStep",
    "ObservationDecoder",
    "RewardPredictor",
    "ContinuePredictor",
    "LatentVisualizer",
    "SC2EnvSimulator",
    "run_demo",
    "WorldModel",
    "DreamerAgent",
    "LatentImagination",
    "demo",
]
