# Evidence ledger

Last consolidated: 2026-08-08.

| Claim | Status | Evidence | Required follow-up |
|---|---|---|---|
| Tested facelift CU2 uses one shared observed F-CAN for ACC/LKAS/PCM/VSA/HUD traffic | Confirmed | Continuity/probing and all supplied CAN captures | Repeat at camera and ACC connector with documented pin numbers |
| A separate second ACC CAN exists at the tested ACC unit | Disproved/currently unsupported | No second CAN pair found; observed functions present on shared bus | Revisit only if a new pin/physical measurement contradicts this |
| Standard Nidec brake command `0x1FA` is used | Disproved for current captures | Absent from all eight logs | Check other CU2 years/firmware separately |
| `0x1C0` carries braking magnitude | Strong inference | Positive/negative capture separation, checksum/counter, pressure correlation | Annotated repeated manoeuvres and controlled TX validation |
| `0x1C0 D2.b0` is pump request | Inferred | Position matches Nidec structure and onset correlation | Observe pump/VSA state independently |
| `0x1C0 D3.b0` is brake request/hold | Inferred | Position and activation timing | Fault-state and release testing |
| `0x1E7` represents brake pressure/response | Strongly observed | Baseline/rise pattern during computer braking | Compare with diagnostic pressure PID or pressure sensor |
| CU2 `0x33D` uses DLC 4 | Confirmed | All supplied captures | Test additional vehicles/firmware |
| Lateral control uses two single-wire serial paths between LKAS and EPS | Confirmed on subject vehicle (passive observation) | Captures 3/4 contain concurrent traffic on both mapped paths; harness investigation identifies the white and blue T-harness branches | Record connector continuity and RX/RXD voltage safety; no active transmission |
| Serial protocol is 9600 8E1 | Strongly supported on subject vehicle | ESP32 UART1/UART2 were configured for 9600 8E1; captures 3/4 contain 4,087 and 20,063 checksum-valid frames at approximately 100 frames/s per channel, with no framing failures | Confirm bit timing/parity independently with a scope or logic analyzer; standard LIN bus semantics remain unproven |
| LKAS→EPS frames are 4 bytes and EPS→LKAS frames are 5 bytes | Strongly supported on subject vehicle (framing) | Captures 3/4 consistently separate GPIO33 into checksum-valid 4-byte frames and GPIO32 into checksum-valid 5-byte frames; analyzer reports 100% checksum validity | Repeat across more vehicle states and a second run; field meanings and standard LIN semantics remain provisional |
| GPIO32/white carries EPS-to-LKAS and GPIO33/blue carries LKAS-to-EPS | Strongly supported | Captures 3/4: GPIO32 has checksum-valid 5-byte records; GPIO33 has checksum-valid 4-byte records; T-harness colours are documented | Record continuity from LKAS pins 3/5 to the T-harness and repeat |
| The single-wire protocol is standard LIN | Open; do not assume | TJA102x modules are only physical-layer candidates | Look for break/sync/PID/master scheduling behaviour |
| Radar link is one-wire and approximately 8.5 V | Observed | Voltage and connector investigation | Scope waveform and determine direction/framing |
| Radar transmits one-way to ACC unit | Inferred | Topology and current working hypothesis | Simultaneous probing at both ends or controlled disconnect |
| Facelift car has no separate LKAS unit | Strongly inferred/part-number based | Camera/controller architecture and module inventory | Confirm against facelift service manual and all connector routing |
| Buttons, VSA, PCM, gas, ACC HUD and LKAS HUD resemble related Nidec Honda layouts | Community report plus capture support | DoRaN analysis and current DBC | Validate each signal against isolated actions |
| A custom DBC is required | Confirmed | CU2 message/DLC differences and missing `0x1FA` | Continue per-signal validation |
| CANable termination must be disabled on the connected vehicle bus | Confirmed engineering requirement | Existing vehicle bus already terminated | Record jumper state in every capture |
| Either ESP32 GND pin may be used | Confirmed for normal dev boards | Ground pins share board ground plane | Check exact board schematic if variant differs |
| Passive serial logger cannot transmit on capture channels | Confirmed by current design | TX pins unassigned and TX buffers disabled | Scope outputs during boot/reset before vehicle use |
| Tested LINTTL3-style module TX outputs are ESP32-safe when directly connected | Disproved | Both modules measured 4.89 V open-circuit; direct connection raised GPIO32/GPIO33 to approximately 3.8 V | Keep the pins marked TX disconnected; measure the pins marked RX separately |
| TJA1021 `RXD` / terminal `RX` carries readable serial data on the tested boards | Strongly supported as the receive path; electrical safety still open | The tested terminal nomenclature is `RX` -> TJA1021 `RXD` -> output to MCU; using that current receive-only path produced checksum-valid traffic on both channels with no added resistors | Measure RX/RXD-to-GND high level under vehicle power; use level conversion if it exceeds 3.6 V |
| Initial vehicle captures contained serial steering bytes | Mixed by test setup | Captures 1 and 2 had zero bytes on the historical TX/TXD connection; captures 3 and 4 had checksum-valid traffic on the current RX/RXD path | Repeat under documented wiring and record the exact board terminal and connector continuity |
| Stock pass-through is required for an active serial gateway | Safety requirement | Failure analysis | Validate hardware under power loss/reset/stuck-output faults |
| ACC pins 1/11 and LKAS pins 7/8 are the shared F-CAN pairs | Strongly supported | DMM snapshots near 2.7/2.2 V and existing CAN captures | Document connector view, continuity and differential capture at both connectors |
| ACC grounds are pins 2/19/20 and LKAS ground is pin 9 | Observed/likely | Black wires and worksheet labels | Confirm low resistance and voltage drop to chassis/module ground |
| LKAS pins 3 and 5 are the two steering serial channels | Strongly supported | White LKAS pin 3 is connected through the T-harness to GPIO32 and carries 5-byte EPS-to-LKAS candidates; blue LKAS pin 5 is connected to GPIO33 and carries 4-byte LKAS-to-EPS candidates in captures 3/4 | Record continuity from each connector pin to the T-harness and repeat on a second run |
| LKAS pin 4 / ACC pin 3 is K-line | Open; name not confirmed | Both teal wires measured near 9.3 V in worksheet | Continuity test and framed traffic capture; do not assume ISO 9141 |
| ACC pin 14 is the radar single-wire link | Open | Worksheet label and 4.3 V snapshot | Reconcile with prior ~8.5 V observation, verify connector orientation and scope both ends |
| ACC pin 16 is write enable | Open; do not drive | Original worksheet working label only | Determine circuit destination and state transitions passively |
| Connector numbering orientation is established | Open | Worksheet contains pin numbers but no connector-face/latch diagram | Add photographs/drawings of both mating views before harness fabrication |
