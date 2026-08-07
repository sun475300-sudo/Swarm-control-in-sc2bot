"""
Swarm behavior #3 — strategy: ``hold``.

This module wraps the :func:`src.bot.swarm._strategies.hold` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior03:
    """Swarm behavior #3 (hold)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_03"
        self.strategy = "hold"
        self._noop = None

    def tick(self, positions: list) -> list:
        """Apply the hold strategy to ``positions``."""
        return strategies.hold(positions)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
