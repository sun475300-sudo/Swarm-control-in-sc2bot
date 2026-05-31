"""
Swarm behavior #25 — strategy: ``vortex``.

This module wraps the :func:`src.bot.swarm._strategies.vortex` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

import math

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior25:
    """Swarm behavior #25 (vortex)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_25"
        self.strategy = "vortex"
        self.angle = math.pi / 12

    def tick(self, positions: list) -> list:
        """Apply the vortex strategy to ``positions``."""
        return strategies.vortex(positions, angle=self.angle)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
