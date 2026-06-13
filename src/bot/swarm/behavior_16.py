"""
Swarm behavior #16 — strategy: ``flee``.

This module wraps the :func:`src.bot.swarm._strategies.flee` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior16:
    """Swarm behavior #16 (flee)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_16"
        self.strategy = "flee"
        self.threat = (0.0, 0.0)
        self.step = 2.0

    def tick(self, positions: list) -> list:
        """Apply the flee strategy to ``positions``."""
        return strategies.flee(positions, threat=self.threat, step=self.step)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
