# Serial steering research

## Why this path matters

The tested CU2 does not expose the expected openpilot-compatible CAN steering-command frames. OEM lateral control appears to use two independent 12 V single-wire serial channels between the LKAS camera/controller and EPS.

A CU2 openpilot port therefore likely needs dedicated serial-steering hardware or a gateway that can reproduce the stock protocol while preserving fail-safe pass-through.

## Current protocol hypotheses

Based on `reddn/LINInterfaceV2` and `mlocoteta/serialSteeringHardware`:

- 9600 baud;
- 8 data bits, even parity, 1 stop bit (`8E1`);
- 4-byte LKAS-to-EPS candidate frames observed on GPIO33/blue wire;
- 5-byte EPS-to-LKAS candidate frames observed on GPIO32/white wire;
- first-byte plausibility rule `(byte >> 4) < 4`;
- checksum is calculated from preceding bytes, folded into 7 bits and placed in the `0x80–0xFF` range.

The checksum-valid lengths and direction mapping are strongly supported by
captures 3 and 4. Field meanings and the claim that this is standard LIN
remain provisional.

## Logger implementation

The repository contains a receive-only ESP32 logger in [`firmware/serial-steering/`](../firmware/serial-steering/README.md).

Properties:

- captures both channels concurrently using UART1 and UART2;
- default RX pins GPIO32 and GPIO33 on classic ESP32-WROOM-32;
- UART TX pins are deliberately unassigned;
- TX buffers are disabled;
- outputs timestamped JSONL over UART0;
- supports raw, forced 4-byte, forced 5-byte and auto-classification modes;
- keeps raw bytes authoritative;
- provides host capture and analysis tools.

The implementation must remain passive until the protocol is independently understood.

## Physical-layer warning

TJA1020/TJA1021-style boards are being used as single-wire physical-layer converters. Their use does not prove the protocol is standard LIN.

Cheap LINTTL3 boards may expose 5 V TTL output. Measure the board output and level-shift to 3.3 V before an ESP32 input when required.

Important board-label finding from the follow-up vehicle test: on the two boards
used here, readable data reached the ESP32 from the pins marked `RX`, not the
pins marked `TX`. The successful captures used a direct RX-to-ESP32 connection
with no added resistors or level converter. This is board-specific evidence;
measure the pin marked `RX` directly before reusing this wiring, and use level
conversion if it exceeds 3.6 V. Keep the pins marked `TX` disconnected because
the earlier TX test measured 4.89 V and raised the ESP32 GPIOs to approximately
3.8 V.

The physical channel mapping is now also constrained: the white T-harness wire
(LKAS connector pin 3) was connected to GPIO32 and carried the 5-byte
EPS-to-LKAS candidate; the blue T-harness wire (LKAS connector pin 5) was
connected to GPIO33 and carried the 4-byte LKAS-to-EPS candidate. Continuity
from the connector cavities to the harness wires should still be recorded.

## Initial in-vehicle capture result

The first in-vehicle attempt on 2026-08-07 produced two clean host sessions but
zero received UART bytes on both channels. A subsequent electrical check found
4.89 V on both module TX outputs with the ESP32 disconnected and approximately
3.8 V at GPIO32/GPIO33 when directly connected. The tested module outputs are
therefore not ESP32-safe and the zero-byte captures are not valid evidence
against the protocol hypothesis.

The follow-up test then moved both data taps to the pins marked `RX` and
produced captures 3 and 4. Full measurements, capture counts, the label
discrepancy and the ordered retest procedure are recorded in the
[2026-08-07 vehicle test report](../firmware/serial-steering/docs/VEHICLE_TEST_2026-08-07.md).

## Capture goals

For each channel determine:

1. idle level and voltage range;
2. baud, parity and stop bits;
3. direction and message ownership;
4. frame length and inter-frame gap;
5. checksum validity;
6. periodicity and timeout;
7. command/feedback fields;
8. relationship to steering angle, driver torque and LKAS state;
9. startup, shutdown and fault sequences.

## Suggested synchronized scenarios

- ignition on, engine off;
- engine running, vehicle stationary;
- straight driving with LKAS unavailable;
- LKAS ready but not actively correcting;
- left and right lane corrections;
- driver override at multiple torque levels;
- lane loss and LKAS disengagement;
- stock ACC/LKAS fault or module restart, only in a controlled environment.

Mark events in the serial log when a passenger or stationary operator is
available, and capture F-CAN at the same time. For solo driving, leave the
laptop alone; the host analyzer derives LKAS-active intervals after the run.

## Active interface requirements

Any later active board should default to hardware pass-through without software. A reset, brownout, watchdog event or unplugged controller must not leave the stock LKAS-to-EPS path interrupted or driven to an unsafe level.

The community-reported DoRaN V1 approach uses fail-safe pass-through and is a useful design reference, but its exact circuit and behaviour still need to be captured in this repository before being treated as canonical.
