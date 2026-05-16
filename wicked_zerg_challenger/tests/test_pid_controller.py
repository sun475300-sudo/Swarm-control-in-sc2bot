# -*- coding: utf-8 -*-
"""
PID Controller / PID2D / UnitMovementController 단위 테스트.
"""

import math
import os
import sys
import unittest

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.pid_controller import PID2D, PIDController, UnitMovementController


class TestPIDControllerSingleAxis(unittest.TestCase):
    def test_zero_dt_returns_zero(self):
        pid = PIDController(kp=1.0)
        self.assertEqual(pid.update(error=10.0, dt=0), 0.0)
        self.assertEqual(pid.update(error=10.0, dt=-1), 0.0)

    def test_proportional_only(self):
        pid = PIDController(kp=2.0, ki=0.0, kd=0.0)
        # 첫 호출은 derivative 0 (initialized=False)
        result = pid.update(error=5.0, dt=0.1)
        # P term: 2.0 * 5.0 = 10.0
        # I term: 0 (ki=0)
        # D term: 0 (first call)
        self.assertAlmostEqual(result, 10.0)

    def test_integral_anti_windup(self):
        pid = PIDController(kp=0.0, ki=1.0, kd=0.0, integral_max=5.0)
        # 큰 오차를 여러 번 누적 → integral 이 5.0 으로 클램프
        for _ in range(100):
            pid.update(error=10.0, dt=1.0)
        self.assertLessEqual(abs(pid.integral), 5.0 + 1e-9)

    def test_output_clamping(self):
        pid = PIDController(kp=100.0, output_min=-1.0, output_max=1.0)
        self.assertEqual(pid.update(error=999.0, dt=0.1), 1.0)
        self.assertEqual(pid.update(error=-999.0, dt=0.1), -1.0)

    def test_reset_clears_state(self):
        pid = PIDController(kp=1.0, ki=1.0)
        pid.update(error=5.0, dt=1.0)
        pid.reset()
        self.assertEqual(pid.integral, 0.0)
        self.assertEqual(pid.last_error, 0.0)
        self.assertFalse(pid.initialized)

    def test_set_gains_updates_values(self):
        pid = PIDController()
        pid.set_gains(kp=2.0, ki=3.0, kd=4.0)
        self.assertEqual(pid.kp, 2.0)
        self.assertEqual(pid.ki, 3.0)
        self.assertEqual(pid.kd, 4.0)

    def test_derivative_initialized_after_first_call(self):
        pid = PIDController(kp=0.0, ki=0.0, kd=1.0)
        pid.update(error=1.0, dt=0.1)
        self.assertTrue(pid.initialized)


class TestPID2D(unittest.TestCase):
    def test_zero_target_zero_output(self):
        pid = PID2D(kp=1.0)
        vx, vy = pid.update(current=(0, 0), target=(0, 0), dt=0.1)
        self.assertAlmostEqual(vx, 0.0)
        self.assertAlmostEqual(vy, 0.0)

    def test_velocity_magnitude_capped(self):
        pid = PID2D(kp=100.0, output_max=5.0)
        vx, vy = pid.update(current=(0, 0), target=(100, 100), dt=0.1)
        magnitude = math.sqrt(vx * vx + vy * vy)
        # output_max 가 5.0 이므로 magnitude도 5.0 이하
        self.assertLessEqual(magnitude, 5.0 + 1e-6)

    def test_reset_propagates(self):
        pid = PID2D(kp=1.0, ki=1.0)
        pid.update(current=(0, 0), target=(5, 5), dt=1.0)
        pid.reset()
        self.assertEqual(pid.pid_x.integral, 0.0)
        self.assertEqual(pid.pid_y.integral, 0.0)


class TestUnitMovementController(unittest.TestCase):
    def test_initial_velocity_is_zero(self):
        mc = UnitMovementController()
        self.assertEqual(mc.current_velocity, (0.0, 0.0))

    def test_reset_clears_velocity(self):
        mc = UnitMovementController()
        mc.current_velocity = (3.0, 4.0)
        mc.reset()
        self.assertEqual(mc.current_velocity, (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
