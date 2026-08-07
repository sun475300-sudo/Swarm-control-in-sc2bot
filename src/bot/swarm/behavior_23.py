"""
Swarm behavior #23 — strategy: ``defend``.

This module wraps the :func:`src.bot.swarm._strategies.defend` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior23:
    """Swarm behavior #23 (defend)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_23"
        self.strategy = "defend"
        self.base = (0.0, 0.0)
        self.radius = 3.0

    def tick(self, positions: list) -> list:
        """Apply the defend strategy to ``positions``."""
        return strategies.defend(positions, base=self.base, radius=self.radius)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
