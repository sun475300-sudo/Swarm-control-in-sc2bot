"""Swarm behavior package.

Exposes the :class:`FormationController` and the 30 ``BehaviorNN`` classes so
they can be enumerated by index without manual imports.
"""

from __future__ import annotations

from importlib import import_module
from typing import Dict, List, Type

from .formation_controller import FormationController

NUM_BEHAVIORS = 30


def _load_behavior(index: int) -> Type:
    module = import_module(f".behavior_{index:02d}", package=__name__)
    return getattr(module, f"Behavior{index:02d}")


BEHAVIORS: Dict[int, Type] = {i: _load_behavior(i) for i in range(1, NUM_BEHAVIORS + 1)}


def all_behaviors() -> List:
    """Instantiate every registered behavior in index order."""
    return [BEHAVIORS[i]() for i in range(1, NUM_BEHAVIORS + 1)]


__all__ = [
    "BEHAVIORS",
    "FormationController",
    "NUM_BEHAVIORS",
    "all_behaviors",
]
