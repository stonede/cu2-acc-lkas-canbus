# Honda Accord CU2 tooling

One repository for experiments and tools around the Honda Accord CU2,
openpilot, CAN and the stock serial steering interface.

## Repository layout

```text
firmware/
  serial-steering/  ESP32 receive-only LKAS↔EPS serial logger
research/
  can/              CAN captures, DBC and brake-command analysis
```

Each directory is self-contained and has its own README, commands and data.
Add a new top-level area only when the code has a different purpose; extend an
existing area when it uses the same hardware, build or dataset.

For future additions, keep device code in `firmware/<device>/`, measurements
and reverse engineering in `research/<topic>/`, and openpilot-specific code in
`integrations/openpilot/`. Do not create those directories until they contain
working code.

## Current projects

- [Serial steering logger](firmware/serial-steering/README.md)
- [CAN research](research/can/README.md)

Safety notes and signal interpretations live with the relevant project. None
of the research in this repository establishes that a candidate frame is safe
to transmit on public roads.
