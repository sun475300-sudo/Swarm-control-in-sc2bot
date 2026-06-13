"""
Swarm behavior #27 — strategy: ``ring_contract``.

This module wraps the :func:`src.bot.swarm._strategies.ring_contract` primitive
and exposes the legacy ``BehaviorNN`` API used elsewhere in the bot.
"""

from __future__ import annotations

from . import _strategies as strategies
from .formation_controller import FormationController


class Behavior27:
    """Swarm behavior #27 (ring_contract)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_27"
        self.strategy = "ring_contract"
        self.factor = 0.2

    def tick(self, positions: list) -> list:
        """Apply the ring_contract strategy to ``positions``."""
        return strategies.ring_contract(positions, factor=self.factor)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy!r})"
