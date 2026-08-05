# Hardware and capture

## Available hardware

- Two custom straight-through T-harnesses: camera and ACC-unit locations.
- CANable v2.0 Pro for passive CAN capture.
- ESP32 development board.
- Two LINTTL3-style TJA1020/TJA1021 single-wire physical-layer converter modules.
- Multimeter (UT61E+).
- Windows host with SavvyCAN and Python tooling.

## Connector documentation

Use [`CONNECTOR_PINOUTS.md`](CONNECTOR_PINOUTS.md) for the current
reverse-engineered pin tables. The tables are evidence-qualified and are not an
official service-manual pinout.

Before fabricating or reconnecting a harness, verify connector-face versus
harness-side orientation. Pin numbering can be mirrored when the viewing
direction is not explicit.

## Grounding

All passive interfaces that exchange logic signals must share a reference ground with the vehicle-side transceiver modules. Any ESP32 GND pin connected to the board ground plane is electrically equivalent; use the mechanically convenient one after checking the board schematic.

Do not connect an ESP32 GPIO directly to a vehicle 8–12 V single-wire line.

## CAN T-harness topology

For each CAN conductor, the stock path remains continuous and the logger is a parallel branch:

```text
female connector ----+---- male connector
                     |
                     +---- CANable input
```

The same topology applies to CAN-H, CAN-L and reference ground. A three-port WAGO can implement the electrical parallel connection during bench work, although an automotive-quality crimp/splice is preferred for permanent vehicle installation.

## CAN termination

A passive logger attached to an already terminated vehicle bus must not add another 120-ohm terminator. The CANable termination jumper should therefore be removed for in-vehicle tapping.

A resistance near 120 ohms on an isolated bench harness with one enabled CANable terminator can be normal. With the CANable terminator removed and the harness disconnected from the vehicle, a high resistance such as tens of kilohms is also expected. On the fully connected, powered-down vehicle bus, approximately 60 ohms between CAN-H and CAN-L is the usual two-terminator expectation, but the exact measurement point and module sleep state matter.

## Serial logger topology

Keep the stock LKAS-to-EPS wiring intact. Connect each serial candidate wire only to the LIN/single-wire input of one physical-layer module. Connect the module's TTL output to an ESP32 RX pin through level conversion if the module outputs 5 V logic.

Canonical wiring and firmware constraints live in [`firmware/serial-steering/docs/WIRING.md`](../firmware/serial-steering/docs/WIRING.md).

## Power

- Power ESP32 by USB during the passive-logging milestone.
- Do not feed vehicle 12 V directly into the ESP32.
- Power the single-wire transceiver boards from an appropriately fused supply according to their actual board design.
- Verify whether module `RX`, `SLP` and `INH` pins have onboard pull-ups or require explicit biasing.

## Capture discipline

For every run, record:

- date, vehicle configuration and firmware version;
- physical connector and pin used, including connector viewing direction;
- interface serial number and termination state;
- ignition/engine/brake/ACC/LKAS state and explicit event markers;
- whether ACC, LKAS or CMBS was active;
- whether the connector was connected, back-probed or disconnected;
- anomalies, dashboard warnings and blown fuses;
- hashes of raw output files.

Never edit a raw capture in place. Store derived/normalized copies separately.

## Known incident: stop-light fuse

During earlier probing, fuse no. 12 (15 A, stop lights) was blown. Symptoms included an ACC error and inability to move the selector because the brake-pedal interlock no longer saw the stop-light circuit. Replacing the fuse restored operation; the ACC warning cleared after a short drive.

Lesson: a listen-only interface does not protect against wiring mistakes, probe slips or an incorrectly built harness. Verify continuity and absence of shorts before reconnecting modules.
