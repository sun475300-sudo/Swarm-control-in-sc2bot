# Phase 606: MAPPO - Multi-Agent PPO for SC2 Unit Coordination
#
# Re-exports are wrapped in try/except so that an importable submodule
# (e.g. via `from mappo_marl.sc2_mappo_agent import MAPPOConfig`) keeps
# working even if optional deps like PyTorch are missing or a re-exported
# symbol gets renamed.

try:  # pragma: no cover - re-export safety net
    from .sc2_mappo_agent import (
        CentralizedCriticNumpy,
        CentralizedCriticTorch,
        DecentralizedActorNumpy,
        DecentralizedActorTorch,
        MAPPOConfig,
        SC2MAPPOAgent,
        SharedObsEncoderNumpy,
        SharedObsEncoderTorch,
    )

    # Backwards-compatible aliases (legacy import paths)
    MAPPOAgent = SC2MAPPOAgent
    MAPPOTrainer = SC2MAPPOAgent
    ActorNetwork = DecentralizedActorNumpy
    SharedCritic = CentralizedCriticNumpy
except Exception:  # noqa: BLE001 - we deliberately swallow to keep submodule importable
    pass
