"""Tests for integration_hub.IntegrationHub.

Covers the bug fixed in cycle 1 (project_root pointed one dir above the repo
root, so go/cpp/android detection always returned False).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from integration_hub import IntegrationHub  # noqa: E402


@pytest.fixture
def hub() -> IntegrationHub:
    return IntegrationHub()


def test_project_root_resolves_to_repo_root(hub: IntegrationHub) -> None:
    """project_root must equal the repo root, not its parent."""
    assert hub.project_root == PROJECT_ROOT


def test_get_status_detects_existing_subprojects(hub: IntegrationHub) -> None:
    """If go_backend/ exists at the repo root, status['go'] must be True.
    Regression guard for the parent.parent off-by-one bug.
    """
    status = hub.get_status()
    if (PROJECT_ROOT / "go_backend" / "go.mod").exists():
        assert status["go"] is True
    if (PROJECT_ROOT / "cpp_accel" / "pathfinding.hpp").exists():
        assert status["cpp"] is True
    if (PROJECT_ROOT / "android_app").exists():
        assert status["kotlin"] is True
        assert status["android_app"] is True


def test_get_status_shape(hub: IntegrationHub) -> None:
    status = hub.get_status()
    for key in ("rust", "go", "julia", "cpp", "kotlin", "android_app"):
        assert key in status


def test_python_formation_line(hub: IntegrationHub) -> None:
    positions = hub._python_formation(5, "line", 2.0, 0.0, 0.0)
    assert len(positions) == 5
    xs = [p[0] for p in positions]
    assert xs == sorted(xs)
    # Centered around 0
    assert abs((min(xs) + max(xs)) / 2) < 1e-9


def test_python_formation_circle(hub: IntegrationHub) -> None:
    import math

    positions = hub._python_formation(8, "circle", 2.0, 5.0, 5.0)
    assert len(positions) == 8
    # All points equidistant from center
    dists = [math.hypot(x - 5.0, y - 5.0) for x, y in positions]
    assert max(dists) - min(dists) < 1e-6


def test_python_formation_zero(hub: IntegrationHub) -> None:
    assert hub._python_formation(0, "line", 2.0, 0.0, 0.0) == []


def test_python_formation_unknown_type_returns_stack(hub: IntegrationHub) -> None:
    positions = hub._python_formation(3, "unknown_type", 2.0, 7.0, 9.0)
    assert positions == [(7.0, 9.0)] * 3


def test_combat_analysis_recommends_attack_when_advantage(hub: IntegrationHub) -> None:
    my_units = [(100.0, 100.0, 50.0, 8.0)] * 5
    enemy_units = [(100.0, 100.0, 5.0, 1.0)]
    result = hub.combat_analysis(my_units, enemy_units)
    assert result["recommendation"] == "ATTACK"
    assert result["advantage"] > 1.2


def test_combat_analysis_recommends_retreat_when_disadvantage(
    hub: IntegrationHub,
) -> None:
    my_units = [(10.0, 100.0, 5.0, 1.0)]
    enemy_units = [(100.0, 100.0, 50.0, 8.0)] * 5
    result = hub.combat_analysis(my_units, enemy_units)
    assert result["recommendation"] == "RETREAT"
    assert result["advantage"] < 0.8


def test_no_module_level_hub_instantiation() -> None:
    """integration_hub must not run IntegrationHub() at import time
    (cycle 1 fix removed that side effect)."""
    import integration_hub

    assert not hasattr(integration_hub, "hub")
