"""
Swarm behavior #12 — strategy: ``encircle``.

This module wraps the :func:`src.bot.swarm._strategies.encircle` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior12:
    """Swarm behavior #12 (encircle)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_12"
        self.strategy = "encircle"
        self.target = (0.0, 0.0)
        self.radius = 5.0

    def tick(self, positions: list) -> list:
        """Apply the encircle strategy to ``positions``."""
        return strategies.encircle(positions, target=self.target, radius=self.radius)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
