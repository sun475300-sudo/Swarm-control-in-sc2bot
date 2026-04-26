# Phase 617: World Model (Dreamer-inspired) for SC2 Imagination-Based Planning
try:
    from .sc2_world_model import (
        RSSM,
        SC2WorldModel,
        DreamerActor,
        DreamerCritic,
        LatentVisualizer,
        SC2EnvSimulator,
    )
except Exception:  # pragma: no cover - tolerate missing optional deps
    pass

__all__ = [
    "RSSM",
    "SC2WorldModel",
    "DreamerActor",
    "DreamerCritic",
    "LatentVisualizer",
    "SC2EnvSimulator",
]
