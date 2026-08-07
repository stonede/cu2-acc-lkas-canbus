# Project status

Last consolidated: 2026-08-07.

## Goal

Develop a safe, reproducible path toward comma.ai/openpilot support for a 2013 European Honda Accord VIII CU2 with K24 engine, automatic transmission, OEM ACC and LKAS.

## Current state

### Completed or available

- Two straight-through T-harnesses have been prepared: one at the camera and one at the ACC unit.
- The vehicle CAN has been passively captured in idle, regular driving, ACC, ACC+LKAS, ACC braking and CMBS scenarios.
- Eight source CSV captures are stored in `research/can/data/`.
- A reproducible analyzer and generated report exist in `research/can/`.
- A CU2-specific DBC covers all 40 IDs observed in the supplied captures, with confidence notes.
- The standard Nidec `0x1FA` brake command is absent from every capture.
- `0x1C0` is the strongest current candidate for the CU2 brake command and has valid Honda checksum/counter structure.
- A receive-only ESP32 logger exists for the two single-wire serial steering channels.
- The serial logger is deliberately RX-only and retains raw bytes as authoritative data.
- The first in-vehicle logger attempt identified 4.89 V TTL outputs on both
  tested physical-layer modules; direct connection to ESP32 GPIO is prohibited.
- The initial ACC and LKAS connector worksheet has been transcribed into confidence-qualified Markdown and CSV pinout records.

### Strong current conclusions

- The tested CU2 exposes one shared F-CAN carrying the observed ACC, LKAS, PCM, VSA and HUD-related traffic.
- No separate second CAN was found at the ACC unit in the tested facelift car.
- The camera/ACC system and EPS also use two independent single-wire serial paths for lateral steering communication.
- The radar has a separate single-wire connection to the ACC unit; its protocol and direction are not yet confirmed.
- Longitudinal integration cannot assume the standard Honda Nidec `0x1FA` path.

## Major unresolved work

1. Correct and bench-validate the 5 V-to-3.3 V serial logger interface, then
   capture and classify both serial steering directions on the car.
2. Confirm connector-face orientation and exact camera/ACC pin functions with repeatable state-dependent measurements.
3. Confirm whether the radar single-wire link is unidirectional and identify its physical/protocol layer.
4. Validate every `0x1C0` field using annotated captures and bench/closed-course testing.
5. Determine message ownership and fault behaviour when stock nodes are disconnected or frames are missing.
6. Design an electrically fail-safe steering interface with transparent stock pass-through.
7. Decide whether the first openpilot milestone should be lateral-only or combined lateral/longitudinal.
8. Implement vehicle support in openpilot/opendbc only after the passive evidence is sufficient.
9. Implement panda safety rules and fault-injection tests before any active road testing.

## Immediate next milestone

Validate the passive serial logger electrical path before collecting more
vehicle data:

- add verified 5 V-to-3.3 V conversion on both module TX outputs;
- confirm GPIO32/GPIO33 still receive a synthetic 3.3 V, 9600-baud 8E1 stream
  after their prior 3.8 V exposure;
- verify common ground, SLP high, unused module RX high and end-to-end
  continuity;
- repeat stationary captures and, if byte counters remain zero, scope the
  vehicle line, module TX and divided GPIO node simultaneously.

The electrical milestone exits when valid UART activity reaches both ESP32
inputs or the absence/loss of activity has been localized to a specific point
in the signal chain. After that, collect synchronized passive logs with:

- both serial steering channels;
- F-CAN;
- explicit event markers for LKAS enable/disable, lane detection, driver torque, stock steering corrections and faults;
- stable power and timestamping.

The output should be sufficient to establish frame length, direction, checksum, periodicity, command magnitude, feedback fields and timeout behaviour without transmitting anything to the vehicle.
