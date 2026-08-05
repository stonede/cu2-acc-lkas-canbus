# Openpilot integration plan

## Principle

Progress from observation to control in explicit stages. Passing one stage does not imply the next is safe.

## Stage 0 — repository and evidence discipline

- Preserve raw logs and hashes.
- Keep confirmed facts separate from inherited Honda assumptions.
- Make analyses reproducible.
- Maintain this documentation and the evidence ledger.

**Exit condition:** another engineer can reproduce the current CAN conclusions from the repository alone.

## Stage 1 — passive vehicle fingerprinting

- Complete CAN message inventory and DBC refinement.
- Record firmware/part-number variants where possible.
- Confirm connector pinouts and electrical levels.
- Capture both serial steering channels synchronized with CAN.

**Exit condition:** stock lateral and longitudinal data paths are described without active transmission.

## Stage 2 — serial protocol characterization

- Confirm frame directions, lengths, checksum and timing.
- Decode steering command, EPS feedback, driver override and fault fields.
- Establish startup and timeout behaviour.
- Reproduce parser results across multiple drives.

**Exit condition:** captured frames can be decoded deterministically with low unexplained residue.

## Stage 3 — bench gateway prototype

- Build hardware with transparent fail-safe pass-through.
- Add isolation/protection, watchdog and brownout-safe behaviour.
- Test loss of MCU power, reset loops, stuck GPIO, malformed frames and disconnected host.
- Do not connect active output to a moving vehicle.

**Exit condition:** every tested failure returns control to stock or a defined non-driving safe state.

## Stage 4 — openpilot vehicle model, passive only

Create `integrations/openpilot/` when working code exists. Expected work includes:

- vehicle fingerprint and firmware matching;
- `CarState` mappings using the CU2 DBC;
- ACC/LKAS HUD and button interpretation;
- steering and longitudinal interface abstractions;
- unit tests using captured routes;
- opendbc changes with confidence notes.

Run in dashcam/passive mode first.

**Exit condition:** openpilot state matches the stock cluster and measured vehicle behaviour without transmitting control commands.

## Stage 5 — lateral control on bench/closed course

- Generate serial steering commands only after the stock command format is confirmed.
- Enforce torque/angle/rate limits and driver override.
- Implement heartbeat and immediate stock fallback.
- Add panda-side or equivalent independent safety enforcement where architecture permits.

Because OEM LKAS has a high activation threshold near motorway speeds, early tests must not rely on public-road activation conditions.

**Exit condition:** repeatable low-risk closed-course steering with tested fallback and no unresolved EPS faults.

## Stage 6 — longitudinal control

- Confirm `0x1C0` ownership and exact semantics.
- Determine gas command, brake command, ACC/VSA coordination and HUD requirements.
- Implement strict checksum, counter, rate and state gating.
- Validate cancel/brake-pedal/driver override and stock-system conflict handling.

**Exit condition:** controlled deceleration and release behave predictably under injected faults and driver takeover.

## Stage 7 — upstream-quality integration

- Add complete tests and documentation.
- Document supported trims, model years and part-number constraints.
- Submit opendbc/openpilot changes as reviewable, separated commits.
- Treat compatibility outside the tested CU2 configuration as unsupported until measured.

## Lateral-only versus longitudinal

A lateral-only first milestone may reduce scope, but it still requires custom serial hardware and rigorous fail-safe behaviour. Longitudinal data appears more conventional at the CAN level, yet the non-standard `0x1C0` brake path creates its own safety and reverse-engineering burden.

The decision should be based on which subsystem reaches deterministic understanding first, not on perceived software simplicity.
