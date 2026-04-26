# Phase 606: MAPPO - Multi-Agent PPO for SC2 Unit Coordination
try:
    from .sc2_mappo_agent import (
        MAPPOConfig,
        SC2MAPPOAgent,
        SharedObsEncoderNumpy,
        CentralizedCriticNumpy,
        DecentralizedActorNumpy,
        MultiAgentRolloutBuffer,
        ELOLeague,
        PBTManager,
    )
except Exception:  # pragma: no cover - tolerate missing optional deps
    pass
