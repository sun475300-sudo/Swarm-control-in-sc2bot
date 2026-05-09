"""
Swarm behavior #6 — strategy: ``circle_target``.

This module wraps the :func:`src.bot.swarm._strategies.circle_target` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior06:
    """Swarm behavior #6 (circle_target)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_06"
        self.strategy = "circle_target"
        self.target = (0.0, 0.0)
        self.radius = 5.0

    def tick(self, positions: list) -> list:
        """Apply the circle_target strategy to ``positions``."""
        return strategies.circle_target(
            positions, target=self.target, radius=self.radius
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
