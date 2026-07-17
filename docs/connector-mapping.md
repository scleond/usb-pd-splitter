# USB-PD Splitter Connector Mapping

## Connectors

- `PWR_IN` — USB-C power input
- `DATA_IN` — USB-C host data input
- `OUT` — USB-C powered device output

## Power path

- `PWR_IN.VBUS` → `OUT.VBUS`
- `PWR_IN.GND` → `OUT.GND`
- `PWR_IN.CC1` → `OUT.CC1`
- `PWR_IN.CC2` → `OUT.CC2`

### Notes
- `PWR_IN` is the only source of power for `OUT`
- All other power/data pins on `PWR_IN` are Do Not Populate (DNP)
- `OUT` must receive CC negotiation for PD through the power path

## Data path

- `DATA_IN.D+` → `OUT.D+`
- `DATA_IN.D-` → `OUT.D-`
- `DATA_IN.GND` → `OUT.GND`
- `DATA_IN.CC1` / `DATA_IN.CC2` present host-side signaling to the host connector

### Notes
- `DATA_IN.VBUS` is not connected to `OUT`
- The data connector is a host-side interface, so CC should indicate a downstream-facing port source

## Pin usage summary

| Connector | Pin group | Usage |
| --- | --- | --- |
| `PWR_IN` | `VBUS`, `GND`, `CC1`, `CC2` | Connected to `OUT` |
| `PWR_IN` | USB 2.0/3.0 data pins | DNP |
| `DATA_IN` | `D+`, `D-`, `GND` | Connected to `OUT` |
| `DATA_IN` | `CC1`, `CC2` | Host-side role signaling |
| `DATA_IN` | `VBUS` | Isolated / not connected to `OUT` |
| `OUT` | `VBUS`, `GND`, `CC1`, `CC2`, `D+`, `D-` | Connected to power and data paths as above |

## Design caution
- This topology is passive, so it relies on the attached power source and attached device to negotiate PD correctly.
- The host connected to `DATA_IN` must see a correct host CC presentation, or USB enumeration may fail.
- If the connected device on `OUT` expects a different role on `D+`/`D-`, the passive split may require active switching or a repeater.
