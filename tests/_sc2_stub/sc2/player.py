"""Stub for sc2.player — Bot, Computer."""
from __future__ import annotations


class _PlayerBase:
    def __init__(self, race=None, ai=None, name=None, difficulty=None, fullscreen=False):
        self.race = race
        self.ai = ai
        self.name = name
        self.difficulty = difficulty
        self.fullscreen = fullscreen


class Bot(_PlayerBase):
    pass


class Computer(_PlayerBase):
    pass


class Human(_PlayerBase):
    pass
