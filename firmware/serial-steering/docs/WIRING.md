# Receive-only wiring

> **Safety:** keep the factory LKAS camera/controller ↔ EPS wiring intact. Use a
> straight-through T-harness and connect this logger only as a parallel tap. Do
> not power the ESP32 from vehicle 12 V.

```text
Vehicle 12 V  ── fuse ──> VIN, module A
              └─ fuse ──> VIN, module B
Vehicle GND  ───────────> GND, module A
              └────────> GND, module B
              └────────> ESP32 GND
Serial line candidate A ─> LIN, module A
Serial line candidate B ─> LIN, module B
Module A TX ─> 5 V-to-3.3 V level conversion ─> ESP32 GPIO32
Module B TX ─> 5 V-to-3.3 V level conversion ─> ESP32 GPIO33
Module A/B RX ─> no ESP32 connection; verify it remains logic HIGH
Module A/B SLP ─> no ESP32 connection in MVP; verify it is held HIGH
Module A/B INH ─> not connected
ESP32 power ─> USB only; never vehicle 12 V directly
```

On LINTTL3-style boards, `TX` is the TTL data output and `RX` is the TTL data
input. The logger connects only to each module's `TX`. Cheap modules may expose
5 V logic even though a bare TJA1021 has MCU-compatible thresholds. Measure the
actual module output before connecting it to an ESP32 and add proper 5 V-to-3.3 V
level conversion when needed.

The defaults target a classic ESP32-WROOM-32/`esp32dev`. GPIO32 and GPIO33 may
be unavailable or unsuitable on ESP32-C3, ESP32-S3, or WROVER/PSRAM boards.
Change only `kChannelARxGpio` and `kChannelBRxGpio` in
`include/app_config.h` after checking the selected board's schematic. UART1 and
UART2 TX pins are deliberately set to `UART_PIN_NO_CHANGE`, and their TX ring
buffers are zero bytes.

Before vehicle use, feed both module inputs from a separate 9600-baud 8E1 test
source, confirm valid records for 30 minutes, and verify with a scope or logic
analyzer that no ESP32 pin is driving either vehicle serial line.
