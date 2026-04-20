"""
Swarm Behavior Module #8 - FollowLeader.
First unit is the leader (position unchanged); all followers trail behind it
with evenly-spaced offsets along the west direction.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_FOLLOW_SPACING = 2.0   # distance between consecutive followers


class Behavior08:
    """FollowLeader: unit[0] leads; remaining units trail behind with fixed spacing."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_08"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Keep the first unit at its current position (the leader) and place
        each subsequent unit directly behind the leader with increasing
        spacing along the west axis.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions: leader unchanged, followers trailing west.
        """
        if not positions:
            return []

        leader_x, leader_y = positions[0]
        targets: List[Position] = [(leader_x, leader_y)]

        for i in range(1, len(positions)):
            # Trail behind leader along the west axis
            tx = leader_x - i * _FOLLOW_SPACING
            ty = leader_y
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
