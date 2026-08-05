# Vehicle architecture

## Subject vehicle

- Honda Accord VIII CU2, European/Japanese-market architecture
- Model year: 2013 facelift
- Engine: K24
- Transmission: automatic
- OEM systems: ACC, CMBS and LKAS

This architecture must not be confused with the North American eighth-generation Accord. The closest US-market relative for some body/service information is the Acura TSX, but ADAS details still require CU2-specific verification.

## Identified modules

| Function | Part number | Current understanding |
|---|---|---|
| LKAS camera/controller | `36870-TL3-B11` | Camera and lateral controller; no separate facelift LKAS unit identified |
| Radar | `36802-TL0-G11` | Connected to ACC controller through a separate single-wire link |
| ACC/ADAS controller | `36700-TL3-B01-M` | Participates in F-CAN and controls ACC/CMBS functions |
| EPS | not yet recorded here | Exchanges two single-wire serial channels with LKAS system |


## Connector-level evidence

The current reverse-engineered connector tables are maintained in
[`CONNECTOR_PINOUTS.md`](CONNECTOR_PINOUTS.md). They locate the likely F-CAN
pair at both the ACC and LKAS connectors and identify several single-wire
candidates, but connector orientation and most function names still require
repeatable validation.

Do not infer signal direction from the original `RX?`/`TX?` labels; the
viewpoint was not recorded.

## Current communication model

```text
                   separate single-wire link
OEM radar  ---------------------------------------->  ACC/ADAS unit
                                                         |
                                                         | shared F-CAN
                                                         |
PCM / VSA / cluster / HUD / other modules  <-------------+------------>  LKAS camera
                                                                          |
                                                                          | two independent
                                                                          | single-wire serial paths
                                                                          v
                                                                         EPS
```

The arrow on the radar link is an inference, not a confirmed direction.

## Shared F-CAN

**Confirmed for the supplied captures:** the observed vehicle traffic is on one common CAN network. It contains the messages used for:

- powertrain and vehicle speed context;
- brake/pressure response;
- ACC state and set speed;
- ACC/LKAS HUD state;
- steering sensor context;
- buttons and VSA-related state;
- the current `0x1C0` brake-command candidate.

Earlier assumptions about a separate ACC CAN should be treated as superseded for this tested facelift CU2 unless new physical evidence proves otherwise.

## Serial steering paths

The lateral steering link is not represented by the conventional Honda CAN steering-command messages expected by current openpilot integrations. The working model is two independent 12 V single-wire serial channels between LKAS and EPS:

- probable LKAS-to-EPS command direction;
- probable EPS-to-LKAS feedback direction.

Reference implementations suggest 9600 baud, 8E1, with 4-byte and 5-byte frames respectively, but this still requires capture on the subject car.

## Radar link

A separate wire between radar and ACC unit measured approximately 8.5 V in one previous investigation. The connector worksheet separately records 4.3 V at ACC pin 14, labelled `radar data`; the conditions and exact equivalence of those observations are unresolved. It may be LIN-like or another proprietary single-wire physical layer. The following remain open:

- exact electrical layer;
- baud and framing;
- directionality;
- whether the radar transmits continuously or responds to polling;
- whether it can be passively monitored with the current TJA1020/TJA1021-style modules.

Do not label this link as LIN until framing and bus behaviour are measured.
