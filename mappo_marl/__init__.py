# Phase 606: MAPPO - Multi-Agent PPO for SC2 Unit Coordination
from .sc2_mappo_agent import (
    CentralizedCriticNumpy,
    CentralizedCriticTorch,
    DecentralizedActorNumpy,
    DecentralizedActorTorch,
    MAPPOConfig,
    MultiAgentRolloutBuffer,
    SC2MAPPOAgent,
    SharedObsEncoderNumpy,
    SharedObsEncoderTorch,
)

# Backwards-compatible aliases
ActorNetwork = DecentralizedActorTorch
SharedCritic = CentralizedCriticTorch
MAPPOAgent = SC2MAPPOAgent
MAPPOTrainer = SC2MAPPOAgent
