# Phase 619: Communication Learning for SC2 Multi-Agent Coordination
# Re-exports the stable public API. Older names (CommAgent, CommChannel,
# CommNet, TarMAC) were renamed during the NumPy-fallback refactor; the
# __init__ was not updated, which made `import comm_learning` raise an
# ImportError and silently skipped TestCommLearning. Sync the surface here.
from .sc2_comm_agent import (
    CommConfig,
    NumpyCommNet,
    NumpyTarMAC,
    ProtocolAnalyzer,
    SC2CommAgent,
)

__all__ = [
    "CommConfig",
    "NumpyCommNet",
    "NumpyTarMAC",
    "ProtocolAnalyzer",
    "SC2CommAgent",
]
