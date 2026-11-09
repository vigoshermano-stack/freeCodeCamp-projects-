# IoT Charcoal Forge Temperature Controller (PID + Thermocouple)

> A closed-loop PID controller that holds an exact forge temperature by modulating blower airflow, using a K-type thermocouple and a MAX31855 amplifier. Built for precise heat-treatment of high-carbon steel.

[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-green)](https://www.raspberrypi.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What this project solves

Heat-treating high-carbon steel is unforgiving. Hardening happens in a narrow window around 760-850 C, and judging 790 C from 830 C by the colour of the steel is almost impossible. Miss the window and the blade is ruined.

Most blacksmiths have zero instrumentation on their forge. This project adds a proper **closed-loop control system**: a thermocouple measures the real temperature, a PID algorithm compares it to a target, and a PWM-driven blower fan adjusts the air blast to hold that setpoint. Colour-guessing becomes a measured, repeatable number, and every heat-treat cycle is logged so you can prove the steel saw the right thermal history.

**Who this is for:** bladesmiths, blacksmiths, and metalworking makers who want repeatable heat-treatment instead of guessing by eye.

## Features

- Closed-loop PID control of forge temperature via blower airflow
- K-type thermocouple reading through a MAX31855 (up to ~1372 C)
- PWM blower control through a logic-level MOSFET
- SQLite data logging of every temperature cycle
- Layered fail-safe interlocks: over-temperature cutoff, sensor-fault cutoff, signal-loss safe state
- Runs on a Raspberry Pi with standard GPIO

## Important sensor note

The commonly cited MAX6675 only reads up to ~1024 C, which is below forge
hardening temperatures. This project uses the **MAX31855** (K-type, to ~1372 C)
or the **MAX31856** for higher accuracy and better fault detection.

## Hardware components

| Component | Function | Notes |
|---|---|---|
| Raspberry Pi | Controller | Runs the PID loop and SQLite logging |
| K-type thermocouple | Temperature sensing | Mineral-insulated, Inconel-sheathed probe |
| MAX31855 amplifier | Cold-junction compensation + SPI | Reports open/short faults |
| 12 V blower fan | Air blast actuator | Modulated by PWM |
| Logic-level MOSFET | Switches the 12 V fan | Flyback diode across the motor |
| 12 V DC supply | Fan power | Battery or bench PSU |

## How it works

The control loop runs the classic process-control cycle:

```
sensor -> controller -> actuator -> process -> back to sensor
```

1. The MAX31855 reports the forge temperature over SPI.
2. The PID controller computes a 0-100% output from the error.
3. That output becomes a PWM duty cycle driving the MOSFET and blower.
4. More air raises the fire; the loop repeats twice per second.

PID blends three terms: proportional (current error), integral (accumulated
error, eliminates steady-state offset), and derivative (rate of change, damps
overshoot). Gains must be tuned to your forge's thermal mass.

## Safety first

A device controlling a 1000 C fire must fail safe. The dangerous failure mode
is "too hot," and in an air-blast forge the safe state is "no air."

- Over-temperature cutoff: above the hard limit, blower duty goes to 0%.
- Sensor-fault cutoff: an open/short fault means the temperature is unknown,
  so the blast is shut down immediately.
- Signal-loss safe state: the MOSFET is wired so loss of signal = fan off.
- A physical kill switch and, ideally, an independent hardware thermal cutoff.

## Quick start

```bash
pip install -r requirements.txt
python src/main.py --setpoint 790
```

## Project structure

```
src/
  main.py           control loop entry point
  pid_controller.py PID algorithm
  sensor.py         MAX31855 reading with fault handling
  logger.py         SQLite logging
docs/
  wiring.md         thermocouple -> MAX31855 -> Pi -> MOSFET -> blower
  pid-tuning.md     how to tune Kp, Ki, Kd for your forge
tests/
  test_pid.py       unit tests for the PID algorithm
```

## Roadmap

- [ ] Grafana dashboard for live telemetry
- [ ] Per-blade heat-treat certificate generation
- [ ] Auto-tuning (Ziegler-Nichols) routine
- [ ] Multi-zone forge support

## Contributing

Fork the repository, create a feature branch, commit with clear messages, and
open a pull request. Run the tests before submitting.

## License

MIT. See [LICENSE](LICENSE).
