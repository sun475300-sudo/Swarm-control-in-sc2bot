"""
Swarm behavior #15 — strategy: ``regroup``.

This module wraps the :func:`src.bot.swarm._strategies.regroup` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior15:
    """Swarm behavior #15 (regroup)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_15"
        self.strategy = "regroup"
        self.factor = 0.5

    def tick(self, positions: list) -> list:
        """Apply the regroup strategy to ``positions``."""
        return strategies.regroup(positions, factor=self.factor)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
