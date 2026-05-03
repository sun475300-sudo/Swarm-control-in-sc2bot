# -*- coding: utf-8 -*-
"""Unit tests for utils.pid_controller (PIDController + PID2D)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.pid_controller import PID2D, PIDController


class TestPIDController(unittest.TestCase):
    def test_proportional_only(self):
        pid = PIDController(kp=2.0, ki=0.0, kd=0.0)
        self.assertEqual(pid.update(error=3.0, dt=0.1), 6.0)

    def test_zero_dt_returns_zero(self):
        pid = PIDController(kp=10.0)
        self.assertEqual(pid.update(error=5.0, dt=0.0), 0.0)
        self.assertEqual(pid.update(error=5.0, dt=-0.1), 0.0)

    def test_output_clamped_to_min_max(self):
        pid = PIDController(kp=100.0, output_min=-1.0, output_max=1.0)
        self.assertEqual(pid.update(error=0.5, dt=0.1), 1.0)
        self.assertEqual(pid.update(error=-0.5, dt=0.1), -1.0)

    def test_integral_anti_windup(self):
        pid = PIDController(kp=0.0, ki=1.0, integral_max=5.0)
        # Drive integrator way past the cap.
        for _ in range(100):
            pid.update(error=1.0, dt=1.0)
        self.assertLessEqual(pid.integral, 5.0)
        self.assertGreaterEqual(pid.integral, -5.0)

    def test_derivative_zero_on_first_call(self):
        # First call has no previous error -> derivative term must be 0.
        pid = PIDController(kp=0.0, ki=0.0, kd=10.0)
        self.assertEqual(pid.update(error=5.0, dt=0.1), 0.0)

    def test_reset_clears_state(self):
        pid = PIDController(kp=1.0, ki=1.0, kd=1.0)
        pid.update(error=2.0, dt=0.1)
        pid.update(error=3.0, dt=0.1)
        pid.reset()
        self.assertEqual(pid.integral, 0.0)
        self.assertEqual(pid.last_error, 0.0)
        self.assertFalse(pid.initialized)

    def test_set_gains_updates_kp_ki_kd(self):
        pid = PIDController()
        pid.set_gains(2.5, 0.4, 0.7)
        self.assertEqual(pid.kp, 2.5)
        self.assertEqual(pid.ki, 0.4)
        self.assertEqual(pid.kd, 0.7)


class TestPID2D(unittest.TestCase):
    def test_velocity_magnitude_capped(self):
        pid = PID2D(kp=100.0, output_max=10.0)
        vx, vy = pid.update(current=(0.0, 0.0), target=(1000.0, 1000.0), dt=0.1)
        magnitude = (vx * vx + vy * vy) ** 0.5
        self.assertLessEqual(magnitude, 10.0 + 1e-6)

    def test_no_movement_at_target(self):
        pid = PID2D(kp=5.0)
        vx, vy = pid.update(current=(1.0, 1.0), target=(1.0, 1.0), dt=0.1)
        self.assertEqual(vx, 0.0)
        self.assertEqual(vy, 0.0)

    def test_reset_propagates_to_axes(self):
        pid = PID2D(kp=1.0, ki=1.0)
        pid.update(current=(0, 0), target=(5, 5), dt=0.1)
        pid.reset()
        self.assertEqual(pid.pid_x.integral, 0.0)
        self.assertEqual(pid.pid_y.integral, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
