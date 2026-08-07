"""
Swarm behavior #10 — strategy: ``spread``.

This module wraps the :func:`src.bot.swarm._strategies.spread` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior10:
    """Swarm behavior #10 (spread)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_10"
        self.strategy = "spread"
        self.min_distance = 2.0
        self.iterations = 5

    def tick(self, positions: list) -> list:
        """Apply the spread strategy to ``positions``."""
        return strategies.spread(
            positions, min_distance=self.min_distance, iterations=self.iterations
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
