# ESP32 Honda Serial Steering Passive Logger — Implementation Plan

## 1. Mission

Implement a compile-ready, receive-only logger for the two independent 12 V single-wire serial channels between the Honda LKAS camera/controller and the EPS controller.

The first milestone is **data acquisition only**. The firmware must never transmit onto either vehicle serial line. It must capture both directions concurrently, timestamp the data, recover protocol frames, validate checksums, emit raw records, and expose provisional decoded fields for later reverse engineering.

This plan is intended to be handed directly to Codex in the target repository.

## 2. Safety and non-goals

### Mandatory safety constraints

1. The capture UARTs are RX-only. Do not assign ESP32 TX pins to either LINTTL3 module.
2. Do not call `uart_write_bytes()`, `uart_tx_chars()`, Arduino `SerialX.write()`, or any equivalent on the two capture UARTs.
3. Do not implement steering injection, frame replacement, forwarding, or bus arbitration in this milestone.
4. Raw bytes are authoritative. Every decoded signal must be explicitly marked as provisional.
5. UART failure, parser failure, queue overflow, or host disconnection must not cause any output on the vehicle serial lines.
6. Do not enable Wi-Fi or Bluetooth in the MVP; they add timing and power variability without helping the logger.
7. Keep the factory LKAS↔EPS wiring intact through a straight-through T-harness. The logger is only a parallel tap.

### Non-goals

- No openpilot control integration.
- No CAN transmit or receive requirement.
- No active LIN commander/master behavior.
- No modification of stock serial frames.
- No on-device plotting.
- No claim that the protocol is standard LIN. The TJA1021/SIT1021 boards are used only as 12 V single-wire physical-layer converters.

## 3. Known facts from the reference repositories

The following protocol assumptions are taken from `reddn/LINInterfaceV2` and must be implemented as configurable hypotheses, not unquestionable truth:

- Both serial channels use **9600 baud, 8 data bits, even parity, 1 stop bit (8E1)**.
- LKAS-to-EPS command frames appear to be 4 bytes long.
- EPS-to-LKAS feedback frames appear to be 5 bytes long.
- A candidate first byte has `(byte >> 4) < 4`.
- The checksum byte is generated from the preceding bytes:

```cpp
uint8_t serial_checksum(const uint8_t *data, size_t length_without_checksum) {
    uint8_t total = 0;
    for (size_t i = 0; i < length_without_checksum; ++i) {
        total = static_cast<uint8_t>(total + data[i]);
    }
    total = static_cast<uint8_t>(256U - total);
    total = static_cast<uint8_t>(total % 128U);
    total = static_cast<uint8_t>(total + 128U);
    return total;
}
```

- For a 4-byte frame, checksum byte `b3` is calculated from `b0..b2`.
- For a 5-byte frame, checksum byte `b4` is calculated from `b0..b3`.

Reference implementation:

- <https://github.com/reddn/LINInterfaceV2>
- <https://raw.githubusercontent.com/reddn/LINInterfaceV2/master/src/main.cpp>
- <https://raw.githubusercontent.com/reddn/LINInterfaceV2/master/src/LKAStoEPS.h>
- <https://raw.githubusercontent.com/reddn/LINInterfaceV2/master/src/EPStoLKAS.h>
- <https://raw.githubusercontent.com/reddn/LINInterfaceV2/master/src/checksums.h>
- <https://raw.githubusercontent.com/reddn/LINInterfaceV2/master/src/createLINMessages.h>
- <https://raw.githubusercontent.com/reddn/LINInterfaceV2/master/src/canMessages.h>
- <https://github.com/mlocoteta/serialSteeringHardware>

Important: `LINInterfaceV2` targets an STM32 Blue Pill and includes active interception/transmission. It is a protocol reference, not firmware to port line-for-line.

## 4. Hardware assumptions and configurable pin map

Default target assumption: classic ESP32-WROOM-32 / `esp32dev` board. Keep all GPIO values in one configuration header so a different ESP32 variant can be selected without changing capture logic.

Suggested default mapping:

| Function | ESP32 resource | Default GPIO |
|---|---:|---:|
| USB log/console | UART0 | board default |
| Channel A receive | UART1 RX | GPIO32 |
| Channel B receive | UART2 RX | GPIO33 |
| Channel A TX | not assigned | `UART_PIN_NO_CHANGE` |
| Channel B TX | not assigned | `UART_PIN_NO_CHANGE` |

The firmware must compile with TX buffers disabled for UART1 and UART2.

Create `include/app_config.h` with at least:

```cpp
#pragma once

#include "driver/uart.h"
#include "driver/gpio.h"

namespace app_config {
constexpr uart_port_t kChannelAUart = UART_NUM_1;
constexpr uart_port_t kChannelBUart = UART_NUM_2;
constexpr gpio_num_t kChannelARxGpio = GPIO_NUM_32;
constexpr gpio_num_t kChannelBRxGpio = GPIO_NUM_33;
constexpr int kVehicleBaud = 9600;
constexpr int kConsoleBaud = 921600;
constexpr size_t kUartRxBufferBytes = 4096;
constexpr size_t kUartEventQueueDepth = 64;
constexpr size_t kFrameQueueDepth = 512;
constexpr uint32_t kStatsPeriodMs = 5000;
constexpr uint32_t kAutoClassifyWindowMs = 5000;
}
```

Do not assume the GPIO map is valid for ESP32-C3, ESP32-S3, or WROVER boards with PSRAM. Document how to change it.

## 5. Required repository work

Before editing:

1. Inspect the existing repository layout, build system, board type, coding style, and current dependencies.
2. Preserve unrelated files and functionality.
3. If a PlatformIO project already exists, extend it rather than replacing it blindly.
4. If the repository is empty or has no embedded build, use PlatformIO with ESP-IDF.
5. Record any assumption that cannot be derived from the repository in the final implementation summary.

Recommended project structure:

```text
platformio.ini
sdkconfig.defaults
include/
  app_config.h
  capture_types.h
  uart_capture.h
  frame_parser.h
  honda_serial_protocol.h
  log_output.h
  console_commands.h
src/
  main.cpp
  uart_capture.cpp
  frame_parser.cpp
  honda_serial_protocol.cpp
  log_output.cpp
  console_commands.cpp
test/
  test_checksum/
  test_frame_parser/
  test_protocol_decode/
tools/
  capture_serial.py
  analyze_log.py
docs/
  WIRING.md
  LOG_FORMAT.md
README.md
```

## 6. Build configuration

Prefer ESP-IDF because its UART driver exposes buffered RX, event queues, parity errors, frame errors, FIFO overflow, and buffer overflow events.

Suggested `platformio.ini` baseline:

```ini
[platformio]
default_envs = esp32dev

[env:esp32dev]
platform = espressif32
board = esp32dev
framework = espidf
monitor_speed = 921600
build_type = debug
build_flags =
    -Wall
    -Wextra
    -Werror=return-type
    -DLOG_LOCAL_LEVEL=ESP_LOG_INFO
```

Adapt the board and upload settings to the actual repository and physical ESP32 board.

## 7. UART configuration

Configure UART1 and UART2 independently with:

- baud: 9600
- data bits: 8
- parity: even
- stop bits: 1
- flow control: disabled
- source clock: default/APB unless the target requires another supported clock
- RX ring buffer: at least 4096 bytes
- TX ring buffer: 0 bytes
- event queue: at least 64 entries
- TX pin: unassigned
- RX pin: from `app_config.h`

Illustrative ESP-IDF configuration:

```cpp
uart_config_t config{
    .baud_rate = app_config::kVehicleBaud,
    .data_bits = UART_DATA_8_BITS,
    .parity = UART_PARITY_EVEN,
    .stop_bits = UART_STOP_BITS_1,
    .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    .rx_flow_ctrl_thresh = 0,
    .source_clk = UART_SCLK_DEFAULT,
};

ESP_ERROR_CHECK(uart_param_config(uart_num, &config));
ESP_ERROR_CHECK(uart_set_pin(
    uart_num,
    UART_PIN_NO_CHANGE,
    rx_gpio,
    UART_PIN_NO_CHANGE,
    UART_PIN_NO_CHANGE));
ESP_ERROR_CHECK(uart_driver_install(
    uart_num,
    app_config::kUartRxBufferBytes,
    0,
    app_config::kUartEventQueueDepth,
    &event_queue,
    0));
```

Where supported, set a small RX timeout. Do not over-tune FIFO thresholds until real logs are available.

## 8. Capture architecture

Use four FreeRTOS tasks:

1. `channel_a_uart_task`
2. `channel_b_uart_task`
3. `parser_task`
4. `output_task`

Optional fifth task:

5. `console_task` for commands received through UART0.

### UART tasks

Each UART task must:

- block on its UART event queue;
- read all available bytes on `UART_DATA`;
- attach a monotonic timestamp from `esp_timer_get_time()`;
- push byte chunks into a bounded capture queue;
- count and report `UART_FIFO_OVF`, `UART_BUFFER_FULL`, `UART_PARITY_ERR`, `UART_FRAME_ERR`, and unknown events;
- flush/reset only the affected UART after an actual overflow;
- never print directly from the high-priority capture task;
- never block indefinitely on the downstream queue;
- increment a drop counter if the queue is full.

Define:

```cpp
enum class ChannelId : uint8_t { kA, kB };

enum class DirectionGuess : uint8_t {
    kUnknown,
    kLkasToEps,
    kEpsToLkas,
};

struct ByteChunk {
    int64_t capture_time_us;
    ChannelId channel;
    uint16_t length;
    std::array<uint8_t, 128> data;
};
```

If a UART event contains more than one `ByteChunk`, split it safely.

### Timestamp semantics

`capture_time_us` is the time the firmware serviced the RX event, not a hardware timestamp for the first bit on the wire. Document this explicitly.

For optional approximate per-byte times, derive backwards from the last serviced byte using 11 serial bits per character at 9600 baud. Never present estimated timestamps as exact.

## 9. Frame parser

Implement one independent parser state per channel. The parser must support:

- forced 4-byte mode;
- forced 5-byte mode;
- auto-detect mode;
- unknown/raw mode;
- loss of synchronization and recovery;
- rolling-window checksum search;
- preservation of bytes that do not form a valid frame.

### Initial framing hypothesis

Candidate frame start:

```cpp
bool is_candidate_start(uint8_t value) {
    return (value >> 4U) < 4U;
}
```

Candidate validity:

```cpp
bool valid_4_byte_frame(std::span<const uint8_t, 4> frame) {
    return is_candidate_start(frame[0]) &&
           serial_checksum(frame.data(), 3) == frame[3];
}

bool valid_5_byte_frame(std::span<const uint8_t, 5> frame) {
    return is_candidate_start(frame[0]) &&
           serial_checksum(frame.data(), 4) == frame[4];
}
```

### Resynchronization algorithm

Do not use only a blind byte counter. Use a rolling buffer:

1. Append each byte.
2. If channel mode is known, test the expected frame length at every possible candidate start.
3. On a valid checksum, emit the frame and consume through its end.
4. If no frame matches, retain enough trailing bytes to detect a frame that starts near the end of the buffer.
5. Emit discarded bytes as `raw_fragment` records in diagnostic mode.
6. Never silently discard data without incrementing a counter.

### Auto-classification

During the first configurable time window, score both hypotheses independently:

- count valid 4-byte windows;
- count valid 5-byte windows;
- count candidate starts;
- calculate valid checksum rate;
- calculate continuity of valid frames;
- penalize overlapping or mutually inconsistent matches.

Choose a direction only when one score clearly exceeds the other. Suggested initial rule:

- minimum 20 valid frames;
- valid ratio at least 90%;
- winning score at least 3× the competing score.

Otherwise keep the channel `unknown` and continue raw logging. These thresholds must be configurable because real data may require adjustment.

Expected association:

- 4-byte frames → `LKAS_TO_EPS`
- 5-byte frames → `EPS_TO_LKAS`

## 10. Protocol decoding

All decoders must return both raw fields and provisional engineering values.

### 4-byte LKAS-to-EPS candidate

From the reference firmware:

```cpp
struct LkasToEpsDecoded {
    uint8_t counter_raw;
    uint8_t big_steer_raw;
    uint8_t little_steer_raw;
    bool lkas_on_candidate;
    uint8_t flags_raw;
    int16_t apply_steer_candidate;
};
```

Candidate decode:

```cpp
const uint8_t big = frame[0] & 0x0F;
const uint8_t little = frame[1] & 0x1F;
const uint16_t raw9 = static_cast<uint16_t>((big & 0x07) << 5) | little;
const int16_t signed_value = (big & 0x08)
    ? static_cast<int16_t>(raw9) - 256
    : static_cast<int16_t>(raw9);

result.counter_raw = frame[0] >> 5;
result.big_steer_raw = big;
result.little_steer_raw = little;
result.lkas_on_candidate = ((frame[1] >> 5) & 0x01) != 0;
result.flags_raw = frame[2];
result.apply_steer_candidate = signed_value;
```

Do not assign physical torque units. The result is a signed raw command candidate in the range -256..255.

### 5-byte EPS-to-LKAS candidate

Store:

```cpp
struct EpsToLkasDecoded {
    uint8_t big_driver_torque_raw;
    uint8_t little_driver_torque_raw;
    int16_t driver_torque_candidate;
    uint16_t motor_torque_raw_10bit;
    int16_t motor_torque_signed_candidate;
    uint8_t flags_b0_raw;
    uint8_t flags_b1_raw;
    uint8_t flags_b2_raw;
};
```

Candidate driver-torque decode may use the same signed 9-bit packing as the command frame, but label it provisional:

```cpp
const uint8_t big = frame[0] & 0x0F;
const uint8_t little = frame[1] & 0x1F;
const uint16_t raw9 = static_cast<uint16_t>((big & 0x07) << 5) | little;
const int16_t driver_candidate = (big & 0x08)
    ? static_cast<int16_t>(raw9) - 256
    : static_cast<int16_t>(raw9);
```

Candidate motor-torque packing derived from the reference CAN mapping:

```cpp
const uint16_t motor_raw =
    (static_cast<uint16_t>((frame[2] >> 4) & 0x03) << 8) |
    (static_cast<uint16_t>((frame[2] >> 3) & 0x01) << 7) |
    static_cast<uint16_t>(frame[3] & 0x7F);

const int16_t motor_signed_candidate = (motor_raw & 0x0200)
    ? static_cast<int16_t>(motor_raw) - 1024
    : static_cast<int16_t>(motor_raw);
```

Do not invert signs to match openpilot conventions in the capture firmware. Any sign normalization belongs in offline analysis.

### Decoder confidence

Every decoded record must contain a confidence/status field, for example:

```text
raw_only
checksum_valid_hypothesis
direction_auto_classified
field_decode_provisional
```

## 11. Data model and output format

Use newline-delimited JSON (NDJSON/JSONL) for the MVP because two 9600-baud channels fit comfortably within a 921600-baud USB console when records are emitted per frame rather than per byte.

Every output line must be valid standalone JSON. Do not mix human-readable log text into stdout. Send diagnostics as structured records too.

### Required record types

#### Session record

```json
{"type":"session","schema":1,"firmware":"0.1.0","git":"<hash>","boot_id":"<random>","vehicle_baud":9600,"format":"8E1","channel_a_gpio":32,"channel_b_gpio":33,"capture_mode":"rx_only"}
```

#### Frame record

```json
{"type":"frame","seq":123,"t_us":4567890,"channel":"A","direction":"LKAS_TO_EPS","len":4,"data":"20A080E0","checksum_ok":true,"apply_steer_candidate":0,"lkas_on_candidate":true,"decode_status":"field_decode_provisional"}
```

#### Raw fragment

```json
{"type":"raw_fragment","seq":124,"t_us":4569000,"channel":"A","data":"FF7A","reason":"resync_discard"}
```

#### UART error

```json
{"type":"uart_error","t_us":4570000,"channel":"B","error":"parity","count":3}
```

#### Statistics

```json
{"type":"stats","t_us":5000000,"channel":"A","bytes":4321,"valid_4":200,"valid_5":0,"checksum_fail":4,"parity_err":0,"frame_err":0,"fifo_overflow":0,"queue_drop":0,"direction":"LKAS_TO_EPS"}
```

#### Marker

```json
{"type":"mark","t_us":6000000,"text":"LKAS enabled"}
```

### Output requirements

- Hex bytes must use uppercase, two characters per byte, no separators.
- `seq` must increase monotonically across all record types that represent captured data.
- Use a dedicated output queue and output task.
- If output cannot keep up, drop decoded/detail fields before dropping raw frame data.
- If raw frame data must be dropped, emit a later statistics record with the exact drop count.
- Do not use floating-point values on the ESP32 unless necessary.

## 12. Console commands

Commands arrive on UART0 and must begin with `!` so they cannot be confused with JSON output.

Implement at least:

```text
!status
!mark <free text>
!stats reset
!channel A auto|raw|4|5
!channel B auto|raw|4|5
!decode on|off
!help
```

Commands must not change the electrical state of either vehicle channel. There must be no `send`, `inject`, `forward`, or `replay` command.

## 13. Host capture tool

Implement `tools/capture_serial.py` using Python 3 and pyserial.

Required behavior:

- arguments: serial port, baud, output path;
- default baud: 921600;
- write each valid line immediately to a `.jsonl` file;
- retain malformed lines in a separate `.bad.log` file;
- periodically flush; optionally call `os.fsync()` on clean shutdown;
- add host UTC timestamp metadata to a sidecar session file;
- accept keyboard input for `!mark` and `!status` without corrupting captured output;
- handle Ctrl+C cleanly;
- print a concise live summary without rewriting the JSONL file.

Do not require a GUI.

## 14. Offline analysis tool

Implement a minimal `tools/analyze_log.py` that:

- reads JSONL;
- reports frame counts and checksum rates per channel;
- reports UART and queue errors;
- plots, when present:
  - driver torque candidate;
  - apply steer candidate;
  - motor torque signed candidate;
  - candidate LKAS/flag values;
- never filters out raw values by default;
- allows channel and time-range selection;
- labels all decoded plots as provisional.

Keep plotting dependencies optional and documented.

## 15. Tests

### Native unit tests

Provide host/native tests for:

1. checksum calculation for 3-byte and 4-byte payloads;
2. valid 4-byte frame recognition;
3. valid 5-byte frame recognition;
4. rejection of corrupted checksums;
5. parser recovery after an inserted or removed byte;
6. parser recovery after arbitrary noise;
7. simultaneous valid data on two parser instances;
8. signed 9-bit command decode boundaries: -256, -1, 0, 1, 255;
9. candidate 10-bit motor decode boundaries;
10. auto-classification with synthetic 4-byte and 5-byte streams;
11. output serialization validity;
12. queue-drop accounting.

### Hardware-in-the-loop tests

Before connection to a vehicle:

1. Feed synthetic 9600 8E1 streams from a second UART adapter or microcontroller.
2. Verify that neither capture UART TX pin is assigned or toggles.
3. Verify 30 minutes of capture with no FIFO overflow or queue drops.
4. Inject parity and framing errors and confirm structured error records.
5. Disconnect and reconnect a stream; confirm automatic recovery.
6. Confirm that USB output interruption cannot block UART capture indefinitely.

## 16. Acceptance criteria

The implementation is complete only when:

- `pio run` succeeds for the selected ESP32 environment;
- native tests pass;
- both UARTs capture concurrently at 9600 8E1;
- UART1/UART2 have no assigned TX pins and zero TX ring-buffer size;
- source search confirms there is no transmit call on the two vehicle UARTs;
- JSONL output remains machine-readable under normal operation;
- every frame includes raw bytes and checksum status;
- decoder fields are explicitly provisional;
- parser resynchronizes after corruption;
- all UART overflow/parity/frame errors are counted;
- the README contains wiring, flashing, capture, and troubleshooting instructions;
- the final implementation report lists every changed file and all unresolved assumptions.

## 17. Documentation requirements

### `docs/WIRING.md`

The original generic wiring sketch below assumed a conventional LINTTL3 `TX`
output label. The tested boards use transceiver-side nomenclature instead:
`RX` terminal -> TJA1021 `RXD` -> output to the MCU, while `TX` terminal ->
TJA1021 `TXD` -> input from the MCU. The current board mapping and voltage
warning in `docs/WIRING.md` supersede the historical sketch.

Document this current receive-only topology:

```text
Vehicle single-wire line -> module LIN
Module A terminal RX / TJA1021 RXD -> ESP32 GPIO32 (UART1 RX)
Module B terminal RX / TJA1021 RXD -> ESP32 GPIO33 (UART2 RX)
Module A/B terminal TX / TJA1021 TXD -> no ESP32 connection
```

The older generic sketch below is retained as historical planning context only;
it is not current wiring.

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

Explicitly state that the current path is vehicle single-wire line -> module
`LIN` -> TJA1021 `RXD` / terminal `RX` -> ESP32 UART `RX`. The historical
TX/TXD divider test is not current wiring. Measure the actual `RX`/`RXD` high
level before connecting it to the ESP32 and use level conversion if it exceeds
3.6 V.

### `docs/LOG_FORMAT.md`

Document all JSON record types, units, timestamp semantics, and schema versioning.

### `README.md`

Include:

- purpose;
- safety warning;
- supported/default ESP32 board;
- build and flash commands;
- GPIO configuration;
- host capture command examples;
- how to force 4-byte or 5-byte parsing;
- how to interpret checksum statistics;
- known unknowns.

## 18. Implementation order

Implement in small, reviewable steps:

1. Repository inspection and build baseline.
2. Configuration and data types.
3. One RX-only UART with structured raw output.
4. Second RX-only UART.
5. UART event/error accounting.
6. Checksum implementation and unit tests.
7. Independent rolling parsers.
8. Auto-classification.
9. Provisional decoders.
10. Output queue and NDJSON schema.
11. Console markers/status.
12. Host capture tool.
13. Minimal offline analyzer.
14. Documentation.
15. Full build/test run and final report.

## 19. Instructions to Codex

- Start by inspecting the current repository; do not assume it is empty.
- Produce actual compile-ready code, not pseudocode-only placeholders.
- Preserve unrelated existing work.
- Use strict error checking and bounded queues/buffers.
- Keep receive-only behavior mechanically obvious in the code and documentation.
- Add a CI-friendly/native test target when possible.
- Run the available build and test commands before finishing.
- If the actual ESP32 board is unknown, keep `esp32dev` as the documented default and make the board/GPIO selection easy to change.
- Do not add active steering control, serial forwarding, LIN headers, breaks, wake-up pulses, or bus transmission.
- At completion, provide:
  1. changed-file list;
  2. build/test results;
  3. exact flash and capture commands;
  4. unresolved hardware/protocol assumptions;
  5. a confirmation that UART1/UART2 TX pins remain unassigned and no vehicle-UART transmit API is called.
