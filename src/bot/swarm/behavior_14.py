"""
Swarm behavior #14 — strategy: ``patrol``.

This module wraps the :func:`src.bot.swarm._strategies.patrol` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior14:
    """Swarm behavior #14 (patrol)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_14"
        self.strategy = "patrol"
        self.waypoint_a = (0.0, 0.0)
        self.waypoint_b = (10.0, 0.0)
        self.progress = 0.5

    def tick(self, positions: list) -> list:
        """Apply the patrol strategy to ``positions``."""
        return strategies.patrol(
            positions,
            waypoint_a=self.waypoint_a,
            waypoint_b=self.waypoint_b,
            progress=self.progress,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
