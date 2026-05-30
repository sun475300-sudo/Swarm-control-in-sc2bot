# Phase 619: Communication Learning for SC2 Multi-Agent Coordination
try:
    from .sc2_comm_agent import (
        CommConfig,
        NumpyCommNet,
        NumpyTarMAC,
        ProtocolAnalyzer,
        SC2CommAgent,
    )
except ImportError:
    CommConfig = None
    SC2CommAgent = None
    NumpyCommNet = None
    NumpyTarMAC = None
    ProtocolAnalyzer = None

# Backward-compat aliases (original API names used by older code)
CommAgent = SC2CommAgent
CommNet = NumpyCommNet
TarMAC = NumpyTarMAC


class CommChannel:
    """Stub retained for API compatibility. No-op placeholder."""

    pass


__all__ = [
    "CommConfig",
    "SC2CommAgent",
    "NumpyCommNet",
    "NumpyTarMAC",
    "ProtocolAnalyzer",
    "CommAgent",
    "CommNet",
    "TarMAC",
    "CommChannel",
]
