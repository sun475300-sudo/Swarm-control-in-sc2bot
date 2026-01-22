# -*- coding: utf-8 -*-
"""
PID Controller for Smooth Unit Movement

Provides proportional-integral-derivative control for:
- Smooth unit velocity transitions
- Stable formation holding
- Optimal path following

Features:
- Anti-windup protection
- Derivative smoothing
- Configurable gains
"""

from typing import Tuple, Optional
import math


class PIDController:
    """
    PID Controller for single-axis control.

    Used for controlling unit velocity, position, or other continuous values.
    """

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        output_min: float = -float("inf"),
        output_max: float = float("inf"),
        integral_max: float = 100.0,
    ):
        """
        Initialize PID controller.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_min: Minimum output value
            output_max: Maximum output value
            integral_max: Maximum integral accumulator (anti-windup)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral_max = integral_max

        # State variables
        self.integral = 0.0
        self.last_error = 0.0
        self.last_derivative = 0.0
        self.last_time = 0.0
        self.initialized = False

    def reset(self) -> None:
        """Reset controller state."""
        self.integral = 0.0
        self.last_error = 0.0
        self.last_derivative = 0.0
        self.last_time = 0.0
        self.initialized = False

    def update(self, error: float, dt: float) -> float:
        """
        Update controller and get output.

        Args:
            error: Current error (setpoint - measured)
            dt: Time step in seconds

        Returns:
            Control output
        """
        if dt <= 0:
            return 0.0

        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        self.integral = max(-self.integral_max, min(self.integral_max, self.integral))
        i_term = self.ki * self.integral

        # Derivative term with smoothing
        if self.initialized:
            derivative = (error - self.last_error) / dt
            # Low-pass filter on derivative (reduce noise)
            alpha = 0.8
            derivative = alpha * derivative + (1 - alpha) * self.last_derivative
            self.last_derivative = derivative
        else:
            derivative = 0.0
            self.initialized = True

        d_term = self.kd * derivative

        # Save state
        self.last_error = error

        # Calculate output with clamping
        output = p_term + i_term + d_term
        output = max(self.output_min, min(self.output_max, output))

        return output

    def set_gains(self, kp: float, ki: float, kd: float) -> None:
        """Update PID gains."""
        self.kp = kp
        self.ki = ki
        self.kd = kd


class PID2D:
    """
    2D PID Controller for position/velocity control.

    Uses separate PID controllers for X and Y axes.
    """

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        output_max: float = 10.0,
    ):
        """
        Initialize 2D PID controller.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_max: Maximum output magnitude
        """
        self.output_max = output_max
        self.pid_x = PIDController(kp, ki, kd, -output_max, output_max)
        self.pid_y = PIDController(kp, ki, kd, -output_max, output_max)

    def reset(self) -> None:
        """Reset both controllers."""
        self.pid_x.reset()
        self.pid_y.reset()

    def update(
        self,
        current: Tuple[float, float],
        target: Tuple[float, float],
        dt: float,
    ) -> Tuple[float, float]:
        """
        Update controller and get 2D output.

        Args:
            current: Current (x, y) position
            target: Target (x, y) position
            dt: Time step

        Returns:
            (vx, vy) velocity output
        """
        error_x = target[0] - current[0]
        error_y = target[1] - current[1]

        vx = self.pid_x.update(error_x, dt)
        vy = self.pid_y.update(error_y, dt)

        # Limit total velocity magnitude
        magnitude = math.sqrt(vx * vx + vy * vy)
        if magnitude > self.output_max:
            scale = self.output_max / magnitude
            vx *= scale
            vy *= scale

        return (vx, vy)

    def set_gains(self, kp: float, ki: float, kd: float) -> None:
        """Update PID gains for both axes."""
        self.pid_x.set_gains(kp, ki, kd)
        self.pid_y.set_gains(kp, ki, kd)


class UnitMovementController:
    """
    High-level movement controller for SC2 units.

    Provides smooth movement with acceleration/deceleration.
    """

    def __init__(
        self,
        max_speed: float = 5.0,
        acceleration: float = 10.0,
        arrival_threshold: float = 0.5,
    ):
        """
        Initialize movement controller.

        Args:
            max_speed: Maximum movement speed
            acceleration: Acceleration rate
            arrival_threshold: Distance to consider "arrived"
        """
        self.max_speed = max_speed
        self.acceleration = acceleration
        self.arrival_threshold = arrival_threshold

        # PID for smooth control
        self.pid = PID2D(kp=2.0, ki=0.1, kd=0.5, output_max=max_speed)

        # State
        self.current_velocity = (0.0, 0.0)

    def reset(self) -> None:
        """Reset controller state."""
        self.pid.reset()
        self.current_velocity = (0.0, 0.0)

    def calculate_velocity(
        self,
        current_pos: Tuple[float, float],
        target_pos: Tuple[float, float],
        dt: float,
    ) -> Tuple[float, float]:
        """
        Calculate optimal velocity towards target.

        Args:
            current_pos: Current (x, y) position
            target_pos: Target (x, y) position
            dt: Time step

        Returns:
            (vx, vy) velocity to apply
        """
        # Calculate distance
        dx = target_pos[0] - current_pos[0]
        dy = target_pos[1] - current_pos[1]
        distance = math.sqrt(dx * dx + dy * dy)

        # Already at target
        if distance < self.arrival_threshold:
            self.current_velocity = (0.0, 0.0)
            return self.current_velocity

        # Use PID for smooth control
        target_velocity = self.pid.update(current_pos, target_pos, dt)

        # Apply acceleration limit
        dvx = target_velocity[0] - self.current_velocity[0]
        dvy = target_velocity[1] - self.current_velocity[1]
        dv_mag = math.sqrt(dvx * dvx + dvy * dvy)

        max_dv = self.acceleration * dt
        if dv_mag > max_dv and dv_mag > 0:
            scale = max_dv / dv_mag
            dvx *= scale
            dvy *= scale

        # Update velocity
        new_vx = self.current_velocity[0] + dvx
        new_vy = self.current_velocity[1] + dvy

        # Limit to max speed
        speed = math.sqrt(new_vx * new_vx + new_vy * new_vy)
        if speed > self.max_speed:
            scale = self.max_speed / speed
            new_vx *= scale
            new_vy *= scale

        # Slow down near target (arrival)
        slow_distance = self.max_speed * 0.5  # Distance to start slowing
        if distance < slow_distance:
            scale = distance / slow_distance
            new_vx *= scale
            new_vy *= scale

        self.current_velocity = (new_vx, new_vy)
        return self.current_velocity

    def get_next_position(
        self,
        current_pos: Tuple[float, float],
        target_pos: Tuple[float, float],
        dt: float,
    ) -> Tuple[float, float]:
        """
        Calculate next position after applying velocity.

        Args:
            current_pos: Current position
            target_pos: Target position
            dt: Time step

        Returns:
            Next (x, y) position
        """
        vx, vy = self.calculate_velocity(current_pos, target_pos, dt)
        return (current_pos[0] + vx * dt, current_pos[1] + vy * dt)


class FormationController:
    """
    Controller for maintaining unit formations.

    Uses multiple PID controllers for cohesive group movement.
    """

    def __init__(self, formation_radius: float = 3.0):
        """
        Initialize formation controller.

        Args:
            formation_radius: Desired spacing between units
        """
        self.formation_radius = formation_radius
        self.unit_controllers: dict = {}

    def get_controller(self, unit_id: int) -> UnitMovementController:
        """Get or create controller for a unit."""
        if unit_id not in self.unit_controllers:
            self.unit_controllers[unit_id] = UnitMovementController()
        return self.unit_controllers[unit_id]

    def calculate_formation_velocity(
        self,
        unit_id: int,
        unit_pos: Tuple[float, float],
        formation_pos: Tuple[float, float],
        group_velocity: Tuple[float, float],
        dt: float,
    ) -> Tuple[float, float]:
        """
        Calculate velocity for unit to maintain formation.

        Args:
            unit_id: Unit identifier
            unit_pos: Current unit position
            formation_pos: Target position in formation
            group_velocity: Average velocity of the group
            dt: Time step

        Returns:
            (vx, vy) velocity
        """
        controller = self.get_controller(unit_id)

        # Get formation-following velocity
        formation_vel = controller.calculate_velocity(unit_pos, formation_pos, dt)

        # Blend with group velocity for cohesion
        blend = 0.3  # How much to match group velocity
        vx = formation_vel[0] * (1 - blend) + group_velocity[0] * blend
        vy = formation_vel[1] * (1 - blend) + group_velocity[1] * blend

        return (vx, vy)

    def remove_unit(self, unit_id: int) -> None:
        """Remove controller for a unit."""
        if unit_id in self.unit_controllers:
            del self.unit_controllers[unit_id]
