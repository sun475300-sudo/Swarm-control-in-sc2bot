# Phase 619: Communication Learning for SC2 Multi-Agent Coordination
# Re-export the canonical NumPy/torch-aware classes. Uses a try/except so that
# importing the submodule directly still works even when optional torch-only
# names are unavailable.
try:
    from .sc2_comm_agent import (
        CommConfig,
        ProtocolAnalyzer,
        NumpyCommNet,
        NumpyTarMAC,
        SC2CommAgent,
    )
except Exception:  # pragma: no cover - tolerate missing optional deps
    pass
