"""PID heater controller for Mars habitat thermal management."""


class PIDController:
    """Discrete PID controller for heater power regulation."""

    def __init__(self, kp: float = 0.8, ki: float = 0.02, kd: float = 0.1,
                 output_min: float = 0.0, output_max: float = 1.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self._integral = 0.0
        self._prev_error = 0.0

    def update(self, setpoint: float, measured: float, dt: float) -> float:
        """Compute heater power fraction given setpoint and measured temp."""
        error = setpoint - measured
        self._integral += error * dt
        # Anti-windup: clamp integral term
        max_integral = (self.output_max - self.output_min) / max(self.ki, 1e-9)
        self._integral = max(-max_integral, min(max_integral, self._integral))
        derivative = (error - self._prev_error) / max(dt, 1e-9)
        self._prev_error = error
        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        return max(self.output_min, min(self.output_max, output))

    def reset(self):
        """Reset controller state."""
        self._integral = 0.0
        self._prev_error = 0.0

