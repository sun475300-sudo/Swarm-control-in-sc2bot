"""Tests for `src.bot.swarm` package: import sanity + tick contract."""

from __future__ import annotations

import importlib

import pytest

BEHAVIOR_COUNT = 30


@pytest.mark.parametrize("idx", list(range(1, BEHAVIOR_COUNT + 1)))
def test_behavior_module_imports(idx: int) -> None:
    """Every behavior_XX module must import successfully."""
    mod = importlib.import_module(f"src.bot.swarm.behavior_{idx:02d}")
    cls_name = f"Behavior{idx:02d}"
    assert hasattr(mod, cls_name), f"{cls_name} missing in {mod.__name__}"


@pytest.mark.parametrize("idx", list(range(1, BEHAVIOR_COUNT + 1)))
def test_behavior_tick_returns_positions(idx: int) -> None:
    """`tick` must return a list of (x, y) tuples for the supplied positions."""
    mod = importlib.import_module(f"src.bot.swarm.behavior_{idx:02d}")
    cls = getattr(mod, f"Behavior{idx:02d}")
    instance = cls()

    sample = [(0.0, 0.0), (1.0, 2.0), (5.5, -3.0)]
    out = instance.tick(sample)

    assert isinstance(out, list)
    assert len(out) == len(sample)
    for original, result in zip(sample, out):
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result == (float(original[0]), float(original[1]))


def test_formation_controller_accepts_point_like() -> None:
    """FormationController must accept objects exposing .x/.y attrs."""
    from src.bot.swarm import FormationController

    class P:
        def __init__(self, x: float, y: float) -> None:
            self.x = x
            self.y = y

    ctrl = FormationController()
    out = ctrl.maintain_formation([P(1, 2), P(3, 4)])
    assert out == [(1.0, 2.0), (3.0, 4.0)]


def test_formation_controller_center_of_mass_empty() -> None:
    from src.bot.swarm import FormationController

    assert FormationController().center_of_mass([]) == (0.0, 0.0)


def test_formation_controller_center_of_mass_basic() -> None:
    from src.bot.swarm import FormationController

    cx, cy = FormationController().center_of_mass([(0, 0), (2, 0), (2, 2), (0, 2)])
    assert cx == pytest.approx(1.0)
    assert cy == pytest.approx(1.0)
