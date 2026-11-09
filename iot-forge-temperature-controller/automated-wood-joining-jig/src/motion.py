"""Motion control for the wood-joining jig.

Converts physical measurements in millimetres into stepper pulses, homes
the carriage against a limit switch, and drives the axis to target
positions.
"""

from machine import Pin
import time

STEP_PIN = 12
DIR_PIN = 14
LIMIT_PIN = 27

# 200 steps/rev motor, 1/16 microstepping, 8 mm travel per revolution
MOTOR_STEPS_PER_REV = 200
MICROSTEPPING = 16
TRAVEL_PER_REV_MM = 8.0
STEPS_PER_MM = (MOTOR_STEPS_PER_REV * MICROSTEPPING) / TRAVEL_PER_REV_MM

PULSE_WIDTH_US = 400

step_pin = Pin(STEP_PIN, Pin.OUT)
dir_pin = Pin(DIR_PIN, Pin.OUT)
limit_pin = Pin(LIMIT_PIN, Pin.IN, Pin.PULL_UP)

current_mm = 0.0


def home():
    """Drive toward the home switch and declare that point as zero."""
    global current_mm
    dir_pin.value(0)
    while limit_pin.value() == 1:
        _pulse()
    current_mm = 0.0
    return current_mm


def move_to(target_mm):
    """Move the carriage to an absolute position in millimetres."""
    global current_mm
    delta = target_mm - current_mm
    dir_pin.value(1 if delta > 0 else 0)
    steps = int(abs(delta) * STEPS_PER_MM)
    for _ in range(steps):
        _pulse()
    current_mm = target_mm
    return current_mm


def layout_positions(count, spacing, offset):
    """Return the list of positions for a row of evenly spaced joints."""
    return [offset + i * spacing for i in range(count)]


def _pulse():
    step_pin.value(1)
    time.sleep_us(PULSE_WIDTH_US)
    step_pin.value(0)
    time.sleep_us(PULSE_WIDTH_US)
