# CAN research summary

## Dataset

The current analysis uses eight captures:

| File | Scenario |
|---|---|
| `idle.csv` | stationary, ACC/LKAS off |
| `reg.csv` | regular driving, ACC/LKAS off |
| `acc.csv` | ACC active, no active LKAS steering |
| `lkas.csv` | ACC and LKAS active |
| `bra.csv` | mixed capture containing ACC braking |
| `bra2.csv` | ACC braking after set-speed reductions |
| `brk_full.csv` | ACC braking behind a lead vehicle |
| `cmb.csv` | CMBS/AEB activation context |

The generated report verifies the dominant operating mode from CAN content rather than trusting file names alone.

## Bus inventory

- 40 CAN identifiers appear in each supplied capture.
- Common observed rates include approximately 100, 50, 25, 10, 5 and 3.3 Hz.
- `0x1E7` is present and tracks brake pressure/response context.
- Standard Honda Nidec `0x1FA` is absent from every log.
- CU2 emits `0x33D` with DLC 4; its first four bytes align with known Honda LKAS HUD layouts that are often represented as five-byte messages elsewhere.

See [`research/can/analysis_report.md`](../research/can/analysis_report.md) for full frequencies and capture integrity data.

## Brake-command candidate

`0x1C0` is the strongest current candidate for an alternative CU2 `BRAKE_COMMAND`.

Current provisional structure:

```text
command       = (D1 << 2) | (D2 >> 6)
pump_request  = D2.b0
brake_request = D3.b0
state_flags   = D3 & 0xFE
counter       = D7[5:4]
checksum      = D7[3:0]
```

Observed evidence:

- seven-byte DLC;
- 50 Hz transmission;
- command is zero in all four negative-control captures;
- command is active in all four positive braking captures;
- Honda checksum validation passes 100% of frames in the supplied dataset;
- counter continuity is approximately 99.9–100%, with discontinuities consistent with dropped capture frames;
- D4–D6 are zero in the current data;
- magnitude closely follows measured braking response;
- combined cross-correlation with `0x1E7` peaks around +120 ms with Pearson `r = 0.986`;
- maximum command versus maximum pressure rise across identified intervals has Pearson correlation `0.991`.

This is strong evidence of function, not proof of a safe transmit format.

## Important context messages

The current DBC/report uses or references:

- `0x17C` — powertrain, ACC and brake-pedal context;
- `0x1A4` — `COMPUTER_BRAKING` controller state used to identify intervals;
- `0x1E7` — brake pressure/response;
- `0x158` — engine/vehicle-speed context;
- `0x1D0` — wheel-speed/vehicle response;
- `0x30C` — ACC HUD/context;
- `0x33D` — LKAS HUD, CU2 DLC 4.

Names inherited from other Honda DBCs remain confidence-qualified in the CU2 DBC.

## What is not yet proven

- Exact engineering units and saturation for `0x1C0.command`.
- Exact meaning of `D2.b0`, `D3.b0` and remaining D3 state flags.
- Node that owns `0x1C0` under all operating modes.
- Required relationship with VSA, PCM and ACC watchdog messages.
- Behaviour when frames are missing, delayed, duplicated or counter-invalid.
- Whether openpilot can safely replace, suppress or coexist with the stock sender.
- Minimum and maximum controllable deceleration.

## Required follow-up captures

Use separate, annotated runs for:

- repeated small ACC decelerations;
- repeated large ACC decelerations;
- set-speed changes without a lead vehicle;
- lead-vehicle following at multiple gaps;
- CMBS warning without braking, if safely reproducible;
- manual brake pedal only;
- module unplug/fault tests on a bench or controlled setup.

Do not combine unrelated manoeuvres when a clean single-purpose capture is possible.
