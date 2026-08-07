"""
Swarm behavior #28 — strategy: ``zigzag``.

This module wraps the :func:`src.bot.swarm._strategies.zigzag` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior28:
    """Swarm behavior #28 (zigzag)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_28"
        self.strategy = "zigzag"
        self.target = (10.0, 0.0)
        self.step = 1.0
        self.lateral = 0.5
        self.phase = 0

    def tick(self, positions: list) -> list:
        """Apply the zigzag strategy to ``positions``."""
        return strategies.zigzag(
            positions,
            target=self.target,
            step=self.step,
            lateral=self.lateral,
            phase=self.phase,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
