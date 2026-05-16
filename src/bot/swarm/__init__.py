"""Swarm behavior package.

Provides a `FormationController` that maintains positions and a set of
auto-generated `BehaviorNN` tick modules built on top of it.
"""

from .formation_controller import FormationController

__all__ = ["FormationController"]
