# Phase 619: Communication Learning for SC2 Multi-Agent Coordination
from .sc2_comm_agent import (
    CommConfig,
    SC2CommAgent,
    NumpyCommNet,
    NumpyTarMAC,
    ProtocolAnalyzer,
)

# Backwards-compatible aliases (older API names)
CommNet = NumpyCommNet
TarMAC = NumpyTarMAC
CommAgent = SC2CommAgent
CommChannel = SC2CommAgent  # the agent owns the channel abstraction

__all__ = [
    "CommConfig",
    "SC2CommAgent",
    "NumpyCommNet",
    "NumpyTarMAC",
    "ProtocolAnalyzer",
    "CommNet",
    "TarMAC",
    "CommAgent",
    "CommChannel",
]
