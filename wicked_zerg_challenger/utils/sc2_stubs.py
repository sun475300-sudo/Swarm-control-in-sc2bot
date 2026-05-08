# -*- coding: utf-8 -*-
"""SC2 import stubs for environments without the python-sc2 library.

Used as ImportError fallback so modules and tests can be imported in CI.
The stubs only need to support attribute access and be type-checkable; they
are never executed against real game state — guard logic with `if SC2_AVAILABLE`.
"""

from enum import Enum

SC2_AVAILABLE = False


class _StubEnum:
    def __getattr__(self, name):
        return name

    def __call__(self, *args, **kwargs):
        return self


UnitTypeId = _StubEnum()
AbilityId = _StubEnum()
UpgradeId = _StubEnum()
BuffId = _StubEnum()
EffectId = _StubEnum()


class Point2(tuple):
    def __new__(cls, iterable=(0, 0)):
        return super().__new__(cls, iterable)

    def __init__(self, iterable=(0, 0)):
        self.x, self.y = self[0], self[1]

    def distance_to(self, other):
        return ((self[0] - other[0]) ** 2 + (self[1] - other[1]) ** 2) ** 0.5


class Point3(tuple):
    pass


class Unit:
    pass


class Units(list):
    def __init__(self, iterable=None, bot_object=None):
        super().__init__(iterable or [])

    def filter(self, fn):
        return Units([x for x in self if fn(x)], None)

    def closer_than(self, distance, position):
        return Units([], None)

    def closest_to(self, position):
        return None


class BotAI:
    pass


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


class Race(Enum):
    NoRace = 0
    Terran = 1
    Zerg = 2
    Protoss = 3
    Random = 4
