# -*- coding: utf-8 -*-
"""Dynamic frame-skip policy for manager execution."""

from __future__ import annotations

from typing import Dict


class FrameSkipManager:
    """Decides whether each manager should run on a given frame."""

    DEFAULT_INTERVALS: Dict[str, int] = {
        "combat_manager": 1,
        "economy_manager": 3,
        "strategy_manager": 5,
        "scouting_system": 11,
        "creep_manager": 33,
        "upgrade_manager": 22,
        "intel_manager": 7,
    }

    COMBAT_INTERVALS: Dict[str, int] = {
        "combat_manager": 1,
        "economy_manager": 5,
        "strategy_manager": 3,
        "scouting_system": 22,
        "creep_manager": 66,
        "upgrade_manager": 44,
        "intel_manager": 3,
    }

    def __init__(self) -> None:
        self.in_combat = False
        self._overloaded = False

    def should_execute(self, manager_name: str, iteration: int) -> bool:
        intervals = self.COMBAT_INTERVALS if self.in_combat else self.DEFAULT_INTERVALS
        interval = max(1, int(intervals.get(manager_name, 1)))
        if self._overloaded and manager_name != "combat_manager":
            interval *= 2
        return iteration % interval == 0

    def set_combat_mode(self, active: bool) -> None:
        self.in_combat = bool(active)

    def set_overloaded(self, overloaded: bool) -> None:
        self._overloaded = bool(overloaded)
