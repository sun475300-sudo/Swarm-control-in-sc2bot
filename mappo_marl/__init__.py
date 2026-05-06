# Phase 606: MAPPO - Multi-Agent PPO for SC2 Unit Coordination
# Re-exports the stable public API. Older names (ActorNetwork, MAPPOAgent,
# MAPPOTrainer, SharedCritic) were renamed during the NumPy-fallback
# refactor; the __init__ was not updated so any `import mappo_marl` raised
# ImportError at module load and silently skipped TestMAPPO.
from .sc2_mappo_agent import (
    CentralizedCriticNumpy,
    DecentralizedActorNumpy,
    MAPPOConfig,
    MultiAgentRolloutBuffer,
    SC2MAPPOAgent,
    SharedObsEncoderNumpy,
)

__all__ = [
    "CentralizedCriticNumpy",
    "DecentralizedActorNumpy",
    "MAPPOConfig",
    "MultiAgentRolloutBuffer",
    "SC2MAPPOAgent",
    "SharedObsEncoderNumpy",
]
