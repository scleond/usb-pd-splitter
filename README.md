# USB-PD Splitter

A KiCad hardware design for a passive USB-C power and data splitter. The design combines power from a dedicated USB-C input with USB 2.0 data from a separate USB-C input and routes both to a single USB-C device output.

## Design intent

The design uses three USB-C connectors:

- `PWR_IN`: dedicated USB-C power source
  - Supplies `VBUS` and `GND` to `OUT`
  - Passes `CC1` and `CC2` to `OUT` for source-to-device role signaling
  - USB data pins are not connected and are marked DNP

- `DATA_IN`: USB-C host/data source
  - Supplies USB 2.0 `D+`, `D-`, and `GND` to `OUT`
  - Uses appropriate host/source-side CC pull-ups (`Rp`) for attachment and role detection
  - Its `VBUS` is isolated from the power path and is not connected to `OUT`

- `OUT`: USB-C powered device connection
  - Receives `VBUS`, `GND`, and CC signaling from `PWR_IN`
  - Receives USB 2.0 `D+` and `D-` from `DATA_IN`
  - Is intended to operate as the sink/device-side connection

This is a passive power-injection topology. It does not contain a USB-PD controller, USB data repeater, or role-switching circuitry. Power negotiation and USB-C attachment behavior depend on the connected source and device and must be validated with the intended hardware.

The design currently targets USB 2.0 data only; USB 3.x, USB4, and alternate-mode signals are not supported.

## Project structure
- `usb-pd-splitter.kicad_pro` - KiCad project file
- `usb-pd-splitter.kicad_sch` - main schematic file
- `usb-pd-splitter.kicad_pcb` - PCB layout file
- `hardware/symbols/` - custom schematic symbols
- `hardware/footprints/` - custom footprints
- `hardware/3d_models/` - 3D model assets
- `docs/` - design notes and reference documents
- `bom/` - exported bill-of-materials files
- `outputs/` - fabrication and review exports; generated subdirectories are ignored

## Notes
This design is a passive power/data splitter, not a USB Power Delivery controller. It assumes:
- `PWR_IN` supplies `VBUS` and negotiates PD directly with the device on `OUT`
- `DATA_IN` is the host-side data connection and provides USB signaling to `OUT`
- `OUT` is the powered device and receives `VBUS` from `PWR_IN` and data from `DATA_IN`

Because the power and data paths are separated, this is effectively a power injector topology and should be verified with the target host and device hardware.

## Working conventions

- Treat the KiCad schematic as the source of truth for connectivity.
- Keep reusable source assets under `hardware/`; keep generated exports under `outputs/`.
- Record unresolved electrical-role decisions in `docs/` before committing the final schematic.
