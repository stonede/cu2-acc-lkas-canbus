# ESP32 serial steering logger

Receive-only logger for the two independent 12 V single-wire serial channels
between a Honda LKAS camera/controller and EPS.

> **Do not connect an ESP32 directly to either 12 V serial line.** Keep the
> factory LKAS↔EPS wiring intact, use suitable physical-layer modules as
> parallel taps and level-shift their TTL outputs when required. The firmware
> never assigns UART1/UART2 TX pins and never transmits on either channel.

## Hardware defaults

| Channel | UART | RX GPIO | Mode |
|---|---:|---:|---|
| A | UART1 | GPIO32 | auto |
| B | UART2 | GPIO33 | auto |

Both inputs are 9600 baud, 8E1. UART0 emits JSONL at 460800 baud. The default
target is a classic ESP32-WROOM-32 PlatformIO `esp32dev` board. Change the board
in `platformio.ini` and pins in `include/app_config.h`; do not reuse this map
blindly on ESP32-C3, ESP32-S3 or WROVER/PSRAM boards. Read
[the wiring guide](docs/WIRING.md) before connecting hardware.

## Build and capture

Run commands from this directory:

```powershell
pio test -e native
pio run -e esp32dev
pio run -e esp32dev -t upload

py -3 -m pip install pyserial
py -3 tools/capture_serial.py COM5 captures/drive.jsonl
py -3 tools/analyze_log.py captures/drive.jsonl
```

The `captures/` directory is local scratch space and is ignored by Git. When
a session is worth keeping, copy the raw JSONL file together with its
`.session.json`, `.bad.log`, and (when present) `.gaps.jsonl` sidecars into
[`research/serial-steering/data/`](../../research/serial-steering/data/).
Put regenerated plots in
[`research/serial-steering/figures/`](../../research/serial-steering/figures/).
Follow the data-management instructions in the research README so that raw
evidence, metadata, and derived figures stay together.

Add `--channel A --start 10 --end 30 --plot` to the analyzer to filter and
plot a capture. Plotting is optional and requires `matplotlib`. The capture
tool requests compact frame JSON by default, increases the host serial receive
buffer where supported, and reports missing sequence numbers while recording.
The analyzer reconstructs provisional decoded fields from the authoritative raw
bytes and automatically lists every detected `lkas_on_candidate` interval, so
manual markers are not required. Use `--decoded-json` only for troubleshooting.

When a passenger or stationary operator is available, the capture tool accepts
these optional commands:

```text
!status
!mark short description
```

The host configures compact decoding automatically. Never operate the laptop or
enter markers while driving.

Auto mode evaluates 4-byte and 5-byte checksum hypotheses over five seconds.
It classifies after at least 20 valid frames, 90% valid candidate attempts and
a 3× lead over the competing hypothesis. Until then, bytes are retained as
`raw_fragment` records. All decoded fields are provisional; raw bytes remain
authoritative.

See [the log format](docs/LOG_FORMAT.md) and the original
[implementation plan](docs/IMPLEMENTATION_PLAN.md). The first in-vehicle test,
including the confirmed 4.89 V module outputs and required electrical
correction, is documented in the
[2026-08-07 vehicle test report](docs/VEHICLE_TEST_2026-08-07.md).

On Windows, an ESP toolchain may misread package paths containing non-ASCII
characters. If an existing `crt0.o` or `libgcc.a` is reported missing, set
`PLATFORMIO_CORE_DIR` to an ASCII-only directory such as `C:\platformio-core`.
