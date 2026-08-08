# Receive-only wiring

> **Safety:** keep the factory LKAS camera/controller <-> EPS wiring intact.
> Use a straight-through T-harness and connect this logger only as a parallel
> tap. Do not power the ESP32 from vehicle 12 V.

```text
Vehicle 12 V  -- fuse --> VIN, module A
              \-- fuse --> VIN, module B
Vehicle GND  ----------------> GND, module A
              \--------------> GND, module B
              \--------------> ESP32 GND
Serial line candidate A (white T-harness wire, LKAS pin 3) --> LIN, module A
Serial line candidate B (blue T-harness wire, LKAS pin 5) ---> LIN, module B
Module A pin marked RX -------> ESP32 GPIO32, direct on the tested board
Module B pin marked RX -------> ESP32 GPIO33, direct on the tested board
Module A/B pins marked TX ----> no ESP32 connection
Module A/B SLP ---------------> no ESP32 connection in MVP; verify HIGH
Module A/B INH ---------------> not connected
ESP32 power ------------------> USB only; never vehicle 12 V directly
```

## Important board-label observation

The two boards used in the vehicle test behaved differently from the expected
LINTTL3 naming: readable data reached the ESP32 only from the pins marked `RX`,
not from the pins marked `TX`. The working test connection was therefore the
pin marked `RX` directly to the ESP32 GPIO, with no added resistor or level
converter.

Treat this as a board-specific empirical observation, not as proof that every
pin marked `RX` is an ESP32-safe output. The labels may describe the
transceiver's viewpoint rather than the direction seen by the logger.

Before repeating a direct connection, measure the pin marked `RX` to GND while
the module is powered and the vehicle interface is active. Every high level
must stay below the ESP32 maximum; use a 5 V-to-3.3 V divider or buffer if it
exceeds 3.6 V. Keep the pin marked `TX` disconnected from the ESP32.

## Evidence from the earlier TX test

The two modules tested in the subject vehicle on 2026-08-07 produced **4.89 V**
at the pins marked `TX` with the ESP32 disconnected. Direct connection of those
pins raised GPIO32/GPIO33 to approximately **3.8 V**, above Espressif's
documented 3.6 V GPIO tolerance. Those `TX` pins must never be connected
directly to an ESP32.

The resistor-divider circuit remains the fallback whenever the pin actually
used as the data output is above 3.6 V. For the measured 4.89 V `TX` output, a
10 kOhm series resistor and 20 kOhm resistor from the GPIO node to GND produces
approximately 3.26 V. A proper 5 V-tolerant input buffer powered at 3.3 V is
preferred for a robust final design.

The tested channel mapping is: white/LKAS pin 3/module A/GPIO32 for the
5-byte EPS-to-LKAS candidate, and blue/LKAS pin 5/module B/GPIO33 for the
4-byte LKAS-to-EPS candidate. This is strongly supported by captures 3 and 4;
record continuity before treating the connector cavity assignment as final.

See the [vehicle test report](VEHICLE_TEST_2026-08-07.md) for the label
discrepancy, capture evidence and required voltage check.

## ESP32 board constraints

The defaults target a classic ESP32-WROOM-32/`esp32dev`. GPIO32 and GPIO33 may
be unavailable or unsuitable on ESP32-C3, ESP32-S3, or WROVER/PSRAM boards.
Change only `kChannelARxGpio` and `kChannelBRxGpio` in
`include/app_config.h` after checking the selected board's schematic. UART1
and UART2 TX pins are deliberately set to `UART_PIN_NO_CHANGE`, and their TX
ring buffers are zero bytes.

Before vehicle use, feed both module data outputs from a separate 9600-baud 8E1
test source, confirm valid records for 30 minutes, and verify with a scope or
logic analyzer that no ESP32 pin is driving either vehicle serial line.
