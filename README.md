# cu2-acc-lkas-canbus

Automated analysis of Honda Accord CU2 CAN logs to identify a possible
non-standard ACC/CMBS brake command.

```powershell
py -3 analyze_can.py
```

The default inputs are:

- `bra.csv` — normal driving with ACC/LKAS,
- `bra2.csv` — braking after reducing the ACC set speed,
- `brk_full.csv` — ACC braking behind a lead vehicle,
- `cmb.csv` — braking during a CMBS activation.

The result is written to `analysis_report.md`. Override the input or output paths
with `--baseline`, `--set-speed`, `--acc-brake`, `--cmbs`, and `--output`.
Run the built-in parser and ranking check with `py -3 analyze_can.py --self-test`.

The report identifies candidates for further reverse engineering. It does not
establish that any frame is safe to transmit and must not be used as the basis
for transmitting candidate frames on public roads.
