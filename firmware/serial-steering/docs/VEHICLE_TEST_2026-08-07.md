# Initial in-vehicle serial logger test — 2026-08-07

## Purpose

This test was the first attempt to capture both candidate LKAS↔EPS single-wire
channels with the receive-only ESP32 logger and two LINTTL3-style physical-layer
modules on the subject vehicle.

The result does **not** validate or disprove the current 9600-baud 8E1 protocol
hypothesis. The test exposed an out-of-spec 5 V logic interface that must be
corrected before the absence of received bytes can be interpreted.

## Electrical observations

Measurements were made with the modules connected to the running vehicle:

| Measurement | Channel A | Channel B | Interpretation |
|---|---:|---:|---|
| Module VIN to GND | approximately 13 V | approximately 13 V | Vehicle supply present |
| Candidate vehicle data line to GND | approximately 8.5 V | approximately 8.5 V | Idle/average voltage only; a DMM does not prove data activity |
| Module SLP to GND | approximately 4.9 V | approximately 4.9 V | Logic-high sleep control; modules appear enabled |
| ESP32 GPIO to GND while directly connected | approximately 3.8 V on GPIO32 | approximately 3.8 V on GPIO33 | Above the ESP32 GPIO limit; unsafe |
| Module TX to GND with ESP32 disconnected | 4.89 V | 4.89 V | Confirmed 5 V TTL output |

The direct TX-to-GPIO connection was therefore invalid. Espressif documents a
3.6 V GPIO tolerance, while the ESP32 DC characteristics specify a maximum
high-level input voltage of `VDD + 0.3 V`. The observed 3.8 V at GPIO32/GPIO33
exceeded that limit and may indicate conduction through the ESP32 input
protection structure.

References:

- [Espressif ESP32 hardware design FAQ](https://docs.espressif.com/projects/esp-faq/en/latest/hardware-related/hardware-design.html)
- [ESP32 Series Datasheet](https://documentation.espressif.com/esp32_datasheet_en.html)

## Capture results

Both captures ended cleanly and contained valid JSONL statistics from the
firmware. The USB/host logging path was therefore operational.

| Capture | Duration | Valid stats records | Host `bad` lines | Channel A bytes | Channel B bytes | Frames |
|---|---:|---:|---:|---:|---:|---:|
| `captures/1.jsonl` | approximately 412.2 s | 160 total | 5 | 0 | 0 | 0 |
| `captures/2.jsonl` | approximately 95.3 s | 36 total | 2 | 0 | 0 | 0 |
| bounded live read | approximately 12 s | 4 total | startup noise observed | 0 | 0 | 0 |

All reported UART parity, frame, FIFO-overflow, buffer-full and queue-drop
counters remained zero. Both channel directions remained `UNKNOWN` because no
UART bytes entered either parser.

The malformed host lines were concentrated around ESP32 reset/startup and are
consistent with boot output being observed at the logger's 921600-baud console
setting. They are not evidence of vehicle-side serial traffic.

## Interpretation

Confirmed by this test:

- the ESP32 firmware boots and emits valid JSONL statistics;
- the CP2102 USB serial path and host capture script work;
- both tested LINTTL3-style module TX outputs are approximately 4.89 V;
- direct connection of either TX output to an ESP32 GPIO is unsafe;
- no UART bytes were counted during these particular captures.

Not established by this test:

- whether either candidate vehicle line was actively switching;
- whether the selected vehicle pins are the two steering serial channels;
- whether the modules reproduced vehicle-side transitions on their TX pins;
- whether the previously overstressed ESP32 GPIO32/GPIO33 inputs remain fully
  functional;
- baud rate, parity, frame length, direction or checksum.

The zero-byte result must not be used to reject the 9600-baud 8E1 hypothesis.
The electrical interface must first be corrected and validated.

## Required correction before reconnecting the ESP32

Do not reconnect either raw module TX output directly to the ESP32. Use a
proper 5 V-tolerant input buffer powered from 3.3 V, or for the current passive
9600-baud prototype use one resistor divider per channel:

```text
Module TX ---- 10 kΩ ----+---- ESP32 GPIO32 or GPIO33
                         |
                        20 kΩ
                         |
                        GND
```

At the measured 4.89 V input this produces approximately 3.26 V. Two 10 kΩ
resistors in series may be used for the 20 kΩ leg. The divider and ESP32 must
share the module ground.

Before attaching an ESP32, power the module and verify the divider output with
a DMM. It should be approximately 3.2–3.3 V and must remain below 3.6 V.

## Ordered next steps

1. Install and independently measure the two 5 V-to-3.3 V input dividers or a
   suitable 5 V-tolerant 3.3 V buffer.
2. With vehicle/module power off, verify continuity from module A TX through
   the level converter to GPIO32 and from module B TX to GPIO33.
3. Verify common-ground continuity, confirm SLP remains logic high, and confirm
   each unused module RX input is held logic high rather than floating.
4. Validate GPIO32 and GPIO33 on the bench after the 3.8 V exposure. Feed each
   channel a known 3.3 V, 9600-baud 8E1 test stream and require error-free
   capture before returning to the vehicle.
5. Repeat stationary captures in documented states: ignition on/engine off,
   engine running, LKAS unavailable, and LKAS ready. Add explicit event markers.
6. If byte counters remain zero, scope or logic-analyze three points at once:
   the vehicle candidate line, the module TX output, and the divided ESP32 GPIO
   node. This will identify whether activity is absent on the vehicle line,
   lost in the transceiver, or lost in the level converter/wiring.
7. Only after stationary traffic is observed, perform synchronized controlled
   driving captures with F-CAN and markers for LKAS engagement, correction,
   lane loss and driver override.

No active transmission to either vehicle single-wire channel is authorized by
this test or by these next steps.
