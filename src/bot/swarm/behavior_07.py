"""
Swarm behavior #7 — strategy: ``line_formation``.

This module wraps the :func:`src.bot.swarm._strategies.line_formation` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior07:
    """Swarm behavior #7 (line_formation)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_07"
        self.strategy = "line_formation"
        self.origin = (0.0, 0.0)
        self.spacing = 1.0
        self.axis = "x"

    def tick(self, positions: list) -> list:
        """Apply the line_formation strategy to ``positions``."""
        return strategies.line_formation(
            positions, origin=self.origin, spacing=self.spacing, axis=self.axis
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
