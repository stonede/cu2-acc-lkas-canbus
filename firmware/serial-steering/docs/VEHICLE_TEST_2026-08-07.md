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
| historical capture 1 (not present in the current checkout) | approximately 412.2 s | 160 total | 5 | 0 | 0 | 0 |
| historical capture 2 (not present in the current checkout) | approximately 95.3 s | 36 total | 2 | 0 | 0 | 0 |
| `research/serial-steering/data/3.jsonl` | approximately 46.1 s | 10 total | 3 | 2,043 | 2,044 | 4,087 |
| `research/serial-steering/data/4.jsonl` | approximately 188.5 s | 42 total | 18 | 10,030 | 10,033 | 20,063 |
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

## Ordered next steps from the initial TX test

The following list records the safety plan before the board-label discrepancy
was found. For the currently tested wiring, use the later RX-pin clarification
and the current checklist in `docs/WIRING.md`.

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
   engine running, LKAS unavailable, and LKAS ready. Markers are optional when
   a stationary operator or passenger is available.
6. If byte counters remain zero, scope or logic-analyze three points at once:
   the vehicle candidate line, the module TX output, and the divided ESP32 GPIO
   node. This will identify whether activity is absent on the vehicle line,
   lost in the transceiver, or lost in the level converter/wiring.
7. Only after stationary traffic is observed, perform synchronized controlled
   driving captures with F-CAN. For solo tests, do not operate the laptop while
   driving; derive LKAS-active intervals from the serial data after the drive.

No active transmission to either vehicle single-wire channel is authorized by
this test or by these next steps.

## Follow-up captures and logger hardening — 2026-08-08

After moving the data connections from the pins marked `TX` to the pins marked
`RX`, captures 3 and 4 established valid traffic on both inputs at approximately
100 frames/s per channel. The operator reports that these captures used a
direct RX-to-ESP32 connection with no added resistors or level converter.
The high-level voltage of the pins marked `RX` was not recorded separately in
that test, so direct operation is evidence of functionality only, not of GPIO
electrical safety.
Channel A/GPIO32 consistently carried checksum-valid 5-byte EPS-to-LKAS
candidates and was connected to the white T-harness wire (LKAS pin 3); channel
B/GPIO33 carried checksum-valid 4-byte LKAS-to-EPS candidates and was connected
to the blue T-harness wire (LKAS pin 5). Capture 4
contained one automatically detectable LKAS-active interval from 132.123 s to
136.054 s (394 frames), with provisional steering command values from -21 to
86. No operator markers were required.

Firmware statistics reported no capture/output queue drops, but host sequence
analysis found 2,438 missing records in capture 3 and 15,387 in capture 4. The
loss was therefore localized to the UART0/CP2102/Windows host path rather than
the two vehicle UART inputs.

The logger was hardened as follows:

- the USB console was reduced from 921600 to 460800 baud;
- compact raw frame JSON became the firmware and host default;
- UART0 now uses an interrupt-driven VFS RX/TX driver and TX buffer;
- the Windows receive buffer is requested at 1 MiB and stale input is cleared;
- the host records global sequence gaps in `*.gaps.jsonl` and session metadata;
- the analyzer reconstructs provisional fields offline and automatically lists
  LKAS-active intervals;
- bootloader noise is preserved separately from live malformed-line counts.

The revised firmware was flashed to the test ESP32. A 20-second USB-only smoke
test with the vehicle disconnected confirmed the compact command on its first
attempt, a configured 1 MiB receive buffer, clean shutdown, zero live malformed
records and zero sequence gaps. Vehicle-load validation is still required on
the next capture. The earlier divider recommendation applies to the pins
marked `TX`; it must not be used to claim that the pins marked `RX` are safe
without a direct voltage measurement.
