# CU2 connector pinout research

This directory contains machine-readable transcriptions of connector
measurements used by the project documentation.

- [`cu2_connector_measurements.csv`](cu2_connector_measurements.csv) transcribes
  the uploaded `pinout.xlsx` worksheet.
- [`docs/CONNECTOR_PINOUTS.md`](../../docs/CONNECTOR_PINOUTS.md) is the
  confidence-qualified human-readable interpretation.
- [`docs/assets/connectors/acc-adas-20pin-numbering-reference.png`](../../docs/assets/connectors/acc-adas-20pin-numbering-reference.png)
  and [`docs/assets/connectors/lkas-camera-10pin-numbering-reference.png`](../../docs/assets/connectors/lkas-camera-10pin-numbering-reference.png)
  preserve the connector-numbering drawings from the worksheet. They are
  numbering references only; mating-face versus wire-side orientation remains
  to be confirmed against the physical connectors.

The CSV preserves the original working labels but does not validate them.
Connector orientation, measurement state and waveform captures remain required
before using the pinout for hardware design.
