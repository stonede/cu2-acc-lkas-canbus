# Serial steering research

## Why this path matters

The tested CU2 does not expose the expected openpilot-compatible CAN steering-command frames. OEM lateral control appears to use two independent 12 V single-wire serial channels between the LKAS camera/controller and EPS.

A CU2 openpilot port therefore likely needs dedicated serial-steering hardware or a gateway that can reproduce the stock protocol while preserving fail-safe pass-through.

## Current protocol status

Based on `reddn/LINInterfaceV2` and `mlocoteta/serialSteeringHardware`:

- 9600 baud, 8 data bits, even parity, 1 stop bit (`8E1`) is strongly
  supported on the subject vehicle by captures 3 and 4;
- 4-byte LKAS-to-EPS framing on GPIO33/blue wire is strongly supported on the
  subject vehicle;
- 5-byte EPS-to-LKAS framing on GPIO32/white wire is strongly supported on the
  subject vehicle;
- first-byte plausibility rule `(byte >> 4) < 4`;
- checksum is calculated from preceding bytes, folded into 7 bits and placed in the `0x80–0xFF` range.

The ESP32 was configured for 9600 8E1 and captured 4,087 frames on channel A
and 20,063 frames on channel B. The analyzer reports checksum-valid 4-byte and
5-byte streams at approximately 100 frames/s per channel. Field meanings,
message ownership outside the observed direction mapping and the claim that
this is standard LIN remain provisional.

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

TJA1020/TJA1021-style boards are being used as single-wire physical-layer
converters. Their use does not prove the protocol is standard LIN.

The tested board terminals follow transceiver nomenclature:

```text
RX terminal -> TJA1021 RXD -> output to MCU
TX terminal -> TJA1021 TXD -> input from MCU
```

The current receive-only path is therefore vehicle single-wire line -> module
`LIN` -> TJA1021 `RXD` / terminal `RX` -> ESP32 UART `RX`. The successful
captures used a direct RX-to-ESP32 connection with no added resistors or level
converter. Measure the `RX`/`RXD` high level before reusing this wiring, and use
level conversion if it exceeds 3.6 V. Keep the `TX`/`TXD` terminals disconnected
because the earlier TX test measured 4.89 V and raised the ESP32 GPIOs to
approximately 3.8 V.

The physical channel mapping is now also constrained: the white T-harness wire
(LKAS connector pin 3) was connected to GPIO32 and carried the 5-byte
EPS-to-LKAS candidate; the blue T-harness wire (LKAS connector pin 5) was
connected to GPIO33 and carried the 4-byte LKAS-to-EPS candidate. Continuity
from the connector cavities to the harness wires should still be recorded.

## Initial in-vehicle capture result

The first in-vehicle attempt on 2026-08-07 produced two clean host sessions but
zero received UART bytes on both channels. A subsequent electrical check found
4.89 V on both module TX outputs with the ESP32 disconnected and approximately
3.8 V at GPIO32/GPIO33 when directly connected. The tested TX/TXD outputs are
therefore not ESP32-safe and the zero-byte captures are not evidence against
the now strongly supported 9600 8E1 framing.

The follow-up test then moved both data taps to the pins marked `RX` and
produced captures 3 and 4. Full measurements, capture counts, the terminal
nomenclature and the ordered retest procedure are recorded in the
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
