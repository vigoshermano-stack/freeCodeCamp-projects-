# Wiring: thermocouple to blower

## Signal chain

```
K-type thermocouple -> MAX31855 -> Raspberry Pi (SPI) -> PID loop
Raspberry Pi PWM pin -> logic-level MOSFET gate -> 12 V blower fan
```

## Connections

| From | To | Notes |
|---|---|---|
| Thermocouple + / - | MAX31855 T+ / T- | Mind polarity |
| MAX31855 VIN | Pi 3V3 | |
| MAX31855 GND | Pi GND | |
| MAX31855 SCK / SO / CS | Pi SPI pins | CS on GPIO configurable |
| Pi PWM (e.g. GPIO18) | MOSFET gate | Through a gate resistor |
| MOSFET drain | Fan negative | |
| Fan positive | 12 V supply | |
| Flyback diode | Across fan terminals | Protects against inductive spikes |

## Fail-safe wiring

Wire the MOSFET so that **loss of signal equals fan off**. A software crash or
a disconnected control wire must leave the fire starved of air, never jammed
at full blast.
