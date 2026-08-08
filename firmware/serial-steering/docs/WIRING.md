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
Module A terminal RX / TJA1021 RXD --> ESP32 GPIO32 (UART1 RX)
Module B terminal RX / TJA1021 RXD --> ESP32 GPIO33 (UART2 RX)
Module A/B terminal TX / TJA1021 TXD -> no ESP32 connection
Module A/B SLP ---------------> no ESP32 connection in MVP; verify HIGH
Module A/B INH ---------------> not connected
ESP32 power ------------------> USB only; never vehicle 12 V directly
```

## Module terminal nomenclature and current receive path

The tested boards use transceiver-side terminal names, not an anomalous
LINTTL3 direction:

```text
RX terminal --> TJA1021 RXD --> output to MCU / ESP32 UART RX
TX terminal --> TJA1021 TXD --> input from MCU
```

Therefore the current receive-only path is:

```text
vehicle single-wire line --> module LIN --> TJA1021 RXD / terminal RX --> ESP32 UART RX
```

Captures 3 and 4 used the terminal marked `RX` directly to ESP32 GPIO32/GPIO33,
with no added resistor or level converter. This proves that the path carried
traffic, but it does not prove that every `RX` output is electrically safe for
an ESP32 input.

Before repeating a direct connection, measure the pin marked `RX` to GND while
the module is powered and the vehicle interface is active. Every high level
must stay below the ESP32 maximum; use a 5 V-to-3.3 V divider or buffer if it
exceeds 3.6 V. Keep the pin marked `TX` disconnected from the ESP32.

## Historical TX-path safety test (not current wiring)

This section records the earlier, invalid connection to the terminal marked
`TX` / TJA1021 `TXD`. It is retained as safety evidence only. It is not the
current receive-only wiring and must not be used as the default connection.

The two modules tested in the subject vehicle on 2026-08-07 produced **4.89 V**
at the pins marked `TX` with the ESP32 disconnected. Direct connection of those
pins raised GPIO32/GPIO33 to approximately **3.8 V**, above Espressif's
documented 3.6 V GPIO tolerance. Those `TX` pins must never be connected
directly to an ESP32.

For this historical `TX`/`TXD` output only, a resistor-divider circuit was
considered as a fallback. For the measured 4.89 V output, a 10 kOhm series
resistor and 20 kOhm resistor from the GPIO node to GND produces approximately
3.26 V. A proper 5 V-tolerant input buffer powered at 3.3 V is preferred for a
robust final design. Do not apply this diagram to the current `RX`/`RXD`
receive-only path unless a separate measurement proves that level conversion
is required there.

The tested current channel mapping is: white/LKAS pin 3/module A/terminal
RX/TJA1021 RXD/GPIO32 for the
5-byte EPS-to-LKAS candidate, and blue/LKAS pin 5/module B/GPIO33 for the
4-byte LKAS-to-EPS candidate. This is strongly supported by captures 3 and 4;
record continuity from the connector cavity to the T-harness before treating
the connector assignment as final.

See the [vehicle test report](VEHICLE_TEST_2026-08-07.md) for the terminal
nomenclature, capture evidence and required RX/RXD voltage check.

## ESP32 board constraints

The defaults target a classic ESP32-WROOM-32/`esp32dev`. GPIO32 and GPIO33 may
be unavailable or unsuitable on ESP32-C3, ESP32-S3, or WROVER/PSRAM boards.
Change only `kChannelARxGpio` and `kChannelBRxGpio` in
`include/app_config.h` after checking the selected board's schematic. UART1
and UART2 TX pins are deliberately set to `UART_PIN_NO_CHANGE`, and their TX
ring buffers are zero bytes.

Before vehicle use, feed each module `LIN` input from a separate 9600-baud 8E1
test source, confirm valid records at the corresponding `RXD`/terminal `RX`
output for 30 minutes, and verify with a scope or logic analyzer that no ESP32
pin is driving either vehicle serial line.
