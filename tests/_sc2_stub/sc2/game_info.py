"""Stub for sc2.game_info.GameInfo."""
from __future__ import annotations


class GameInfo:
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
