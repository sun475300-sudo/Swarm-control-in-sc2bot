# -*- coding: utf-8 -*-
"""SC2 observation and discrete action helpers for RL training."""

from __future__ import annotations

import numpy as np

try:
    from sc2.ids.unit_typeid import UnitTypeId
except Exception:
    class UnitTypeId:
        LAIR = "LAIR"
        QUEEN = "QUEEN"
        ZERGLING = "ZERGLING"
        ROACH = "ROACH"
        HYDRALISK = "HYDRALISK"


def _amount(collection) -> int:
    if collection is None:
        return 0
    if hasattr(collection, "amount"):
        return int(collection.amount)
    try:
        return len(collection)
    except Exception:
        return 0


def _ready_exists(structures) -> bool:
    ready = getattr(structures, "ready", structures)
    exists = getattr(ready, "exists", None)
    if exists is not None:
        return bool(exists)
    return _amount(ready) > 0


def _call_units(bot, unit_type):
    try:
        return bot.units(unit_type)
    except Exception:
        return []


class SC2Observation:
    """Build the 16D normalized observation vector used by macro RL."""

    @staticmethod
    def from_bot(bot) -> np.ndarray:
        try:
            lair_ready = _ready_exists(bot.structures(UnitTypeId.LAIR))
        except Exception:
            lair_ready = False

        values = [
            min(float(getattr(bot, "minerals", 0)) / 2000.0, 1.0),
            min(float(getattr(bot, "vespene", 0)) / 1000.0, 1.0),
            min(_amount(getattr(bot, "workers", [])) / 80.0, 1.0),
            min(float(getattr(bot, "supply_used", 0)) / 200.0, 1.0),
            min(float(getattr(bot, "supply_army", 0)) / 150.0, 1.0),
            min(_amount(getattr(bot, "townhalls", [])) / 5.0, 1.0),
            min(float(getattr(bot, "supply_left", 0)) / 20.0, 1.0),
            1.0 if lair_ready else 0.0,
            min(_amount(getattr(bot, "enemy_units", [])) / 50.0, 1.0),
            min(_amount(getattr(bot, "enemy_structures", [])) / 20.0, 1.0),
            1.0 if _enemy_near_start(bot) else 0.0,
            min(float(getattr(bot, "time", 0.0)) / 1200.0, 1.0),
            min(_amount(_call_units(bot, UnitTypeId.QUEEN)) / 6.0, 1.0),
            min(_amount(_call_units(bot, UnitTypeId.ZERGLING)) / 40.0, 1.0),
            min(_amount(_call_units(bot, UnitTypeId.ROACH)) / 20.0, 1.0),
            min(_amount(_call_units(bot, UnitTypeId.HYDRALISK)) / 15.0, 1.0),
        ]
        return np.asarray(values, dtype=np.float32)


def _enemy_near_start(bot) -> bool:
    enemies = getattr(bot, "enemy_units", [])
    start = getattr(bot, "start_location", None)
    if start is None:
        return False
    closer_than = getattr(enemies, "closer_than", None)
    if callable(closer_than):
        try:
            return bool(closer_than(30, start))
        except Exception:
            return False
    return False


class SC2ActionSpace:
    """Seven macro actions exposed to higher-level RL."""

    ACTIONS = {
        0: "MACRO_FOCUS",
        1: "ARMY_FOCUS",
        2: "TECH_UP",
        3: "ATTACK",
        4: "DEFEND",
        5: "HARASS",
        6: "EXPAND",
    }

    @classmethod
    def contains(cls, action: int) -> bool:
        return int(action) in cls.ACTIONS

    @classmethod
    def label(cls, action: int) -> str:
        return cls.ACTIONS[int(action)]
