# Honda Accord CU2 Brake Command Analysis

> Heuristic report. Correlation does not prove that a frame is a safe TX command.

## Input data

| Role | File | Frames | Duration | IDs | Zero timestamps | Wraps | Anomalies | SHA-256 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| normal ACC/LKAS driving | `bra.csv` | 190395 | 115.35 s | 40 | 26906 | 115 | 0 | `ed5ba12a951d` |
| braking after reducing the ACC set speed | `bra2.csv` | 174177 | 105.52 s | 40 | 46040 | 105 | 0 | `36deb9b0b684` |
| ACC braking behind a lead vehicle | `brk_full.csv` | 42419 | 25.70 s | 40 | 9602 | 26 | 0 | `f5c0a5f5866f` |
| braking with CMBS activation | `cmb.csv` | 39168 | 23.73 s | 40 | 12496 | 23 | 0 | `3522ae00c047` |

- `0x1E7`: present.
- Standard Nidec `0x1FA`: absent from every log.

## Frame frequencies

| ID | bra | bra2 | brk_full | cmb |
|---:|---:|---:|---:|---:|
| `0x039` | 90.9 Hz | 90.9 Hz | 90.9 Hz | 90.9 Hz |
| `0x097` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz |
| `0x136` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz |
| `0x13A` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz |
| `0x13F` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz |
| `0x156` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz |
| `0x158` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz |
| `0x15A` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz |
| `0x17C` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz |
| `0x188` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz |
| `0x18E` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz |
| `0x1A4` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz |
| `0x1A6` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz |
| `0x1AA` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz |
| `0x1B0` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz |
| `0x1C0` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz |
| `0x1D0` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz |
| `0x1DC` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz |
| `0x1E7` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz |
| `0x294` | 25.0 Hz | 25.0 Hz | 25.0 Hz | 25.0 Hz |
| `0x305` | 9.6 Hz | 9.6 Hz | 9.6 Hz | 9.6 Hz |
| `0x309` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz |
| `0x30C` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz |
| `0x320` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz |
| `0x324` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz |
| `0x33D` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz |
| `0x374` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz |
| `0x377` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz |
| `0x378` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz |
| `0x37C` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz |
| `0x3D7` | 5.0 Hz | 5.0 Hz | 5.0 Hz | 5.0 Hz |
| `0x400` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x405` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x406` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x40C` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x421` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x428` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x454` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x465` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x6C1` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |

## Detected `0x1A4 COMPUTER_BRAKING` intervals

| Log | # | Start | End | Duration | Speed before → after | 0x1E7 raw before → max | 0x17C / 0x30C context |
|---|---:|---:|---:|---:|---|---|---|
| `bra.csv` | 1 | 65.756 s | 71.875 s | 6.12 s | 55.6 → 28.5 km/h | 104 → 154 | ACC=1, brake pedal=0, set=40 km/h, lead=1 |
| `bra2.csv` | 1 | 36.214 s | 41.735 s | 5.52 s | 56.1 → 28.9 km/h | 104 → 155 | ACC=1, brake pedal=0, set=40 km/h, lead=2 |
| `bra2.csv` | 2 | 70.415 s | 75.774 s | 5.36 s | 67.4 → 32.6 km/h | 104 → 181 | ACC=1, brake pedal=0, set=60 km/h, lead=1 |
| `bra2.csv` | 3 | 88.513 s | 92.253 s | 3.74 s | 46.0 → 29.1 km/h | 104 → 157 | ACC=1, brake pedal=0, set=30 km/h, lead=1 |
| `brk_full.csv` | 1 | 3.482 s | 7.223 s | 3.74 s | 58.7 → 46.9 km/h | 104 → 143 | ACC=1, brake pedal=0, set=70 km/h, lead=2 |
| `brk_full.csv` | 2 | 12.262 s | 19.603 s | 7.34 s | 45.2 → 15.1 km/h | 104 → 163 | ACC=1, brake pedal=0, set=70 km/h, lead=2 |
| `cmb.csv` | 1 | 8.120 s | 12.241 s | 4.12 s | 46.0 → 32.1 km/h | 104 → 142 | ACC=1, brake pedal=0, set=60 km/h, lead=2 |
| `cmb.csv` | 2 | 16.120 s | 19.560 s | 3.44 s | 30.1 → 13.5 km/h | 104 → 182 | ACC=1, brake pedal=0, set=60 km/h, lead=2 |

## Candidate ranking

The score is relative: it rewards changes before the marker, agreement between `brk_full` and `cmb`, confirmation in `bra2`, and the absence of similar changes in control windows from `bra`.

| # | ID / field | Known role | Score | Confidence | brk | cmb | bra2 | Control false positives | Lead | Payload before → during → after |
|---:|---|---|---:|---|---:|---:|---:|---:|---:|---|
| 1 | `0x1C0` `D3.b0` | unknown | 1.000 | high | 100% | 100% | 100% | 0% | -22 ms | `00 00 10 00 00 00 28 → 03 01 11 00 00 00 14 → 00 00 11 00 00 00 27` |
| 2 | `0x1DC` `D3` | unknown | 0.928 | high | 100% | 100% | 100% | 23% | -491 ms | `02 06 93 19 → 02 06 7A 05 → 02 05 39 1A` |
| 3 | `0x13F` `D4` | unknown | 0.898 | high | 100% | 100% | 67% | 34% | -491 ms | `FF 84 00 8B 00 00 00 35 → FF 85 00 91 FF C4 00 11 → FF 8F 00 D7 00 00 00 39` |
| 4 | `0x324` `D6.b2` | unknown | 0.873 | high | 100% | 50% | 67% | 3% | -470 ms | `7C 46 23 7F 46 E7 00 26 → 7C 46 23 7F 46 09 00 13 → 7C 46 23 7F 46 09 00 13` |
| 5 | `0x097` `D5` | unknown | 0.840 | high | 50% | 100% | 33% | 3% | -495 ms | `80 60 20 02 0D 00 00 09 → 80 60 20 02 00 00 00 24 → 7F 9F E0 02 04 00 00 06` |
| 6 | `0x309` `D2` | unknown | 0.819 | high | 50% | 100% | 100% | 20% | -475 ms | `12 AE 00 00 00 2F 00 6A → 12 7F 00 00 00 2F 00 5D → 06 38 00 00 00 0F 00 57` |
| 7 | `0x18E` `D2.b2` | unknown | 0.800 | high | 50% | 100% | 33% | 23% | -488 ms | `00 06 29 → 00 01 00 → 00 05 2A` |
| 8 | `0x136` `D5.b1` | unknown | 0.786 | high | 50% | 50% | 67% | 3% | -492 ms | `10 00 00 0F 01 00 00 1C → 00 00 00 0C 00 00 00 3F → 00 00 00 0C 00 00 00 11` |
| 9 | `0x37C` `D1.b3` | unknown | 0.786 | high | 50% | 50% | 67% | 3% | -475 ms | `E3 00 E4 34 00 01 00 25 → D9 00 DA 34 00 01 00 1C → D9 00 DA 34 00 02 00 0C` |
| 10 | `0x40C` `D5` | unknown | 0.772 | high | 50% | 100% | 33% | 37% | -369 ms | `55 00 00 2B 13 92 41 2B → 57 00 00 80 FF 32 18 08 → 64 0A 11 06 06 01 00 14` |
| 11 | `0x13A` `D3` | unknown | 0.719 | medium | 50% | 50% | 0% | 3% | -127 ms | `00 00 80 00 00 00 00 11 → 00 00 00 00 00 00 00 37 → 00 00 00 00 00 00 00 19` |
| 12 | `0x15A` `D4.b0` | unknown | 0.719 | medium | 50% | 50% | 0% | 3% | -395 ms | `00 00 FF 79 00 00 00 28 → 00 00 FF 79 00 00 00 37 → 00 00 FF BD 00 00 00 20` |
| 13 | `0x1A6` `D4.b2` | unknown | 0.718 | hypothesis | 100% | 0% | 33% | 20% | -488 ms | `02 00 00 4A 71 80 00 25 → 02 00 00 4A 6C 80 00 1C → 02 00 40 46 63 80 00 24` |
| 14 | `0x377` `D1` | unknown | 0.686 | hypothesis | 100% | 0% | 100% | 14% | -178 ms | `0C 06 7B 74 AF 00 A2 21 → 08 06 7B 74 AF 00 A2 16 → 04 06 7D 74 B0 00 A2 16` |
| 15 | `0x156` `D4.b0` | unknown | 0.681 | hypothesis | 0% | 50% | 67% | 11% | -287 ms | `FF FE 00 00 07 28 → FF FE 00 01 07 09 → FF FE 00 01 07 09` |
| 16 | `0x30C` `D2.b4` | ACC_HUD / ACC context | 0.680 | medium | 100% | 100% | 100% | 14% | -377 ms | `17 B1 16 46 01 60 90 13 → 00 00 16 46 01 60 90 08 → 12 C0 16 46 01 60 90 36` |
| 17 | `0x1D0` `D6` | WHEEL_SPEEDS / vehicle response | 0.657 | medium | 100% | 100% | 67% | 14% | -498 ms | `2F 2C 5E 9C BC 89 76 2C → 2E 50 5C 60 BA 09 72 61 → 25 4A 49 B4 94 79 2C 1D` |
| 18 | `0x17C` `D4` | POWERTRAIN_DATA / ACC and pedal state | 0.649 | medium | 100% | 100% | 100% | 23% | -491 ms | `00 00 06 93 48 00 00 33 → 00 00 06 74 48 00 00 16 → 00 00 05 39 48 00 00 34` |
| 19 | `0x158` `D2.b2` | ENGINE_DATA / vehicle speed | 0.599 | medium | 50% | 100% | 67% | 11% | -473 ms | `11 BF 05 0E 11 BF A8 3A → 11 A4 05 05 11 A4 A9 1C → 05 E6 02 5B 05 E6 B0 0B` |
| 20 | `0x1B0` `D2.b6` | unknown | 0.551 | hypothesis | 50% | 0% | 0% | 6% | -499 ms | `80 10 7F FF 00 00 0F → 80 10 7F FF 00 00 3C → 7F D0 7F FF 00 00 05` |

## CMBS-specific changes

These fields may represent AEB/CMBS status rather than a pressure command.

| ID / pole | CMBS-only | cmb | brk_full | Kontrola |
|---|---:|---:|---:|---:|
| `0x097` `D5` | 0.486 | 100% | 50% | 3% |
| `0x156` `D4.b0` | 0.443 | 50% | 0% | 11% |
| `0x158` `D2.b2` | 0.443 | 100% | 50% | 11% |
| `0x309` `D2` | 0.400 | 100% | 50% | 20% |
| `0x18E` `D2.b2` | 0.386 | 100% | 50% | 23% |
| `0x40C` `D5` | 0.314 | 100% | 50% | 37% |
| `0x136` `D5.b1` | 0.243 | 50% | 50% | 3% |
| `0x37C` `D1.b3` | 0.243 | 50% | 50% | 3% |
| `0x13A` `D3` | 0.243 | 50% | 50% | 3% |
| `0x15A` `D4.b0` | 0.243 | 50% | 50% | 3% |

## Conclusion

The highest-ranked unknown frame is `0x1C0` (`D3.b0`, score 1.000, confidence: **high**). It is a candidate for further decoding, not a confirmed command.

The next capture should contain separate, annotated trials: steady ACC without braking, one ACC set-speed reduction, one lead-vehicle braking event, and one separate CMBS event. Confirmation requires the same field to repeat with similar lead time; do not transmit candidate frames on public roads.

## Method and limitations

- Counter and checksum bits in the lower six bits of the last byte are ignored for ranking.
- `0x1A4`, `0x1E7`, `0x158`, `0x1D0`, `0x17C`, and `0x30C` are tagged as known status/response frames.
- Zero timestamps are interpolated and the microsecond field is unwrapped once per second.
- The analysis does not create TX frames or modify openpilot or panda safety code.
