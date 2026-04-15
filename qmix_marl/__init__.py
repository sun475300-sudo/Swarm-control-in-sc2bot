# Phase 607: QMIX - Value Decomposition for SC2 Cooperative Play
from .sc2_qmix_agent import (
    QMIXConfig,
    QMIXMixingNetNumpy,
    AgentQNetNumpy,
    PrioritizedReplayBuffer,
    SC2QMIXAgent,
)

# Backwards-compatible aliases
QMIXMixingNetwork = QMIXMixingNetNumpy
AgentQNetwork = AgentQNetNumpy
ReplayBuffer = PrioritizedReplayBuffer
QMIXTrainer = SC2QMIXAgent
