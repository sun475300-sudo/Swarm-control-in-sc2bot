"""
Swarm behavior #5 — strategy: ``retreat``.

This module wraps the :func:`src.bot.swarm._strategies.retreat` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior05:
    """Swarm behavior #5 (retreat)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_05"
        self.strategy = "retreat"
        self.threat = (0.0, 0.0)
        self.step = 1.0

    def tick(self, positions: list) -> list:
        """Apply the retreat strategy to ``positions``."""
        return strategies.retreat(positions, threat=self.threat, step=self.step)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
