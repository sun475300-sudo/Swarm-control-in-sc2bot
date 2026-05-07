# Phase 619: Communication Learning for SC2 Multi-Agent Coordination
#
# Re-export the always-available core classes; the torch-only classes
# (CommNetModule, TarMACModule, etc.) are exposed lazily via __getattr__
# so that this package imports cleanly when torch is absent.
from .sc2_comm_agent import (
    CommConfig,
    NumpyCommNet,
    NumpyTarMAC,
    ProtocolAnalyzer,
    SC2CommAgent,
)

# Backwards-compatible aliases (legacy names — prefer the explicit ones above)
CommAgent = SC2CommAgent
CommNet = NumpyCommNet
TarMAC = NumpyTarMAC


def __getattr__(name):
    """Lazy access to torch-only classes; returns None when torch is absent."""
    if name in {
        "MessageGate",
        "CommNetModule",
        "TarMACModule",
        "HierarchicalCommModule",
        "CommPolicyNetwork",
        "CommChannel",
    }:
        from . import sc2_comm_agent as _impl

        if name == "CommChannel":
            # Legacy alias — point to the torch CommNet module if available.
            return getattr(_impl, "CommNetModule", None)
        return getattr(_impl, name, None)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
