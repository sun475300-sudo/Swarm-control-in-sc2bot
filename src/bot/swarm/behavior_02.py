"""
Swarm behavior #2 — strategy: ``scatter``.

This module wraps the :func:`src.bot.swarm._strategies.scatter` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior02:
    """Swarm behavior #2 (scatter)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_02"
        self.strategy = "scatter"
        self.factor = 0.25

    def tick(self, positions: list) -> list:
        """Apply the scatter strategy to ``positions``."""
        return strategies.scatter(positions, factor=self.factor)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
