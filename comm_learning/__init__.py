# Phase 619: Communication Learning for SC2 Multi-Agent Coordination
from .sc2_comm_agent import (
    CommConfig,
    NumpyCommNet,
    NumpyTarMAC,
    ProtocolAnalyzer,
    SC2CommAgent,
)

# Backwards-compatible aliases for older import paths
CommAgent = SC2CommAgent
CommNet = NumpyCommNet
TarMAC = NumpyTarMAC
CommChannel = ProtocolAnalyzer
