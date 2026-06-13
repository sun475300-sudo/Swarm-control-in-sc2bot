"""
Swarm behavior #22 — strategy: ``ambush``.

This module wraps the :func:`src.bot.swarm._strategies.ambush` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior22:
    """Swarm behavior #22 (ambush)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_22"
        self.strategy = "ambush"
        self.ambush_point = (5.0, 5.0)
        self.step = 1.0

    def tick(self, positions: list) -> list:
        """Apply the ambush strategy to ``positions``."""
        return strategies.ambush(
            positions, ambush_point=self.ambush_point, step=self.step
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
