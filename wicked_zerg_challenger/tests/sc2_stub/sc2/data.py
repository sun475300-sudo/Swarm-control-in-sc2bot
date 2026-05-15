"""Minimal data enums."""

from enum import Enum


class Race(Enum):
    NoRace = 0
    Terran = 1
    Zerg = 2
    Protoss = 3
    Random = 4


class Result(Enum):
    Victory = 1
    Defeat = 2
    Tie = 3
    Undecided = 4


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


class AIBuild(Enum):
    RandomBuild = 0
    Rush = 1
    Timing = 2
    Power = 3
    Macro = 4
    Air = 5
