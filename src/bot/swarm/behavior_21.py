"""
Swarm behavior #21 — strategy: ``scout``.

This module wraps the :func:`src.bot.swarm._strategies.scout` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior21:
    """Swarm behavior #21 (scout)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_21"
        self.strategy = "scout"
        self.origin = (0.0, 0.0)
        self.distance = 5.0

    def tick(self, positions: list) -> list:
        """Apply the scout strategy to ``positions``."""
        return strategies.scout(positions, origin=self.origin, distance=self.distance)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
