# Phase 617: World Model (Dreamer-inspired) for SC2 Imagination-Based Planning
from .sc2_world_model import (
    RSSM,
    ContinuePredictor,
    DreamerActor,
    DreamerCritic,
    KLManager,
    ObservationDecoder,
    RewardPredictor,
    RSSMState,
    SC2WorldModel,
    SequenceBuffer,
    run_demo,
)

# Backwards-compatible aliases (legacy names referenced by older callers / tests).
WorldModel = SC2WorldModel
DreamerAgent = SC2WorldModel
LatentImagination = DreamerActor
demo = run_demo

__all__ = [
    "RSSM",
    "RSSMState",
    "SC2WorldModel",
    "DreamerActor",
    "DreamerCritic",
    "ObservationDecoder",
    "RewardPredictor",
    "ContinuePredictor",
    "KLManager",
    "SequenceBuffer",
    "run_demo",
    "WorldModel",
    "DreamerAgent",
    "LatentImagination",
    "demo",
]
