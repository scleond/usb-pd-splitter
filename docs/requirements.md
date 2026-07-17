# USB-PD Splitter Requirements

## Purpose
Create a passive USB-C splitter that separates power and data for a powered device.

## Connectors
- `PWR_IN`: USB-C power input
- `DATA_IN`: USB-C host data input
- `OUT`: USB-C device output

## Signal requirements
- `PWR_IN` supplies:
  - `VBUS` → `OUT.VBUS`
  - `GND` → `OUT.GND`
  - `CC1/CC2` → `OUT.CC1/CC2`
- `DATA_IN` supplies:
  - `D+` → `OUT.D+`
  - `D-` → `OUT.D-`
  - `GND` → `OUT.GND`
  - `CC1/CC2` to indicate host/data-side role
- `DATA_IN.VBUS` is not connected to `OUT`
- `PWR_IN` non-CC high-speed/data pins are DNP

## Roles
- `DATA_IN` is the USB host-side data connector
- `OUT` is the powered USB device connector
- `PWR_IN` is the power source connector
- The board is passive and does not contain an active PD controller

## Assumptions
- The power source and attached device negotiate PD independently through the `PWR_IN` → `OUT` power path.
- `DATA_IN` must present the correct CC role for a host-side data connection.
- The device on `OUT` will receive `VBUS` from `PWR_IN` and `D+/D-` from `DATA_IN`.

## KiCad
- This project is targeted for KiCad 10.
- Custom symbols and footprints will be stored under `hardware/symbols/` and `hardware/footprints/`.
