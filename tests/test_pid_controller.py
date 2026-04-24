# -*- coding: utf-8 -*-
"""
pid_controller 단위 테스트

standalone 모듈 (sc2 의존성 없음). PIDController / PID2D /
UnitMovementController 동작 검증.
"""

import importlib.util
import math
import sys
from pathlib import Path

import pytest

BOT_ROOT = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"


@pytest.fixture(scope="module")
def pid_mod():
    path = BOT_ROOT / "utils" / "pid_controller.py"
    spec = importlib.util.spec_from_file_location("wzc_pid_controller", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules["wzc_pid_controller"] = module
    spec.loader.exec_module(module)
    return module


# ═══════════════════════════════════════════════════════
# PIDController
# ═══════════════════════════════════════════════════════


class TestPIDControllerInit:
    def test_default_values(self, pid_mod):
        pid = pid_mod.PIDController()
        assert pid.kp == 1.0
        assert pid.ki == 0.0
        assert pid.kd == 0.0
        assert pid.integral == 0.0
        assert pid.initialized is False

    def test_custom_gains(self, pid_mod):
        pid = pid_mod.PIDController(kp=2.0, ki=0.5, kd=0.1)
        assert pid.kp == 2.0
        assert pid.ki == 0.5
        assert pid.kd == 0.1


class TestPIDUpdate:
    def test_zero_dt_returns_zero(self, pid_mod):
        pid = pid_mod.PIDController(kp=1.0)
        assert pid.update(error=5.0, dt=0.0) == 0.0

    def test_negative_dt_returns_zero(self, pid_mod):
        pid = pid_mod.PIDController(kp=1.0)
        assert pid.update(error=5.0, dt=-0.1) == 0.0

    def test_proportional_only(self, pid_mod):
        pid = pid_mod.PIDController(kp=2.0, ki=0.0, kd=0.0)
        out = pid.update(error=3.0, dt=0.1)
        assert out == pytest.approx(6.0)  # P = kp * error

    def test_integral_accumulates(self, pid_mod):
        pid = pid_mod.PIDController(kp=0.0, ki=1.0, kd=0.0)
        pid.update(error=1.0, dt=1.0)  # I += 1.0
        pid.update(error=1.0, dt=1.0)  # I += 1.0 → 2.0
        out = pid.update(error=1.0, dt=1.0)  # I = 3.0
        assert out == pytest.approx(3.0)

    def test_anti_windup_clamps_integral(self, pid_mod):
        pid = pid_mod.PIDController(kp=0.0, ki=1.0, kd=0.0, integral_max=5.0)
        # Drive integral past max
        for _ in range(100):
            pid.update(error=1.0, dt=1.0)
        assert pid.integral <= 5.0

    def test_output_clamping(self, pid_mod):
        pid = pid_mod.PIDController(kp=100.0, ki=0.0, kd=0.0, output_min=-10, output_max=10)
        out = pid.update(error=5.0, dt=0.1)  # Unclamped would be 500
        assert out == 10.0

        out2 = pid.update(error=-5.0, dt=0.1)
        assert out2 == -10.0


class TestPIDReset:
    def test_reset_clears_state(self, pid_mod):
        pid = pid_mod.PIDController(kp=1.0, ki=1.0, kd=1.0)
        pid.update(error=5.0, dt=0.1)
        pid.update(error=3.0, dt=0.1)
        assert pid.initialized is True
        assert pid.integral != 0.0

        pid.reset()
        assert pid.integral == 0.0
        assert pid.last_error == 0.0
        assert pid.last_derivative == 0.0
        assert pid.initialized is False


class TestPIDSetGains:
    def test_set_gains(self, pid_mod):
        pid = pid_mod.PIDController()
        pid.set_gains(kp=5.0, ki=1.0, kd=0.5)
        assert pid.kp == 5.0
        assert pid.ki == 1.0
        assert pid.kd == 0.5


# ═══════════════════════════════════════════════════════
# PID2D
# ═══════════════════════════════════════════════════════


class TestPID2D:
    def test_update_returns_vector(self, pid_mod):
        pid = pid_mod.PID2D(kp=1.0, output_max=10.0)
        vx, vy = pid.update(current=(0, 0), target=(3, 4), dt=0.1)
        assert isinstance(vx, float)
        assert isinstance(vy, float)

    def test_magnitude_clamped(self, pid_mod):
        pid = pid_mod.PID2D(kp=100.0, output_max=5.0)
        vx, vy = pid.update(current=(0, 0), target=(100, 100), dt=0.1)
        magnitude = math.sqrt(vx * vx + vy * vy)
        assert magnitude <= 5.0 + 1e-6

    def test_reset(self, pid_mod):
        pid = pid_mod.PID2D(kp=1.0, ki=1.0)
        pid.update(current=(0, 0), target=(5, 5), dt=0.1)
        pid.update(current=(0, 0), target=(5, 5), dt=0.1)
        pid.reset()
        assert pid.pid_x.integral == 0.0
        assert pid.pid_y.integral == 0.0

    def test_set_gains_both_axes(self, pid_mod):
        pid = pid_mod.PID2D()
        pid.set_gains(kp=3.0, ki=1.0, kd=0.5)
        assert pid.pid_x.kp == 3.0
        assert pid.pid_y.kp == 3.0
        assert pid.pid_x.kd == 0.5


# ═══════════════════════════════════════════════════════
# UnitMovementController
# ═══════════════════════════════════════════════════════


class TestUnitMovementController:
    def test_at_target_returns_zero(self, pid_mod):
        mc = pid_mod.UnitMovementController(arrival_threshold=0.5)
        v = mc.calculate_velocity(current_pos=(0, 0), target_pos=(0.1, 0.1), dt=0.1)
        assert v == (0.0, 0.0)

    def test_velocity_towards_target(self, pid_mod):
        mc = pid_mod.UnitMovementController(max_speed=5.0, acceleration=10.0)
        vx, vy = mc.calculate_velocity(current_pos=(0, 0), target_pos=(10, 0), dt=0.1)
        # Should be moving toward +x
        assert vx > 0
        assert abs(vy) < 1e-3

    def test_max_speed_not_exceeded(self, pid_mod):
        mc = pid_mod.UnitMovementController(max_speed=3.0, acceleration=100.0)
        # After a few steps, velocity should not exceed max_speed
        for _ in range(20):
            vx, vy = mc.calculate_velocity(current_pos=(0, 0), target_pos=(100, 0), dt=0.1)
        speed = math.sqrt(vx * vx + vy * vy)
        assert speed <= 3.0 + 1e-6

    def test_reset(self, pid_mod):
        mc = pid_mod.UnitMovementController()
        mc.calculate_velocity(current_pos=(0, 0), target_pos=(10, 0), dt=0.1)
        assert mc.current_velocity != (0.0, 0.0)
        mc.reset()
        assert mc.current_velocity == (0.0, 0.0)
