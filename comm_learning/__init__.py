# Phase 619: Communication Learning for SC2 Multi-Agent Coordination
from .sc2_comm_agent import (
    CommConfig,
    NumpyCommNet,
    NumpyTarMAC,
    ProtocolAnalyzer,
    SC2CommAgent,
)

# Backwards-compatible aliases (legacy names from pre-NumPy-fallback split)
CommAgent = SC2CommAgent
CommChannel = ProtocolAnalyzer
CommNet = NumpyCommNet
TarMAC = NumpyTarMAC

__all__ = [
    "CommConfig",
    "NumpyCommNet",
    "NumpyTarMAC",
    "ProtocolAnalyzer",
    "SC2CommAgent",
    "CommAgent",
    "CommChannel",
    "CommNet",
    "TarMAC",
]
