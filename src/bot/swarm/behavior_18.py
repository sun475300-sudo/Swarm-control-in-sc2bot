"""
Swarm behavior #18 — strategy: ``random_jitter``.

This module wraps the :func:`src.bot.swarm._strategies.random_jitter` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior18:
    """Swarm behavior #18 (random_jitter)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_18"
        self.strategy = "random_jitter"
        self.magnitude = 0.5
        self.seed = 0

    def tick(self, positions: list) -> list:
        """Apply the random_jitter strategy to ``positions``."""
        return strategies.random_jitter(
            positions, magnitude=self.magnitude, seed=self.seed
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
