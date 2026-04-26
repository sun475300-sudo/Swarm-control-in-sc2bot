"""Import + tick smoke tests for ``src/bot/swarm/behavior_01..30.py``.

Background
----------
All 30 ``behavior_*.py`` modules import ``FormationController`` from
``.formation_controller``. That file did not exist on the branch, so
every single ``BehaviorNN`` class raised ``ModuleNotFoundError`` the
moment it was imported. These tests pin the contract:

* every behavior module imports cleanly,
* ``BehaviorNN()`` constructs without args,
* ``tick(positions)`` is length-preserving (it should not silently
  drop units).
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


BEHAVIOR_INDICES = list(range(1, 31))


@pytest.mark.parametrize("idx", BEHAVIOR_INDICES)
def test_behavior_module_imports(idx: int) -> None:
    mod = importlib.import_module(f"bot.swarm.behavior_{idx:02d}")
    cls = getattr(mod, f"Behavior{idx:02d}")
    instance = cls()
    assert instance.name == f"behavior_{idx:02d}"
    assert hasattr(instance, "tick")


@pytest.mark.parametrize("idx", BEHAVIOR_INDICES)
def test_behavior_tick_preserves_length(idx: int) -> None:
    mod = importlib.import_module(f"bot.swarm.behavior_{idx:02d}")
    cls = getattr(mod, f"Behavior{idx:02d}")
    inst = cls()
    inputs = [(0.0, 0.0), (1.5, 2.5), (-3.0, 4.0)]
    out = inst.tick(inputs)
    assert len(out) == len(inputs), (
        f"behavior_{idx:02d}.tick() dropped/duplicated units: "
        f"{len(inputs)} in, {len(out)} out"
    )


def test_formation_controller_identity_default() -> None:
    from bot.swarm import FormationController

    fc = FormationController()
    assert fc.maintain_formation([]) == []
    assert fc.maintain_formation([(1, 2), (3, 4)]) == [(1.0, 2.0), (3.0, 4.0)]


def test_formation_controller_handles_3d_positions() -> None:
    from bot.swarm import FormationController

    out = FormationController().maintain_formation([(1, 2, 3)])
    assert out == [(1.0, 2.0, 3.0)]
