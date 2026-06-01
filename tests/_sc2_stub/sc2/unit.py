"""Stub for sc2.unit.Unit."""
from __future__ import annotations


class Unit:
    """Minimal stand-in. Real tests use MagicMock instead of subclassing."""

    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
