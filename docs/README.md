# Honda Accord CU2 openpilot knowledge base

This directory is the project-level source of truth for the planned comma.ai/openpilot integration with the European/Japanese-market Honda Accord VIII CU2.

Detailed tooling remains next to the code and data that produce it:

- CAN captures, DBC and analysis: [`research/can/`](../research/can/README.md)
- Passive serial-steering logger: [`firmware/serial-steering/`](../firmware/serial-steering/README.md)

## Documentation map

| Document | Purpose |
|---|---|
| [Project status](PROJECT_STATUS.md) | Current state, completed work, unresolved questions and next milestones |
| [Vehicle architecture](VEHICLE_ARCHITECTURE.md) | CU2 ADAS modules, buses and observed communication paths |
| [Hardware and capture](HARDWARE_AND_CAPTURE.md) | T-harnesses, CANable, ESP32, physical-layer modules and safe logging procedure |
| [Connector pinouts](CONNECTOR_PINOUTS.md) | Reverse-engineered connector cavities, wire colours, voltage snapshots and confidence-qualified functions |
| [CAN research summary](CAN_RESEARCH_SUMMARY.md) | Dataset, known messages, brake-command analysis and limitations |
| [Serial steering research](SERIAL_STEERING_RESEARCH.md) | LKAS↔EPS single-wire protocol assumptions and logger status |
| [Openpilot integration plan](OPENPILOT_INTEGRATION_PLAN.md) | Staged route from passive logging to a safety-reviewed integration |
| [Evidence ledger](EVIDENCE_LEDGER.md) | Claim-by-claim confidence, source and required follow-up |

## Evidence labels

- **Confirmed** — directly measured on this specific 2013 CU2, reproduced in supplied captures, or established by continuity/pin measurements.
- **Observed** — seen in one or more captures or vehicle tests, but not yet reproduced enough to treat as a protocol invariant.
- **Inferred** — best current interpretation of measurements, correlations or related Honda implementations.
- **Community report** — supplied by another reverse engineer and not yet independently reproduced in this car.
- **Open** — unknown or actively disputed.

Raw captures and measurements outrank decoded names. A signal name copied from another Honda platform is not automatically confirmed for the CU2.

## Canonical artifacts

- [`research/can/data/`](../research/can/data/) — original CAN captures; preserve them unchanged.
- [`research/can/analyze_can.py`](../research/can/analyze_can.py) — reproducible CAN analysis.
- [`research/can/analysis_report.md`](../research/can/analysis_report.md) — generated results for the current dataset.
- [`research/can/2013_CU_honda_accord.dbc`](../research/can/2013_CU_honda_accord.dbc) — current definitions and confidence comments.
- [`firmware/serial-steering/`](../firmware/serial-steering/) — receive-only ESP32 logger and host-side tools.
- [`research/pinouts/cu2_connector_measurements.csv`](../research/pinouts/cu2_connector_measurements.csv) — machine-readable transcription of current connector measurements.

## Scope and safety boundary

This repository currently supports reverse engineering and passive data collection. It does **not** establish that any candidate steering or braking message is safe to transmit.

Before active control is attempted, the project must separately demonstrate deterministic protocol understanding, electrical fail-safe behaviour, watchdog/pass-through behaviour, correct timing/counters/checksums, panda safety coverage, and controlled bench and closed-course validation.

No result in this repository should be treated as permission to inject unverified frames on public roads.

## Maintenance rules

- Put project-wide conclusions in `docs/` and implementation details beside relevant code.
- Add a date and evidence source when promoting a statement from inferred to confirmed.
- Keep hypotheses explicit.
- Preserve original captures; derived files should be reproducible from scripts.
- Record failed experiments and disproved assumptions.
- Create `integrations/openpilot/` only when working integration code exists.
