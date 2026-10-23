# Desk Bike

A ProForm XP 185 U exercise bike turned into an under-desk bike. The
bike's console stays unplugged; an ESP32 takes over the 8-pin harness
from the base:

- drives the magnetic-brake gearmotor through an H-bridge to one of 8
  resistance levels, closed loop on the motor's feedback potentiometer;
- reads cadence from the crank reed switch and tracks ride time and
  distance;
- a 1.3" OLED + EC11 encoder module is the local UI: turn for
  resistance, push for the next page, Back to coast, Confirm to restore.

This design covers the hardware and wiring. The behaviour (resistance
levels, ride stats, heart rate from a BLE chest strap) lives in
[`desk-bike.yaml`](https://github.com/moellere/esphome/blob/main/desk-bike.yaml),
which also documents the calibration steps.

Built: the author's own bike.
