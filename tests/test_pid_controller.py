# -*- coding: utf-8 -*-
"""Tests for utils/pid_controller.py - PID, PID2D, UnitMovement, FormationController."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from utils.pid_controller import (
    PIDController,
    PID2D,
    UnitMovementController,
    FormationController,
)


class TestPIDControllerBasics:
    def test_default_gains(self):
        pid = PIDController()
        assert pid.kp == 1.0
        assert pid.ki == 0.0
        assert pid.kd == 0.0

    def test_initial_state(self):
        pid = PIDController()
        assert pid.integral == 0.0
        assert pid.last_error == 0.0
        assert not pid.initialized

    def test_reset_clears_state(self):
        pid = PIDController()
        pid.update(5.0, 0.1)
        pid.reset()
        assert pid.integral == 0.0
        assert pid.last_error == 0.0
        assert not pid.initialized


class TestPIDControllerUpdate:
    def test_zero_dt_returns_zero(self):
        pid = PIDController(kp=1.0)
        assert pid.update(100.0, 0.0) == 0.0

    def test_proportional_only(self):
        pid = PIDController(kp=2.0, ki=0.0, kd=0.0)
        # P-only: output = kp * error = 2.0 * 5.0 = 10.0
        output = pid.update(5.0, 0.1)
        assert output == 10.0

    def test_output_clamping_high(self):
        pid = PIDController(kp=100.0, output_max=5.0)
        output = pid.update(1.0, 0.1)
        assert output == 5.0

    def test_output_clamping_low(self):
        pid = PIDController(kp=100.0, output_min=-5.0, output_max=5.0)
        output = pid.update(-1.0, 0.1)
        assert output == -5.0

    def test_integral_anti_windup(self):
        pid = PIDController(ki=10.0, integral_max=1.0)
        # Hammer with large errors; integral should cap at 1.0
        for _ in range(100):
            pid.update(10.0, 1.0)
        assert pid.integral <= 1.0

    def test_set_gains_updates(self):
        pid = PIDController()
        pid.set_gains(5.0, 1.0, 0.5)
        assert pid.kp == 5.0
        assert pid.ki == 1.0
        assert pid.kd == 0.5


class TestPID2D:
    def test_2d_returns_two_outputs(self):
        pid = PID2D(kp=1.0)
        result = pid.update((10.0, 20.0), (0.0, 0.0), 0.1)
        assert len(result) == 2

    def test_x_axis_tracks_error(self):
        # Signature: update(current, target, dt)
        pid = PID2D(kp=1.0, output_max=100.0)
        out_x, out_y = pid.update((0.0, 0.0), (5.0, 0.0), 0.1)
        # Target is +x relative to current -> vx should be positive
        assert out_x > 0

    def test_reset_both_axes(self):
        pid = PID2D()
        pid.update((10.0, 10.0), (0.0, 0.0), 0.1)
        pid.reset()
        assert pid.pid_x.integral == 0.0
        assert pid.pid_y.integral == 0.0

    def test_set_gains_applied_to_both(self):
        pid = PID2D()
        pid.set_gains(3.0, 0.5, 0.1)
        assert pid.pid_x.kp == 3.0
        assert pid.pid_y.kp == 3.0


class TestUnitMovementController:
    def test_instantiate(self):
        umc = UnitMovementController()
        assert umc is not None

    def test_calculate_velocity_returns_tuple(self):
        umc = UnitMovementController()
        result = umc.calculate_velocity((0.0, 0.0), (10.0, 0.0), 0.1)
        assert len(result) == 2

    def test_velocity_points_toward_target(self):
        umc = UnitMovementController()
        vx, vy = umc.calculate_velocity((0.0, 0.0), (10.0, 0.0), 0.1)
        # Target is to the right (+x), so vx should be positive
        assert vx > 0

    def test_reset_clears_state(self):
        umc = UnitMovementController()
        umc.calculate_velocity((0.0, 0.0), (10.0, 0.0), 0.1)
        umc.reset()
        # UnitMovementController uses PID2D; check each axis
        assert umc.pid.pid_x.integral == 0.0
        assert umc.pid.pid_y.integral == 0.0

    def test_get_next_position_moves_forward(self):
        umc = UnitMovementController()
        next_pos = umc.get_next_position((0.0, 0.0), (10.0, 0.0), dt=0.1)
        # After one step, should be closer to target
        assert next_pos[0] > 0


class TestFormationController:
    def test_instantiate_with_default_radius(self):
        fc = FormationController()
        assert fc.formation_radius == 3.0

    def test_custom_radius(self):
        fc = FormationController(formation_radius=5.0)
        assert fc.formation_radius == 5.0

    def test_unit_controllers_empty_initially(self):
        fc = FormationController()
        assert len(fc.unit_controllers) == 0

    def test_get_controller_creates_on_demand(self):
        fc = FormationController()
        ctrl = fc.get_controller(unit_id=42)
        assert ctrl is not None
        assert 42 in fc.unit_controllers

    def test_get_controller_returns_same_instance(self):
        fc = FormationController()
        ctrl1 = fc.get_controller(42)
        ctrl2 = fc.get_controller(42)
        assert ctrl1 is ctrl2

    def test_remove_unit(self):
        fc = FormationController()
        fc.get_controller(42)
        fc.remove_unit(42)
        assert 42 not in fc.unit_controllers

    def test_remove_missing_unit_does_not_raise(self):
        fc = FormationController()
        fc.remove_unit(999)  # should not crash

    def test_calculate_formation_velocity_returns_tuple(self):
        fc = FormationController()
        vx, vy = fc.calculate_formation_velocity(
            unit_id=1,
            unit_pos=(0.0, 0.0),
            formation_pos=(5.0, 5.0),
            group_velocity=(1.0, 0.0),
            dt=0.1,
        )
        assert isinstance(vx, float)
        assert isinstance(vy, float)
