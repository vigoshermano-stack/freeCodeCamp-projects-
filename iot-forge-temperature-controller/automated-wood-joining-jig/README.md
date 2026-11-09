# Automated Wood-Joining Jig (ESP32 + MicroPython)

> A precision dowel and mortise-and-tenon positioning jig driven by an ESP32 and stepper motors, controlled from a local web interface with no internet connection required.

[![MicroPython](https://img.shields.io/badge/MicroPython-1.23-blue)](https://micropython.org/)
[![Platform](https://img.shields.io/badge/platform-ESP32-green)](https://www.espressif.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What this project solves

Hand-cutting repetitive joinery is where accuracy dies. By the tenth mortise, your pencil marks have drifted and the joints no longer line up. Full CNC routers fix this, but they cost thousands, need mains power, and usually want a cloud account before they will do anything.

This project takes a different route. It is a **single-purpose, off-grid positioning jig** that nails one family of joints with CNC-grade repeatability, runs off a 12 V battery, and serves its own control page over local Wi-Fi. No internet, no cloud account, no desktop software.

**Who this is for:** carpenters, makers, and workshop tinkerers who want repeatable dowel or mortise spacing without buying a full CNC machine.

## Features

- Stepper-driven axis positioning with limit-switch homing
- MicroPython firmware with a steps-per-mm calculation engine
- Local web interface served directly from the ESP32 over its own access point
- No internet dependency and no cloud accounts
- Battery-friendly 12 V operation
- Preset joint layouts (count, spacing, edge offset)

## Hardware components

| Component | Function | Notes |
|---|---|---|
| ESP32 dev board | Controller + Wi-Fi | Runs MicroPython and the web server |
| NEMA-17 stepper motor | Linear motion | Coupled to leadscrew or belt |
| TMC2209 stepper driver | Current switching | Quiet, microstepped, current-limited |
| Mechanical limit switches (x2) | Homing + safety end-stop | Defines position zero |
| 12 V DC supply | Motor power | Battery, solar, or bench PSU |
| Buck converter (LM2596) | Logic power | Steps 12 V down to 5 V / 3.3 V |

## How it works

The firmware converts a physical measurement into motor steps using one constant:

```
steps_per_mm = (motor_steps_per_rev x microstepping) / travel_per_rev
```

A 200-step motor at 1/16 microstepping on an 8 mm leadscrew gives 400 steps/mm. Moving the carriage 40 mm means pulsing the driver 16,000 times in the right direction.

## Quick start

```bash
# 1. Flash MicroPython to the ESP32 (see docs/hardware-setup.md)
# 2. Copy the firmware to the board
mpremote cp src/*.py :

# 3. Or over the serial REPL, connect and run:
# >>> import main
```

Once the ESP32 boots, it creates a Wi-Fi access point. Connect to it, open `http://192.168.4.1`, and enter count, spacing, and edge offset.

## Project structure

```
src/
  main.py          entry point: boots Wi-Fi AP and web server
  motion.py        stepper control, homing, move_to()
  webapp.py        Microdot routes and HTML form
docs/
  hardware-setup.md   wiring and power design
  calibration.md      tuning steps_per_mm for your machine
tests/
  test_motion.py    unit tests for the positioning math
```

## Usage

1. Power the jig and wait for the access point to appear.
2. Connect a phone or laptop to the jig's Wi-Fi.
3. Open the control page and enter the joint parameters.
4. Press Run. The carriage homes, then steps to each position and pauses for the cut.

## Roadmap

- [ ] Second axis for X-Y positioning (shelf pins, box joints)
- [ ] Automatic tool actuation via servo or solenoid
- [ ] Preset recipes stored on the ESP32 flash
- [ ] Temperature and dust-tolerant enclosure design

## Contributing

Contributions are welcome. Fork the repository, create a feature branch, commit your changes, and open a pull request. Run the tests before submitting.

## License

MIT. See [LICENSE](LICENSE).
