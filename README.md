# Honda Accord CU2 tooling

One repository for experiments, evidence and tools around the Honda Accord CU2, comma.ai/openpilot, CAN and the stock serial steering interface.

## Start here

The project-wide source of truth is the [CU2 openpilot knowledge base](docs/README.md). It records the current vehicle architecture, confirmed findings, hypotheses, hardware, safety boundaries and staged integration plan.

## Repository layout

```text
docs/                       Project-wide knowledge base and roadmap
firmware/
  serial-steering/           ESP32 receive-only LKAS↔EPS serial logger
research/
  can/                       CAN captures, DBC and brake-command analysis
  pinouts/                   Machine-readable connector measurements
```

Each implementation directory is self-contained and has its own README, commands and data. Project-wide conclusions belong in `docs/`; implementation details stay beside the relevant code.

For future additions, keep device code in `firmware/<device>/`, measurements and reverse engineering in `research/<topic>/`, and openpilot-specific code in `integrations/openpilot/`. Do not create an integration directory until it contains working code.

## Current projects

- [Project knowledge base](docs/README.md)
- [Serial steering logger](firmware/serial-steering/README.md)
- [CAN research](research/can/README.md)
- [Connector pinout research](research/pinouts/README.md)

## Safety

This repository currently supports passive logging and reverse engineering. None of the research establishes that a candidate frame is safe to transmit. Active steering or braking work requires independent electrical fail-safes, protocol validation, safety-model enforcement and controlled testing.
