# CU2 CAN research

CAN captures, a DBC and an analyzer for a possible non-standard ACC/CMBS brake
command in the Honda Accord CU2.

From the repository root:

```powershell
py -3 research/can/analyze_can.py --self-test
py -3 research/can/analyze_can.py
```

The analyzer reads the eight captures in `data/` and writes
`analysis_report.md`. Override paths with `--baseline`, `--set-speed`,
`--acc-brake`, `--cmbs`, `--idle`, `--regular`, `--acc`, `--lkas` and
`--output`.

`2013_CU_honda_accord.dbc` covers every ID in the supplied captures. Its
comments distinguish CU2-confirmed, related-Accord, inherited-Nidec and
unresolved evidence.

The report identifies candidates for further reverse engineering. It does not
establish that any frame is safe to transmit and must not be used as the basis
for transmitting candidate frames on public roads.
