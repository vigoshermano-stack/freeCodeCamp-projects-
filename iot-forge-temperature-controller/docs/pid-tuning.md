# Tuning the PID for your forge

PID gains must match your forge's thermal mass. A setting that is smooth on a
small knife forge will oscillate on a large coal forge.

## Manual tuning (simple and reliable)

1. Set `ki = 0` and `kd = 0`.
2. Raise `kp` until the temperature oscillates steadily around the setpoint.
3. Back `kp` off to about half that value.
4. Increase `ki` slowly until steady-state offset disappears (the fire stops
   sitting a few degrees low).
5. Add `kd` to dampen overshoot as the temperature approaches the setpoint.

## Target windows for high-carbon steel

| Process | Approx. temperature |
|---|---|
| Austenitizing / hardening | 760-850 C (just past non-magnetic ~768 C) |
| Tempering | 180-250 C |
| Annealing | slow controlled cool from above critical |

Always confirm the exact numbers for your specific steel (for example 1084,
O1, 1095) against a metallurgical data sheet.
