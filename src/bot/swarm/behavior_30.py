"""
Swarm behavior #30 — strategy: ``rally``.

This module wraps the :func:`src.bot.swarm._strategies.rally` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior30:
    """Swarm behavior #30 (rally)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_30"
        self.strategy = "rally"
        self.rally_point = (0.0, 0.0)
        self.step = 1.0

    def tick(self, positions: list) -> list:
        """Apply the rally strategy to ``positions``."""
        return strategies.rally(positions, rally_point=self.rally_point, step=self.step)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
