"""Swarm Behavior #01 - Circular Formation Hold."""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position


class Behavior01:
    """Maintain a stable circular formation around group centroid."""

    def __init__(self) -> None:
        self.controller = FormationController(formation_radius=3.0)
        self.name = "circular_formation"

    def tick(self, positions: List[Position]) -> List[Position]:
        return self.controller.maintain_formation(positions)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
