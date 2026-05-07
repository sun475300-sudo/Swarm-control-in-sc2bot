# Phase 606: MAPPO - Multi-Agent PPO for SC2 Unit Coordination
#
# Re-export the actual classes from sc2_mappo_agent.py and provide
# backwards-compatible aliases for the legacy names that earlier callers
# (and outdated docs) referenced.
from .sc2_mappo_agent import (
    CentralizedCriticNumpy,
    CentralizedCriticTorch,
    DecentralizedActorNumpy,
    DecentralizedActorTorch,
    ELOLeague,
    MAPPOConfig,
    MultiAgentRolloutBuffer,
    PBTManager,
    SC2MAPPOAgent,
    SharedObsEncoderNumpy,
    SharedObsEncoderTorch,
)

# Backwards-compatible aliases (legacy names — prefer the explicit ones above)
ActorNetwork = DecentralizedActorNumpy
SharedCritic = CentralizedCriticNumpy
MAPPOAgent = SC2MAPPOAgent
MAPPOTrainer = SC2MAPPOAgent
