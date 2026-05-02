# Phase 619: Communication Learning for SC2 Multi-Agent Coordination
#
# Wrapped re-exports keep the submodule importable even if optional
# deps (PyTorch) are missing or symbol names drift.

try:  # pragma: no cover - re-export safety net
    from .sc2_comm_agent import (
        CommConfig,
        NumpyCommNet,
        NumpyTarMAC,
        ProtocolAnalyzer,
        SC2CommAgent,
    )

    # Backwards-compatible aliases (legacy import paths)
    CommAgent = SC2CommAgent
    CommNet = NumpyCommNet
    TarMAC = NumpyTarMAC
    CommChannel = ProtocolAnalyzer
except Exception:  # noqa: BLE001 - keep submodule importable
    pass
