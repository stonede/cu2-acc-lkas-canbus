# ESP32 logger — garage cheat sheet

This guide is for the current laptop, ESP32 board and repository checkout. All
required Python packages, PlatformIO/ESP-IDF packages and the CP210x USB driver
are already installed, so no internet connection is required in the garage.

## 0. Current hardware stop condition

The two tested LINTTL3-style modules produce **4.89 V** at their TX outputs.
Direct connection raised ESP32 GPIO32/GPIO33 to approximately **3.8 V**, above
the documented ESP32 GPIO tolerance.

Do not reconnect either raw TX output to the ESP32. Before another vehicle
capture, both channels require verified 5 V-to-3.3 V conversion and the ESP32
inputs must pass a synthetic 3.3 V, 9600-baud 8E1 bench test. See the
[2026-08-07 vehicle test report](VEHICLE_TEST_2026-08-07.md).

For the current passive prototype, use one divider per channel:

```text
Module TX ---- 10 kΩ ----+---- ESP32 GPIO32 or GPIO33
                         |
                        20 kΩ
                         |
                        GND
```

At the measured 4.89 V input, the expected GPIO-node voltage is approximately
3.26 V. Measure the divider output with the ESP32 disconnected before attaching
it. It must remain below 3.6 V and should be approximately 3.2–3.3 V.

## 1. Safety rules

- Power the ESP32 only from the laptop USB port. Never apply vehicle 12 V to
  the ESP32.
- Keep the factory LKAS↔EPS path continuous. Connect the logger only as a
  parallel tap through a straight-through T-harness.
- Never connect an 8–12 V vehicle data wire directly to an ESP32 GPIO.
- Power the physical-layer modules through a correctly fused circuit suitable
  for the actual module design.
- Connect module A TX through verified level conversion to GPIO32. Connect
  module B TX through verified level conversion to GPIO33.
- Do not connect the ESP32 to the modules' RX inputs. The logger is receive-only.
- Maintain a common reference ground between both modules and the ESP32.
- Before vehicle power is applied, verify continuity, absence of shorts, SLP
  high, unused module RX high, and the converted TX voltages.
- Do not move probes or wiring at vehicle connectors while the ignition is on.
- Never run the engine in a closed or insufficiently ventilated garage.

The complete wiring guide is [WIRING.md](WIRING.md).

## 2. Open the terminal

Open **PowerShell** and change to the firmware directory:

```powershell
cd C:\Repos\openpilot\honda-cu2-openpilot\firmware\serial-steering
```

Check the installed tools:

```powershell
py -3 --version
py -3 -m platformio --version
```

The current setup should report Python 3.12 and PlatformIO 6.1.19.

Do not run the PlatformIO serial monitor at the same time as the capture
script. Only one program can own the COM port.

## 3. Detect the ESP32 COM port

Connect the ESP32 with a USB data cable, then run:

```powershell
py -3 -m platformio device list
```

The current board has previously appeared as `COM4`, but the number can change.
Use the port reported by this command in all later commands.

If the list is empty:

1. confirm that the USB cable supports data;
2. unplug and reconnect the ESP32;
3. check Device Manager → Ports (COM & LPT);
4. do not continue until a working COM port is present.

## 4. Flash firmware only when required

The logger firmware is already installed and does not need to be flashed before
every capture. Reflash only after a firmware change or to restore the known
build:

```powershell
py -3 -m platformio run -e esp32dev -t upload --upload-port COM4
```

Replace `COM4` with the detected port. A successful upload ends with `SUCCESS`
and `Hash of data verified`. The command works offline on this laptop because
the complete toolchain is already cached.

Do not flash while the raw 4.89 V module outputs are attached to the ESP32.

## 5. Pre-vehicle electrical checklist

Perform wiring changes with ignition and module power off:

1. Keep the stock LKAS↔EPS wiring continuous through the T-harness.
2. Connect candidate vehicle line A only to the LIN/single-wire input of module A.
3. Connect candidate vehicle line B only to the LIN/single-wire input of module B.
4. Connect module A TX through its divider/buffer to GPIO32.
5. Connect module B TX through its divider/buffer to GPIO33.
6. Connect module grounds and ESP32 GND as a common reference.
7. Leave module RX disconnected from the ESP32 and verify it is held logic high.
8. Verify SLP is logic high; approximately 4.9 V was observed on the tested boards.
9. With the ESP32 disconnected, power the modules and measure both converted TX
   nodes. Each should be approximately 3.2–3.3 V.
10. Power the modules off, connect the divided nodes to GPIO32/GPIO33, power the
    ESP32 from USB, then reapply module power and recheck both GPIO voltages.

Stop immediately if either GPIO exceeds 3.6 V, a fuse opens, a module heats up,
or the vehicle reports a fault.

## 6. Start a capture

Create the capture directory if necessary:

```powershell
New-Item -ItemType Directory -Force captures
```

Create a timestamped filename and start logging:

```powershell
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmm'
py -3 tools\capture_serial.py COM4 "captures\garage_$stamp.jsonl"
```

Replace `COM4` with the current port. The console should print `capturing` and
periodic `frames`, `raw`, `errors` and `bad` counters.

The current host capture script accepts these interactive commands:

```text
!status
!mark ignition_off
!mark ignition_on
!mark engine_started
!mark LKAS_ready
!mark LKAS_enabled
!mark LKAS_disabled
!mark lane_lost
!mark driver_override
!mark brake_pressed
```

Enter short markers at the exact time each event occurs. The current capture
script forwards only `!status` and `!mark ...`; other firmware console commands
are not forwarded by this host tool.

Stop capture cleanly with:

```text
Ctrl+C
```

Wait for `saved ... frames` before disconnecting USB. Each run produces:

- `*.jsonl` — authoritative raw JSONL capture;
- `*.bad.log` — bytes that could not be parsed as JSONL;
- `*.session.json` — host timestamps, clean-shutdown state and final counters.

Never edit the raw `*.jsonl` file in place.

## 7. Analyze a capture offline

Replace the example filename with the actual file created above.

Basic summary:

```powershell
py -3 tools\analyze_log.py captures\garage_2026-08-07_2300.jsonl
```

Analyze one channel:

```powershell
py -3 tools\analyze_log.py captures\garage_2026-08-07_2300.jsonl --channel A
py -3 tools\analyze_log.py captures\garage_2026-08-07_2300.jsonl --channel B
```

Write a plot to PNG:

```powershell
py -3 tools\analyze_log.py captures\garage_2026-08-07_2300.jsonl --plot-output captures\garage_2026-08-07_2300.png
```

Record a SHA-256 hash:

```powershell
Get-FileHash captures\garage_2026-08-07_2300.jsonl -Algorithm SHA256
```

## 8. Interpret the output

- `session` — firmware boot record with GPIOs, baud rate and RX-only mode.
- `stats` — per-channel byte, error and loss counters.
- `frame` — a candidate frame was parsed on channel A or B.
- `raw_fragment` — bytes were retained but auto-detection has not classified
  the channel format.
- `uart_error` — UART hardware event; persistent errors require investigation.
- host `bad` count — a console line was not valid JSONL. Preserve `*.bad.log`.

Auto-detection requires time and enough valid candidate frames. Raw bytes are
more authoritative than provisional decoded fields.

If both `stats` records continue to report `bytes: 0` after the electrical
interface is corrected and bench-tested, do not change live wiring. Scope or
logic-analyze the vehicle line, module TX and divided GPIO node to localize
where transitions disappear.

## 9. Shutdown order

1. Stop the logger with `Ctrl+C` and wait for `saved ... frames`.
2. Turn the ignition off.
3. Remove power from the physical-layer modules.
4. Disconnect the ESP32 USB cable only after logging has stopped.
5. Confirm that the `jsonl`, `bad.log` and `session.json` files exist.

If a dashboard warning, blown fuse, overheating smell or unstable supply
appears, turn the ignition off and disconnect the logger immediately. A lack of
frames is not a reason to move probes or experiment with powered vehicle wiring.
