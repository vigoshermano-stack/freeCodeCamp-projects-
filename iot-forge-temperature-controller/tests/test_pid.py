"""Unit tests for the PID controller. Pure Python, no hardware needed."""

import sys

sys.path.insert(0, "src")
from pid_controller import PIDController  # noqa: E402


def test_output_clamped_to_max():
    pid = PIDController(kp=10, ki=0, kd=0, setpoint=800)
    # Large error should saturate the output at 100
    assert pid.update(0, dt=1.0) == 100.0


def test_output_clamped_to_min():
    pid = PIDController(kp=10, ki=0, kd=0, setpoint=800)
    # Measurement above setpoint -> negative raw output -> clamped to 0
    assert pid.update(900, dt=1.0) == 0.0


def test_proportional_response():
    pid = PIDController(kp=1.0, ki=0, kd=0, setpoint=100)
    # error = 10, output = 10
    assert pid.update(90, dt=1.0) == 10.0


def test_integral_accumulates():
    pid = PIDController(kp=0, ki=1.0, kd=0, setpoint=100)
    first = pid.update(90, dt=1.0)   # integral = 10
    second = pid.update(90, dt=1.0)  # integral = 20
    assert second > first


def test_reset_clears_integral():
    pid = PIDController(kp=0, ki=1.0, kd=0, setpoint=100)
    pid.update(90, dt=1.0)
    pid.reset()
    assert pid.update(90, dt=1.0) == 10.0
