"""
Swarm behavior #4 — strategy: ``attack_move``.

This module wraps the :func:`src.bot.swarm._strategies.attack_move` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior04:
    """Swarm behavior #4 (attack_move)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_04"
        self.strategy = "attack_move"
        self.target = (10.0, 0.0)
        self.step = 1.0

    def tick(self, positions: list) -> list:
        """Apply the attack_move strategy to ``positions``."""
        return strategies.attack_move(positions, target=self.target, step=self.step)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
