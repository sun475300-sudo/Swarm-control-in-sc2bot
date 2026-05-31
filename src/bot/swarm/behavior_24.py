"""
Swarm behavior #24 — strategy: ``split_groups``.

This module wraps the :func:`src.bot.swarm._strategies.split_groups` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior24:
    """Swarm behavior #24 (split_groups)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_24"
        self.strategy = "split_groups"
        self.target_a = (10.0, 0.0)
        self.target_b = (-10.0, 0.0)
        self.step = 1.0

    def tick(self, positions: list) -> list:
        """Apply the split_groups strategy to ``positions``."""
        return strategies.split_groups(
            positions, target_a=self.target_a, target_b=self.target_b, step=self.step
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
