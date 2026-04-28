# Phase 607: QMIX - Value Decomposition for SC2 Cooperative Play
from .sc2_qmix_agent import (
    AgentQNetNumpy,
    PrioritizedReplayBuffer,
    QMIXConfig,
    QMIXMixingNetNumpy,
    SC2QMIXAgent,
)

# Backwards-compatible aliases
QMIXMixingNetwork = QMIXMixingNetNumpy
AgentQNetwork = AgentQNetNumpy
ReplayBuffer = PrioritizedReplayBuffer
QMIXTrainer = SC2QMIXAgent
