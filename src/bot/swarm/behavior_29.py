"""
Swarm behavior #29 — strategy: ``bait``.

This module wraps the :func:`src.bot.swarm._strategies.bait` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior29:
    """Swarm behavior #29 (bait)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_29"
        self.strategy = "bait"
        self.target = (10.0, 0.0)
        self.retreat_point = (-5.0, 0.0)
        self.bait_step = 1.0
        self.retreat_step = 1.0

    def tick(self, positions: list) -> list:
        """Apply the bait strategy to ``positions``."""
        return strategies.bait(
            positions,
            target=self.target,
            retreat_point=self.retreat_point,
            bait_step=self.bait_step,
            retreat_step=self.retreat_step,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
