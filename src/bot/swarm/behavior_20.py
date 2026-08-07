"""
Swarm behavior #20 — strategy: ``charge``.

This module wraps the :func:`src.bot.swarm._strategies.charge` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior20:
    """Swarm behavior #20 (charge)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_20"
        self.strategy = "charge"
        self.target = (10.0, 0.0)
        self.step = 3.0

    def tick(self, positions: list) -> list:
        """Apply the charge strategy to ``positions``."""
        return strategies.charge(positions, target=self.target, step=self.step)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
