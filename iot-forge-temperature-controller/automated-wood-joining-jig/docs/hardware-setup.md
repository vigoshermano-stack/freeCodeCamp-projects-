# Hardware setup and wiring

## Bill of materials

| Qty | Part | Purpose |
|---|---|---|
| 1 | ESP32 dev board | Controller + Wi-Fi |
| 1 | NEMA-17 stepper motor | Axis motion |
| 1 | TMC2209 stepper driver | Coil switching |
| 2 | Mechanical limit switch | Homing + end-stop |
| 1 | 12 V DC supply (battery/solar/PSU) | Motor power |
| 1 | LM2596 buck converter | Logic power (5 V / 3.3 V) |
| - | Leadscrew or GT2 belt + pulley | Rotation to linear travel |

## Wiring overview

```
ESP32 GPIO12  -> TMC2209 STEP
ESP32 GPIO14  -> TMC2209 DIR
ESP32 GPIO27  -> Limit switch (other side to GND)
TMC2209 VM    -> 12 V motor supply
TMC2209 GND   -> common ground
LM2596 OUT    -> ESP32 5V / 3V3
```

## Power design notes

- The motor supply (12 V) and the logic supply (5 V / 3.3 V) share a common
  ground but are regulated separately. This is the single most important
  wiring detail for reliability.
- Add decoupling capacitors across the motor supply to absorb the current
  spikes stepper coils produce.
- Set the TMC2209 current limit to match your motor's rated current.

## Homing direction

On power-up the carriage drives slowly toward the home limit switch until it
triggers, then declares that point as position zero. A second limit switch at
the far end acts as a safety end-stop so the carriage can never drive itself
off the rail.
