"""Stub for sc2.data — Race, Difficulty, Result enums."""
from __future__ import annotations

from enum import Enum


class Race(Enum):
    Random = 0
    Protoss = 1
    Terran = 2
    Zerg = 3


class Difficulty(Enum):
    VeryEasy = 1
    Easy = 2
    Medium = 3
    MediumHard = 4
    Hard = 5
    Harder = 6
    VeryHard = 7
    CheatVision = 8
    CheatMoney = 9
    CheatInsane = 10


class Result(Enum):
    Victory = 1
    Defeat = 2
    Tie = 3
    Undecided = 4
