# Phase 617: World Model (Dreamer-inspired) for SC2 Imagination-Based Planning
try:
    from .sc2_world_model import (
        RSSM,
        DreamerAgent,
        LatentImagination,
        WorldModel,
        demo,
    )
except ImportError:
    RSSM = None
    DreamerAgent = None
    LatentImagination = None
    WorldModel = None
    demo = None

__all__ = [
    "RSSM",
    "WorldModel",
    "DreamerAgent",
    "LatentImagination",
    "demo",
]
