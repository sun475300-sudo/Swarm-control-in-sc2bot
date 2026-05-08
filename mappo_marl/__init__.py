# Phase 606: MAPPO - Multi-Agent PPO for SC2 Unit Coordination
try:
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
except ImportError:
    MAPPOConfig = None
    SC2MAPPOAgent = None
    CentralizedCriticNumpy = None
    CentralizedCriticTorch = None
    DecentralizedActorNumpy = None
    DecentralizedActorTorch = None
    MultiAgentRolloutBuffer = None
    ELOLeague = None
    PBTManager = None

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
