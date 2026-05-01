# Phase 606: MAPPO - Multi-Agent PPO for SC2 Unit Coordination
from .sc2_mappo_agent import (
    CentralizedCriticNumpy,
    DecentralizedActorNumpy,
    ELOLeague,
    MAPPOConfig,
    MultiAgentRolloutBuffer,
    PBTManager,
    SC2MAPPOAgent,
    SharedObsEncoderNumpy,
    SyntheticSC2MultiAgentEnv,
)

# Backwards-compatible aliases (legacy names used in older docs/tests)
ActorNetwork = DecentralizedActorNumpy
SharedCritic = CentralizedCriticNumpy
MAPPOAgent = SC2MAPPOAgent
MAPPOTrainer = SC2MAPPOAgent

__all__ = [
    "ActorNetwork",
    "CentralizedCriticNumpy",
    "DecentralizedActorNumpy",
    "ELOLeague",
    "MAPPOAgent",
    "MAPPOConfig",
    "MAPPOTrainer",
    "MultiAgentRolloutBuffer",
    "PBTManager",
    "SC2MAPPOAgent",
    "SharedCritic",
    "SharedObsEncoderNumpy",
    "SyntheticSC2MultiAgentEnv",
]
