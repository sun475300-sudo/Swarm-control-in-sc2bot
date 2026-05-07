# Phase 617: World Model (Dreamer-inspired) for SC2 Imagination-Based Planning
#
# The actual implementations are: RSSM (recurrent state-space model),
# DreamerActor + DreamerCritic, ObservationDecoder, RewardPredictor,
# ContinuePredictor, SC2WorldModel. The legacy names (DreamerAgent,
# LatentImagination, WorldModel, demo) are not defined in
# sc2_world_model.py — we provide back-compat aliases here.
from .sc2_world_model import (
    RSSM,
    ContinuePredictor,
    DreamerActor,
    DreamerCritic,
    KLManager,
    LatentVisualizer,
    ObservationDecoder,
    RewardPredictor,
    RSSMState,
    SC2WorldModel,
    SequenceBuffer,
)

# Backwards-compatible aliases (legacy names — prefer the explicit ones above)
WorldModel = SC2WorldModel
DreamerAgent = SC2WorldModel
LatentImagination = LatentVisualizer  # closest available equivalent


def demo():
    """Backwards-compatible no-op demo entrypoint."""
    print("world_model.demo: see world_model.sc2_world_model.main() for the demo.")


__all__ = [
    "RSSM",
    "RSSMState",
    "SequenceBuffer",
    "KLManager",
    "ObservationDecoder",
    "RewardPredictor",
    "ContinuePredictor",
    "DreamerActor",
    "DreamerCritic",
    "LatentVisualizer",
    "SC2WorldModel",
    # Legacy aliases:
    "WorldModel",
    "DreamerAgent",
    "LatentImagination",
    "demo",
]
