"""Minimal player module stub."""


class Bot:
    def __init__(self, race=None, ai=None, name=None):
        self.race = race
        self.ai = ai
        self.name = name


class Computer:
    def __init__(self, race=None, difficulty=None, ai_build=None):
        self.race = race
        self.difficulty = difficulty
        self.ai_build = ai_build


class Human:
    def __init__(self, race=None, name=None):
        self.race = race
        self.name = name
