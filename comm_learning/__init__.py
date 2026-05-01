# Phase 619: Communication Learning for SC2 Multi-Agent Coordination
from .sc2_comm_agent import (
    CommConfig,
    NumpyCommNet,
    NumpyTarMAC,
    ProtocolAnalyzer,
    SC2CommAgent,
)

# Backwards-compatible aliases
CommAgent = SC2CommAgent
CommNet = NumpyCommNet
TarMAC = NumpyTarMAC

__all__ = [
    "CommAgent",
    "CommConfig",
    "CommNet",
    "NumpyCommNet",
    "NumpyTarMAC",
    "ProtocolAnalyzer",
    "SC2CommAgent",
    "TarMAC",
]
