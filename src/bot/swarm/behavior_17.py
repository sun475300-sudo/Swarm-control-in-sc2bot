"""
Swarm behavior #17 — strategy: ``pursue_closest``.

This module wraps the :func:`src.bot.swarm._strategies.pursue_closest` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior17:
    """Swarm behavior #17 (pursue_closest)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_17"
        self.strategy = "pursue_closest"
        self.targets = ((10.0, 0.0),)
        self.step = 1.0

    def tick(self, positions: list) -> list:
        """Apply the pursue_closest strategy to ``positions``."""
        return strategies.pursue_closest(
            positions, targets=self.targets, step=self.step
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
