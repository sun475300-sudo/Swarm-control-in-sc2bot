# Phase 606: MAPPO - Multi-Agent PPO for SC2 Unit Coordination
#
# 본 패키지의 실제 공개 심볼은 sc2_mappo_agent.py에 정의되어 있다.
# 과거 __init__.py가 존재하지 않는 (MAPPOAgent / MAPPOTrainer /
# SharedCritic / ActorNetwork) 이름들을 import하려 시도하여
# `from mappo_marl import ...` 자체가 ImportError로 깨졌다.
# 실제 클래스 이름들로 재export한다 — 외부 코드는 sc2_mappo_agent를 직접
# import 해도 무방.
from .sc2_mappo_agent import (
    MAPPOConfig,
    SC2MAPPOAgent,
    MultiAgentRolloutBuffer,
    ELOLeague,
    PBTManager,
)

__all__ = [
    "MAPPOConfig",
    "SC2MAPPOAgent",
    "MultiAgentRolloutBuffer",
    "ELOLeague",
    "PBTManager",
]
