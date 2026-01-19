# -*- coding: utf-8 -*-
"""
PID Controller for Unit Movement Optimization

PID (Proportional-Integral-Derivative) control for smooth unit acceleration/deceleration.
Based on drone control systems and mechanical engineering principles.

This provides physically optimal movement for units like Mutalisks,
enabling efficient hit-and-run tactics.
"""

from dataclasses import dataclass
from typing import Optional
import math

try:
    from sc2.position import Point2
    SC2_AVAILABLE = True
except ImportError:
    class Point2:
        def __init__(self, coords):
            self.x, self.y = coords[0], coords[1]
    SC2_AVAILABLE = False


@dataclass
class PIDConfig:
    """PID Controller configuration"""
    kp: float = 1.0  # Proportional gain
    ki: float = 0.1  # Integral gain
    kd: float = 0.05  # Derivative gain
    max_integral: float = 10.0  # Maximum integral accumulation
    max_output: float = 5.0  # Maximum output velocity


class PIDController:
    """
    PID Controller for unit movement.
    
    Provides smooth acceleration/deceleration based on:
    - Proportional: Current error
    - Integral: Accumulated error (eliminates steady-state error)
    - Derivative: Rate of change (reduces overshoot)
    
    Usage:
        controller = PIDController()
        target_velocity = controller.update(current_position, target_position, current_velocity, dt)
    """
    
    def __init__(self, config: PIDConfig = None):
        """
        Initialize PID Controller.
        
        Args:
            config: PID configuration (uses defaults if None)
        """
        self.config = config or PIDConfig()
        self.integral_x = 0.0
        self.integral_y = 0.0
        self.last_error_x = 0.0
        self.last_error_y = 0.0
    
    def update(
        self,
        current_pos: Point2,
        target_pos: Point2,
        current_vel: Point2,
        dt: float = 0.1
    ) -> Point2:
        """
        Update PID controller and return desired velocity.
        
        Args:
            current_pos: Current unit position
            target_pos: Target position
            current_vel: Current unit velocity
            dt: Time step (seconds)
            
        Returns:
            Desired velocity vector (Point2)
        """
        # Calculate error (difference between target and current)
        error_x = target_pos.x - current_pos.x
        error_y = target_pos.y - current_pos.y
        
        # Proportional term
        p_x = self.config.kp * error_x
        p_y = self.config.kp * error_y
        
        # Integral term (accumulate error)
        self.integral_x += error_x * dt
        self.integral_y += error_y * dt
        
        # Limit integral to prevent windup
        self.integral_x = max(-self.config.max_integral, min(self.config.max_integral, self.integral_x))
        self.integral_y = max(-self.config.max_integral, min(self.config.max_integral, self.integral_y))
        
        i_x = self.config.ki * self.integral_x
        i_y = self.config.ki * self.integral_y
        
        # Derivative term (rate of change)
        if dt > 0:
            d_x = self.config.kd * (error_x - self.last_error_x) / dt
            d_y = self.config.kd * (error_y - self.last_error_y) / dt
        else:
            d_x = 0.0
            d_y = 0.0
        
        # Update last error
        self.last_error_x = error_x
        self.last_error_y = error_y
        
        # Calculate output (P + I + D)
        output_x = p_x + i_x + d_x
        output_y = p_y + i_y + d_y
        
        # Limit output magnitude
        magnitude = math.sqrt(output_x*output_x + output_y*output_y)
        if magnitude > self.config.max_output:
            scale = self.config.max_output / magnitude
            output_x *= scale
            output_y *= scale
        
        return Point2((output_x, output_y))
    
    def reset(self):
        """Reset controller state (for new target or unit)."""
        self.integral_x = 0.0
        self.integral_y = 0.0
        self.last_error_x = 0.0
        self.last_error_y = 0.0


class UnitMovementController:
    """
    High-level unit movement controller using PID.
    
    Provides optimal movement for units like Mutalisks,
    enabling efficient hit-and-run tactics.
    """
    
    def __init__(self, pid_config: PIDConfig = None):
        """
        Initialize movement controller.
        
        Args:
            pid_config: PID configuration
        """
        self.pid = PIDController(pid_config)
        self.current_target = None
    
    def calculate_movement(
        self,
        unit_pos: Point2,
        target_pos: Point2,
        current_vel: Point2,
        dt: float = 0.1
    ) -> Point2:
        """
        Calculate optimal movement vector using PID control.
        
        Args:
            unit_pos: Current unit position
            target_pos: Target position
            current_vel: Current unit velocity
            dt: Time step
            
        Returns:
            Desired velocity vector
        """
        return self.pid.update(unit_pos, target_pos, current_vel, dt)
    
    def reset(self):
        """Reset controller state."""
        self.pid.reset()
        self.current_target = None
