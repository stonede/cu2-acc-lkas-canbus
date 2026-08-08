# Project status

Last consolidated: 2026-08-08.

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
- Corrected captures identify GPIO32/channel A as a checksum-valid 5-byte
  EPS-to-LKAS candidate and GPIO33/channel B as a checksum-valid 4-byte
  LKAS-to-EPS candidate, both at approximately 100 frames/s.
- The successful captures used the physical-layer board pins marked `RX`
  directly to GPIO32/GPIO33, with no added resistors. This pin-label behavior
  is board-specific; the pins marked `TX` remain unsafe because the earlier
  direct measurement reached approximately 4.89 V.
- The working harness mapping is white wire/LKAS pin 3 -> GPIO32 -> 5-byte
  EPS-to-LKAS candidate, and blue wire/LKAS pin 5 -> GPIO33 -> 4-byte
  LKAS-to-EPS candidate. Continuity from connector cavities to the T-harness
  still needs to be recorded explicitly.
- Capture 4 contains an automatically detected 3.931-second LKAS-active interval;
  analysis no longer depends on operator markers during a solo drive.
- The USB logger path has been hardened with compact records, a 460800-baud
  buffered console, a larger Windows receive buffer and host sequence-gap
  accounting. The revised firmware is flashed to the test ESP32.
- The initial ACC and LKAS connector worksheet has been transcribed into confidence-qualified Markdown and CSV pinout records.

### Strong current conclusions

- The tested CU2 exposes one shared F-CAN carrying the observed ACC, LKAS, PCM, VSA and HUD-related traffic.
- No separate second CAN was found at the ACC unit in the tested facelift car.
- The camera/ACC system and EPS also use two independent single-wire serial paths for lateral steering communication.
- The radar has a separate single-wire connection to the ACC unit; its protocol and direction are not yet confirmed.
- Longitudinal integration cannot assume the standard Honda Nidec `0x1FA` path.

## Major unresolved work

1. Validate the hardened host path under full two-channel vehicle traffic and
   collect a capture with zero host sequence gaps.
2. Confirm connector-face orientation and exact camera/ACC pin functions with repeatable state-dependent measurements.
3. Confirm whether the radar single-wire link is unidirectional and identify its physical/protocol layer.
4. Validate every `0x1C0` field using annotated captures and bench/closed-course testing.
5. Determine message ownership and fault behaviour when stock nodes are disconnected or frames are missing.
6. Design an electrically fail-safe steering interface with transparent stock pass-through.
7. Decide whether the first openpilot milestone should be lateral-only or combined lateral/longitudinal.
8. Implement vehicle support in openpilot/opendbc only after the passive evidence is sufficient.
9. Implement panda safety rules and fault-injection tests before any active road testing.

## Immediate next milestone

Validate the hardened logger under full vehicle traffic, requiring live
`bad=0`, `seq_missing=0`, a confirmed compact mode and zero firmware queue-drop
counters. Before repeating the direct RX-pin wiring, record the RX-to-GND high
levels and confirm they remain below 3.6 V. Then collect synchronized passive
logs with:

- both serial steering channels;
- F-CAN;
- automatic LKAS enable/disable intervals from the serial stream; optional
  passenger-entered markers may supplement them, but the driver must not
  operate the laptop;
- stable power and timestamping.

The output should be sufficient to establish frame length, direction, checksum, periodicity, command magnitude, feedback fields and timeout behaviour without transmitting anything to the vehicle.
