"""Swarm control sub-package.

Contains :class:`FormationController` and a family of placeholder
``Behavior01..Behavior30`` modules that delegate formation work to it.
"""

from .formation_controller import FormationController

__all__ = ["FormationController"]
