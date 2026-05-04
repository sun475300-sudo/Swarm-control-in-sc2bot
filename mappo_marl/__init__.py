# Phase 606: MAPPO - Multi-Agent PPO for SC2 Unit Coordination
from .sc2_mappo_agent import (
    CentralizedCriticNumpy,
    DecentralizedActorNumpy,
    MAPPOConfig,
    MultiAgentRolloutBuffer,
    SC2MAPPOAgent,
    SharedObsEncoderNumpy,
)

# Backwards-compatible aliases (legacy names referenced before NumPy fallback split)
ActorNetwork = DecentralizedActorNumpy
SharedCritic = CentralizedCriticNumpy
MAPPOAgent = SC2MAPPOAgent
MAPPOTrainer = SC2MAPPOAgent

__all__ = [
    "CentralizedCriticNumpy",
    "DecentralizedActorNumpy",
    "MAPPOConfig",
    "MultiAgentRolloutBuffer",
    "SC2MAPPOAgent",
    "SharedObsEncoderNumpy",
    "ActorNetwork",
    "SharedCritic",
    "MAPPOAgent",
    "MAPPOTrainer",
]
