"""
Swarm behavior #11 — strategy: ``kite``.

This module wraps the :func:`src.bot.swarm._strategies.kite` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior11:
    """Swarm behavior #11 (kite)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_11"
        self.strategy = "kite"
        self.target = (10.0, 0.0)
        self.advance = 1.0
        self.retreat_step = 0.5

    def tick(self, positions: list) -> list:
        """Apply the kite strategy to ``positions``."""
        return strategies.kite(
            positions,
            target=self.target,
            advance=self.advance,
            retreat_step=self.retreat_step,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
