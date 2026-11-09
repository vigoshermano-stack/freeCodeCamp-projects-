"""A self-contained PID controller for forge temperature control.

No external dependencies, so it is trivially unit-testable on any host.
"""


class PIDController:
    """Proportional-Integral-Derivative controller with output clamping."""

    def __init__(self, kp, ki, kd, setpoint, output_limits=(0.0, 100.0)):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.min_output, self.max_output = output_limits
        self._integral = 0.0
        self._previous_error = None

    def reset(self):
        self._integral = 0.0
        self._previous_error = None

    def update(self, measurement, dt):
        """Compute the controller output for a new measurement.

        Args:
            measurement: current temperature in Celsius.
            dt: time elapsed since the previous update, in seconds.
        Returns:
            A clamped output value (fan duty cycle, 0-100).
        """
        error = self.setpoint - measurement

        proportional = self.kp * error

        self._integral += error * dt
        integral = self.ki * self._integral

        if self._previous_error is None:
            derivative = 0.0
        else:
            derivative = self.kd * (error - self._previous_error) / dt
        self._previous_error = error

        output = proportional + integral + derivative
        return self._clamp(output)

    def _clamp(self, value):
        if value < self.min_output:
            return self.min_output
        if value > self.max_output:
            return self.max_output
        return value
