# Honda Accord CU2 Brake Command Analysis

> Heuristic report. Correlation does not prove that a frame is a safe TX command.

## Input data and verified capture modes

| Intended role | File | Verified dominant mode | Frames | Duration | ACC status | ACC HUD | Set speed | Lead shown | LKAS ready | Dashed | Solid | Steering required | 0x33D DLC |
|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| original mixed capture | `bra.csv` | mixed capture; ACC active part-time | 190395 | 115.35 s | 13.8% | 13.8% | 30–60 km/h | 13.8% | 0.0% | 0.0% | 0.0% | 0.0% | [4] |
| ACC set-speed reduction capture | `bra2.csv` | mixed capture; ACC active part-time | 174177 | 105.52 s | 38.4% | 38.1% | 30–70 km/h | 38.1% | 100.0% | 100.0% | 0.0% | 0.0% | [4] |
| lead-vehicle ACC braking capture | `brk_full.csv` | mixed capture; ACC active part-time | 42419 | 25.70 s | 69.2% | 69.6% | 70–70 km/h | 81.3% | 100.0% | 100.0% | 0.0% | 0.0% | [4] |
| CMBS capture | `cmb.csv` | ACC active; LKAS not actively steering | 39168 | 23.73 s | 74.8% | 75.1% | 60–60 km/h | 87.8% | 100.0% | 100.0% | 0.0% | 0.0% | [4] |
| stationary control | `idle.csv` | stationary; ACC and LKAS off | 95775 | 58.54 s | 0.0% | 0.0% | off | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | [4] |
| regular-driving control | `reg.csv` | regular driving; ACC and LKAS off | 72288 | 44.60 s | 0.0% | 0.0% | off | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | [4] |
| ACC-only control | `acc.csv` | ACC active; LKAS not actively steering | 106391 | 64.72 s | 89.2% | 89.3% | 35–35 km/h | 89.3% | 100.0% | 100.0% | 0.0% | 0.0% | [4] |
| ACC+LKAS control | `lkas.csv` | ACC and LKAS active | 116018 | 70.67 s | 100.0% | 100.0% | 95–95 km/h | 100.0% | 100.0% | 1.1% | 98.9% | 1.1% | [4] |

- `0x1E7`: present.
- Standard Nidec `0x1FA`: absent from every log.

### Capture integrity

| File | CAN IDs | Timestamp wraps | Zero timestamps | Time anomalies | SHA-256 |
|---|---:|---:|---:|---:|---|
| `bra.csv` | 40 | 115 | 26906 | 0 | `ed5ba12a951d…` |
| `bra2.csv` | 40 | 105 | 46040 | 0 | `36deb9b0b684…` |
| `brk_full.csv` | 40 | 26 | 9602 | 0 | `f5c0a5f5866f…` |
| `cmb.csv` | 40 | 23 | 12496 | 0 | `3522ae00c047…` |
| `idle.csv` | 40 | 59 | 49912 | 0 | `6a40e3890a32…` |
| `reg.csv` | 40 | 45 | 36822 | 0 | `4f63dfac89d2…` |
| `acc.csv` | 40 | 64 | 58157 | 134 | `cdf0e5f35ba8…` |
| `lkas.csv` | 40 | 71 | 58291 | 0 | `79c80690b9ad…` |

## Frame frequencies

| ID | bra | bra2 | brk_full | cmb | idle | reg | acc | lkas |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `0x039` | 90.9 Hz | 90.9 Hz | 90.9 Hz | 90.9 Hz | 90.1 Hz | 89.2 Hz | 90.5 Hz | 90.4 Hz |
| `0x097` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz | 99.1 Hz | 98.2 Hz | 99.6 Hz | 99.5 Hz |
| `0x136` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz | 99.1 Hz | 98.2 Hz | 99.6 Hz | 99.5 Hz |
| `0x13A` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz | 99.1 Hz | 98.2 Hz | 99.6 Hz | 99.5 Hz |
| `0x13F` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz | 99.1 Hz | 98.2 Hz | 99.6 Hz | 99.5 Hz |
| `0x156` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz | 99.1 Hz | 98.2 Hz | 99.6 Hz | 99.5 Hz |
| `0x158` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz | 99.1 Hz | 98.2 Hz | 99.6 Hz | 99.5 Hz |
| `0x15A` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz | 99.1 Hz | 98.2 Hz | 99.6 Hz | 99.5 Hz |
| `0x17C` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz | 99.1 Hz | 98.2 Hz | 99.6 Hz | 99.5 Hz |
| `0x188` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz | 99.1 Hz | 98.2 Hz | 99.6 Hz | 99.5 Hz |
| `0x18E` | 100.0 Hz | 100.0 Hz | 100.0 Hz | 100.0 Hz | 99.1 Hz | 98.2 Hz | 99.6 Hz | 99.5 Hz |
| `0x1A4` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz | 49.6 Hz | 49.1 Hz | 49.8 Hz | 49.7 Hz |
| `0x1A6` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz | 49.6 Hz | 49.1 Hz | 49.8 Hz | 49.7 Hz |
| `0x1AA` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz | 49.6 Hz | 49.1 Hz | 49.8 Hz | 49.7 Hz |
| `0x1B0` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz | 49.6 Hz | 49.1 Hz | 49.8 Hz | 49.7 Hz |
| `0x1C0` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz | 49.5 Hz | 49.1 Hz | 49.8 Hz | 49.7 Hz |
| `0x1D0` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz | 49.6 Hz | 49.1 Hz | 49.8 Hz | 49.7 Hz |
| `0x1DC` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz | 49.6 Hz | 49.1 Hz | 49.8 Hz | 49.7 Hz |
| `0x1E7` | 50.0 Hz | 50.0 Hz | 50.0 Hz | 50.0 Hz | 49.6 Hz | 49.1 Hz | 49.8 Hz | 49.7 Hz |
| `0x294` | 25.0 Hz | 25.0 Hz | 25.0 Hz | 25.0 Hz | 24.8 Hz | 24.5 Hz | 24.9 Hz | 24.9 Hz |
| `0x305` | 9.6 Hz | 9.6 Hz | 9.6 Hz | 9.6 Hz | 9.5 Hz | 9.4 Hz | 9.5 Hz | 9.5 Hz |
| `0x309` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz | 9.9 Hz | 9.8 Hz | 10.0 Hz | 10.0 Hz |
| `0x30C` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz | 9.9 Hz | 9.8 Hz | 10.0 Hz | 9.9 Hz |
| `0x320` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz | 9.9 Hz | 9.8 Hz | 10.0 Hz | 9.9 Hz |
| `0x324` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz | 9.9 Hz | 9.8 Hz | 10.0 Hz | 9.9 Hz |
| `0x33D` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz | 9.9 Hz | 9.8 Hz | 9.9 Hz | 9.9 Hz |
| `0x374` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz | 9.9 Hz | 9.8 Hz | 10.0 Hz | 10.0 Hz |
| `0x377` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz | 9.9 Hz | 9.8 Hz | 10.0 Hz | 10.0 Hz |
| `0x378` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz | 9.9 Hz | 9.8 Hz | 9.9 Hz | 10.0 Hz |
| `0x37C` | 10.0 Hz | 10.0 Hz | 10.0 Hz | 10.0 Hz | 9.9 Hz | 9.8 Hz | 10.0 Hz | 9.9 Hz |
| `0x3D7` | 5.0 Hz | 5.0 Hz | 5.0 Hz | 5.0 Hz | 5.0 Hz | 5.0 Hz | 5.0 Hz | 5.0 Hz |
| `0x400` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x405` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x406` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x40C` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x421` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x428` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x454` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x465` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |
| `0x6C1` | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz | 3.3 Hz |

## Observed `0x1A4 COMPUTER_BRAKING` intervals

These are controller-state intervals, not counts of distinct physical braking maneuvers. One real-world maneuver may contain multiple intervals.

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
| `idle.csv` | — | — | — | no intervals | — | — | — |
| `reg.csv` | — | — | — | no intervals | — | — | — |
| `acc.csv` | — | — | — | no intervals | — | — | — |
| `lkas.csv` | — | — | — | no intervals | — | — | — |

## Capture-level candidate ranking

Each CSV contributes at most one consistency vote, regardless of how many marker intervals it contains. The score weights positive-capture consistency (35%), onset alignment (25%), control specificity (25%), and magnitude (15%).

| # | ID / field | Known role | Score | Confidence | Positive captures | Clean negatives | Onset | Release | Control false positives | Payload before → during → after |
|---:|---|---|---:|---|---:|---:|---:|---:|---:|---|
| 1 | `0x1C0` `D3.b0` | unknown | 0.988 | high | 4/4 | 4/4 | -24 ms | +477 ms | 0% | `00 00 00 00 00 00 38 → 04 01 11 00 00 00 22 → 00 00 01 00 00 00 28` |
| 2 | `0x1DC` `D3.b2` | unknown | 0.822 | hypothesis | 3/4 | 0/4 | -38 ms | +53 ms | 28% | `02 09 60 1C → 02 06 8E 00 → 02 04 8F 01` |
| 3 | `0x13F` `D2` | unknown | 0.819 | hypothesis | 4/4 | 0/4 | -240 ms | +6 ms | 31% | `03 06 03 05 00 28 00 28 → 00 85 00 8A FF 4C 00 08 → 01 26 01 3C 00 32 00 07` |
| 4 | `0x136` `D5.b1` | unknown | 0.727 | hypothesis | 4/4 | 1/4 | -492 ms | +386 ms | 11% | `00 00 00 31 22 00 00 24 → 00 00 00 0C 00 00 00 02 → 00 00 00 0D 02 00 00 0F` |
| 5 | `0x324` `D6.b2` | unknown | 0.716 | hypothesis | 3/4 | 1/4 | -98 ms | +298 ms | 24% | `7B 4D 14 9B 32 FF 00 00 → 7B 4D 14 9F 1E F8 00 36 → 7B 4E 14 A3 1E F8 00 03` |
| 6 | `0x37C` `D1` | unknown | 0.714 | hypothesis | 2/4 | 1/4 | -27 ms | — | 10% | `DD 00 E3 33 00 01 00 1F → 08 00 08 33 00 01 00 0B → 08 00 08 34 00 02 00 36` |
| 7 | `0x40C` `D5.b3` | unknown | 0.713 | medium | 3/4 | 4/4 | -97 ms | +89 ms | 7% | `78 00 00 2B 56 05 3E 1A → 7A 00 00 FF FF 80 00 30 → 4D 00 7F FD 26 80 00 23` |
| 8 | `0x097` `D5.b0` | unknown | 0.669 | hypothesis | 2/4 | 1/4 | -38 ms | +2 ms | 18% | `80 60 10 02 03 00 00 04 → 7F E0 00 02 00 00 00 20 → 80 A0 30 01 F5 00 00 2C` |
| 9 | `0x13A` `D3` | unknown | 0.666 | medium | 2/4 | 3/4 | -127 ms | +8 ms | 1% | `00 00 80 00 00 00 00 11 → 00 00 00 00 00 00 00 37 → 00 00 00 00 00 00 00 19` |
| 10 | `0x309` `D2` | unknown | 0.657 | hypothesis | 3/4 | 1/4 | -219 ms | +68 ms | 42% | `16 AF 00 00 00 3A 00 69 → 17 44 00 00 00 3B 00 59 → 0B AC 00 00 00 1D 00 49` |
| 11 | `0x15A` `D4` | unknown | 0.655 | medium | 2/4 | 3/4 | -51 ms | +309 ms | 13% | `00 00 02 1C 00 00 00 09 → 00 00 00 CA 00 00 00 20 → FF A1 FF 36 00 00 00 26` |
| 12 | `0x158` `D2.b2` | ENGINE_DATA / vehicle speed | 0.654 | hypothesis | 4/4 | 1/4 | -19 ms | +8 ms | 21% | `15 98 06 25 15 98 61 35 → 16 2B 06 4F 16 2B 62 10 → 0B 1E 04 6F 0B 1E 69 1D` |
| 13 | `0x18E` `D2.b2` | unknown | 0.649 | hypothesis | 2/4 | 1/4 | -18 ms | +14 ms | 27% | `00 06 29 → 00 01 00 → 00 05 2A` |
| 14 | `0x1A6` `D5.b3` | unknown | 0.639 | hypothesis | 2/4 | 1/4 | -82 ms | +34 ms | 16% | `62 00 00 47 67 80 00 3C → 02 00 00 43 63 80 00 2B → 02 00 40 54 57 80 00 22` |
| 15 | `0x156` `D4.b0` | unknown | 0.629 | hypothesis | 2/4 | 2/4 | -31 ms | +46 ms | 10% | `00 14 00 01 07 0F → 00 14 00 01 07 3C → 00 0E 00 07 07 3D` |
| 16 | `0x30C` `D2.b6` | ACC_HUD / ACC context | 0.600 | hypothesis | 4/4 | 1/4 | -132 ms | +112 ms | 18% | `16 3A C6 FF 01 90 91 01 → 00 00 C6 23 01 90 91 3B → 0B CE C6 1E 01 90 90 2E` |
| 17 | `0x1D0` `D6` | WHEEL_SPEEDS / vehicle response | 0.586 | hypothesis | 4/4 | 1/4 | -94 ms | +305 ms | 47% | `2C 00 58 08 B0 39 5E C1 → 2D 2A 5A 64 B5 41 6B 1F → 16 8E 2D 20 5A 78 B4 96` |
| 18 | `0x377` `D1.b5` | unknown | 0.582 | hypothesis | 2/4 | 3/4 | -285 ms | +92 ms | 4% | `20 06 31 74 89 00 72 33 → 18 06 31 74 8A 00 72 2C → 10 06 33 74 8A 00 72 13` |
| 19 | `0x17C` `D4.b5` | POWERTRAIN_DATA / ACC and pedal state | 0.556 | hypothesis | 3/4 | 0/4 | -51 ms | +14 ms | 13% | `00 00 09 60 48 00 00 27 → 00 00 06 8E 48 00 00 0C → 00 00 04 8F 48 00 00 0D` |
| 20 | `0x3D7` `D1:D2` | unknown | 0.450 | hypothesis | 1/4 | 4/4 | -303 ms | +178 ms | 25% | `B0 C1 04 00 00 00 00 05 → B0 C1 04 00 00 00 00 05 → B0 00 00 00 00 00 00 7F` |

## Focused evidence: `0x1C0 D3.b0`

| Positive capture | Marker intervals | Matching intervals | Median onset | Median release | Candidate active runs |
|---|---:|---:|---:|---:|---|
| `bra.csv` | 1 | 1 | -22 ms | +478 ms | 65.734–72.334 s |
| `bra2.csv` | 3 | 3 | -26 ms | +475 ms | 36.188–42.189 s, 70.389–76.229 s, 88.489–92.709 s |
| `brk_full.csv` | 2 | 2 | -29 ms | +471 ms | 3.453–7.673 s, 12.233–20.054 s |
| `cmb.csv` | 2 | 2 | -16 ms | +484 ms | 8.104–12.703 s, 16.104–20.023 s |

| Negative capture | Candidate active fraction | COMPUTER_BRAKING active fraction |
|---|---:|---:|
| `idle.csv` | 0.00% | 0.00% |
| `reg.csv` | 0.00% | 0.00% |
| `acc.csv` | 0.00% | 0.00% |
| `lkas.csv` | 0.00% | 0.00% |

## CMBS-specific changes

These fields may represent AEB/CMBS status rather than a pressure command.

| ID / field | CMBS-only | Score | Positive captures | Control false positives |
|---|---:|---:|---:|---:|
| `0x13A` `D3` | 0.660 | 0.666 | 2/4 | 1% |
| `0x156` `D4.b0` | 0.599 | 0.629 | 2/4 | 10% |
| `0x097` `D5.b0` | 0.547 | 0.669 | 2/4 | 18% |
| `0x18E` `D2.b2` | 0.486 | 0.649 | 2/4 | 27% |
| `0x40C` `D5.b3` | 0.309 | 0.713 | 3/4 | 7% |
| `0x324` `D6.b2` | 0.255 | 0.716 | 3/4 | 24% |
| `0x1DC` `D3.b2` | 0.241 | 0.822 | 3/4 | 28% |
| `0x309` `D2` | 0.192 | 0.657 | 3/4 | 42% |
| `0x1C0` `D3.b0` | 0.000 | 0.988 | 4/4 | 0% |
| `0x13F` `D2` | 0.000 | 0.819 | 4/4 | 31% |

## Conclusion

The highest-ranked unknown frame is `0x1C0` (`D3.b0`, score 0.988, confidence: **high**). It is a candidate for further decoding, not a confirmed command.

Physical maneuver count is intentionally left unknown. Confirmation still requires separate annotated captures with repeatable onset timing; do not transmit candidate frames on public roads.

## Method and limitations

- Off-marker control windows are sampled from all eight captures, including captures that also contain marker intervals.
- Counter and checksum bits in the lower six bits of the last byte are ignored for ranking.
- `0x1A4`, `0x1E7`, `0x158`, `0x1D0`, `0x17C`, and `0x30C` are tagged as known status/response frames.
- CU2 emits `0x33D` with DLC 4. Signal positions in the first four bytes match upstream [`LKAS_HUD`](https://github.com/commaai/opendbc/blob/master/opendbc/dbc/generator/honda/_lkas_hud_5byte.dbc), which defines a five-byte message.
- Zero timestamps are interpolated and the microsecond field is unwrapped once per second.
- The analysis does not create TX frames or modify openpilot or panda safety code.
