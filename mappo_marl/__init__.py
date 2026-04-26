# Phase 606: MAPPO - Multi-Agent PPO for SC2 Unit Coordination
#
# The names re-exported here must exist as top-level symbols in
# sc2_mappo_agent.py. Previously this file imported MAPPOAgent /
# MAPPOTrainer / SharedCritic / ActorNetwork — none of which existed —
# so `import mappo_marl` raised ImportError and all P606 tests failed.
from .sc2_mappo_agent import (
    MAPPOConfig,
    MultiAgentRolloutBuffer,
    SC2MAPPOAgent,
    ELOLeague,
    PBTManager,
    HAS_TORCH,
)

__all__ = [
    "MAPPOConfig",
    "MultiAgentRolloutBuffer",
    "SC2MAPPOAgent",
    "ELOLeague",
    "PBTManager",
    "HAS_TORCH",
]
