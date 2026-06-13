# -*- coding: utf-8 -*-
"""utils.pid_controller 테스트"""

import sys
import math
import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BOT_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))


def _load():
    if "bot_pid" in sys.modules:
        return sys.modules["bot_pid"]
    spec = importlib.util.spec_from_file_location(
        "bot_pid", BOT_ROOT / "utils" / "pid_controller.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bot_pid"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestPIDController:
    def test_default(self):
        p = _load().PIDController()
        assert p.kp == 1.0 and p.ki == 0.0 and p.kd == 0.0

    def test_proportional(self):
        p = _load().PIDController(kp=2.0)
        assert p.update(5.0, 0.1) == 10.0

    def test_zero_dt(self):
        assert _load().PIDController(kp=1.0).update(5.0, 0.0) == 0.0

    def test_output_clamp(self):
        p = _load().PIDController(kp=100.0, output_min=-5.0, output_max=5.0)
        assert p.update(10.0, 0.1) == 5.0

    def test_anti_windup(self):
        p = _load().PIDController(kp=0.0, ki=1.0, integral_max=10.0)
        for _ in range(100):
            p.update(100.0, 0.1)
        assert p.integral <= 10.0

    def test_reset(self):
        p = _load().PIDController()
        p.update(5.0, 0.1)
        p.reset()
        assert p.integral == 0.0 and p.initialized is False

    def test_set_gains(self):
        p = _load().PIDController()
        p.set_gains(3.0, 0.5, 0.2)
        assert (p.kp, p.ki, p.kd) == (3.0, 0.5, 0.2)


class TestPID2D:
    def test_update_tuple(self):
        result = _load().PID2D(kp=1.0).update((0, 0), (5, 5), 0.1)
        assert len(result) == 2

    def test_magnitude_limit(self):
        vx, vy = _load().PID2D(kp=100.0, output_max=5.0).update((0, 0), (100, 100), 0.1)
        assert math.sqrt(vx*vx + vy*vy) <= 5.001


class TestUnitMovementController:
    def test_arrival(self):
        m = _load().UnitMovementController(arrival_threshold=1.0)
        assert m.calculate_velocity((5, 5), (5, 5), 0.1) == (0.0, 0.0)

    def test_get_next_position(self):
        pos = _load().UnitMovementController().get_next_position((0, 0), (10, 10), 0.1)
        assert len(pos) == 2


class TestFormationController:
    def test_get_controller(self):
        f = _load().FormationController()
        c = f.get_controller(1)
        assert f.get_controller(1) is c

    def test_remove(self):
        f = _load().FormationController()
        f.get_controller(1)
        f.remove_unit(1)
        assert 1 not in f.unit_controllers

    def test_remove_nonexistent(self):
        _load().FormationController().remove_unit(999)
