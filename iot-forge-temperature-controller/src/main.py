"""Forge temperature control loop entry point.

Reads the thermocouple, runs the PID loop, drives the blower via PWM, logs
every reading, and enforces fail-safe interlocks. The hardware-specific
GPIO and sensor wiring is isolated so the control logic stays testable.
"""

import argparse
import time

from pid_controller import PIDController
from sensor import ThermocoupleFault
from logger import ForgeLogger

HARD_LIMIT_C = 950.0   # emergency ceiling
LOOP_PERIOD_S = 0.5


def run(sensor, set_blower_duty, setpoint, logger):
    pid = PIDController(kp=2.0, ki=0.5, kd=1.0, setpoint=setpoint)
    last = time.monotonic()
    try:
        while True:
            now = time.monotonic()
            dt = now - last
            last = now

            try:
                temp = sensor.read_celsius()
            except ThermocoupleFault:
                set_blower_duty(0)  # unknown temperature -> safe state
                raise

            if temp > HARD_LIMIT_C:
                set_blower_duty(0)  # over-temperature -> cut the blast
                print("OVER-TEMPERATURE: blower off")
                time.sleep(LOOP_PERIOD_S)
                continue

            duty = pid.update(temp, dt if dt > 0 else LOOP_PERIOD_S)
            set_blower_duty(duty)
            logger.log(temp, setpoint, duty)
            print(f"temp={temp:.1f}C  setpoint={setpoint}C  duty={duty:.0f}%")
            time.sleep(LOOP_PERIOD_S)
    finally:
        set_blower_duty(0)  # always leave the fire starved on exit


def main():
    parser = argparse.ArgumentParser(description="Forge PID controller")
    parser.add_argument("--setpoint", type=float, default=790.0)
    args = parser.parse_args()

    from sensor import build_hardware_sensor
    import board
    import pwmio

    sensor = build_hardware_sensor(board.D5)
    fan = pwmio.PWMOut(board.D18, frequency=25000)

    def set_blower_duty(percent):
        fan.duty_cycle = int(max(0, min(100, percent)) / 100 * 65535)

    logger = ForgeLogger()
    try:
        run(sensor, set_blower_duty, args.setpoint, logger)
    finally:
        logger.close()


if __name__ == "__main__":
    main()
