# Calibrating steps-per-mm for your machine

The positioning accuracy depends entirely on one constant: `STEPS_PER_MM`.

```
steps_per_mm = (motor_steps_per_rev x microstepping) / travel_per_rev
```

## Example

- Motor: 200 steps/rev (1.8 degree stepper)
- Microstepping: 1/16 (set on the TMC2209)
- Leadscrew travel: 8 mm per revolution

```
steps_per_mm = (200 x 16) / 8 = 400
```

## Verifying by measurement

1. Home the carriage.
2. Command a 100 mm move.
3. Measure the actual travel with calipers.
4. Correct the constant:

```
corrected = STEPS_PER_MM x (commanded_mm / measured_mm)
```

Repeat until the commanded and measured distances match within your tolerance
(0.1 mm is realistic for a leadscrew build).
