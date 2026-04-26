# Phase 619: Communication Learning for SC2 Multi-Agent Coordination
#
# The names re-exported here must exist as top-level symbols in
# sc2_comm_agent.py. Previously this file imported CommChannel / CommNet /
# TarMAC / CommAgent — none of which existed — so `import comm_learning`
# raised ImportError and the P619 tests all failed.
from .sc2_comm_agent import (
    CommConfig,
    ProtocolAnalyzer,
    NumpyCommNet,
    NumpyTarMAC,
    SC2CommAgent,
    TORCH_AVAILABLE,
)

__all__ = [
    "CommConfig",
    "ProtocolAnalyzer",
    "NumpyCommNet",
    "NumpyTarMAC",
    "SC2CommAgent",
    "TORCH_AVAILABLE",
]
