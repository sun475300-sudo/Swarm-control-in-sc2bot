# Phase 606: MAPPO - Multi-Agent PPO for SC2 Unit Coordination
from .sc2_mappo_agent import (
    MAPPOConfig,
    SC2MAPPOAgent,
    CentralizedCriticNumpy,
    CentralizedCriticTorch,
    DecentralizedActorNumpy,
    DecentralizedActorTorch,
    MultiAgentRolloutBuffer,
    ELOLeague,
    PBTManager,
)

# Backwards-compatible aliases (older API names)
MAPPOAgent = SC2MAPPOAgent
MAPPOTrainer = SC2MAPPOAgent
SharedCritic = CentralizedCriticNumpy
ActorNetwork = DecentralizedActorNumpy

__all__ = [
    "MAPPOConfig",
    "SC2MAPPOAgent",
    "CentralizedCriticNumpy",
    "CentralizedCriticTorch",
    "DecentralizedActorNumpy",
    "DecentralizedActorTorch",
    "MultiAgentRolloutBuffer",
    "ELOLeague",
    "PBTManager",
    "MAPPOAgent",
    "MAPPOTrainer",
    "SharedCritic",
    "ActorNetwork",
]
