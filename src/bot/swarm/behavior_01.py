"""
Swarm behavior #1 — strategy: ``cohere``.

This module wraps the :func:`src.bot.swarm._strategies.cohere` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior01:
    """Swarm behavior #1 (cohere)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_01"
        self.strategy = "cohere"
        self.factor = 0.25

    def tick(self, positions: list) -> list:
        """Apply the cohere strategy to ``positions``."""
        return strategies.cohere(positions, factor=self.factor)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
