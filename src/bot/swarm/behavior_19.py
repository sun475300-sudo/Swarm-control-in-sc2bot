"""
Swarm behavior #19 — strategy: ``wall_off``.

This module wraps the :func:`src.bot.swarm._strategies.wall_off` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior19:
    """Swarm behavior #19 (wall_off)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_19"
        self.strategy = "wall_off"
        self.choke_a = (0.0, 0.0)
        self.choke_b = (10.0, 0.0)

    def tick(self, positions: list) -> list:
        """Apply the wall_off strategy to ``positions``."""
        return strategies.wall_off(
            positions, choke_a=self.choke_a, choke_b=self.choke_b
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
