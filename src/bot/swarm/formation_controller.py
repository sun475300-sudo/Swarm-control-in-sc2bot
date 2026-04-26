"""Formation controller used by every ``Behavior01..30`` placeholder.

The 30 ``behavior_*.py`` modules all do::

    from .formation_controller import FormationController
    ...
    self.controller = FormationController()
    return self.controller.maintain_formation(positions)

…but the file backing that import was missing, so every single
``Behavior*`` class raised ``ModuleNotFoundError`` at import time.

This module supplies the contract the placeholders rely on:
:meth:`maintain_formation` returns a list of target positions of the
same length and shape as the input. The default implementation is an
identity (units stay where they are), which is a safe no-op until the
real swarm logic is filled in.
"""
from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

# A position can be a 2-tuple, a 3-tuple, or any sequence of floats.
Position = Sequence[float]


class FormationController:
    """Minimal, side-effect-free controller.

    Designed to be cheap to instantiate (the placeholder behaviors do
    so per-tick today) and trivially testable.
    """

    def __init__(self, name: str = "default") -> None:
        self.name = name

    def maintain_formation(self, positions: Iterable[Position]) -> List[Tuple[float, ...]]:
        """Return target positions for the given units.

        The default is identity — preserves length, ordering, and shape.
        Subclasses or a future real implementation can re-target units
        without breaking the call site contract.
        """
        result: List[Tuple[float, ...]] = []
        for p in positions:
            # Defensive copy: callers often mutate their own input list.
            result.append(tuple(float(v) for v in p))
        return result

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"FormationController(name={self.name!r})"
