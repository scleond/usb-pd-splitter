# USB-PD Splitter

A simple KiCad project scaffold for a USB-C splitter with separate power and data inputs feeding a single output connector.

This repository is currently a documentation and project-organization scaffold. The schematic and PCB files are intentionally minimal and still need to be populated in KiCad.

## Design intent
- 3x USB-C connectors
  - `PWR_IN`: USB-C power input
  - provides `VBUS`, `GND`, and `CC1`/`CC2` to `OUT`
  - all data pins are DNP
- `DATA_IN`: USB-C host data input
  - provides `D+`, `D-`, `GND`, and CC signaling for the host
  - `VBUS` is isolated from `OUT`
- `OUT`: powered USB-C device output
  - receives `VBUS`, `GND`, and `CC1`/`CC2` from `PWR_IN`
  - receives `D+`, `D-`, and `GND` from `DATA_IN`
- `DATA_IN` CC pins will be configured to present host-side signaling on the data path
- `OUT` is the powered device connection, and the power source negotiates with the device passively through the splitter

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
