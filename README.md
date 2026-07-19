# USB-PD Splitter

![Isometric raytraced view of the USB-PD Splitter PCB](docs/assets/usb-pd-splitter-isometric.png)

A KiCad 10 design for a passive USB-C power/data injector: a dedicated USB-C
power input and a separate USB 2.0 data input feed one USB-C device output.

## At a glance

- `PWR_IN` supplies `VBUS`, `GND`, and CC signaling to `OUT`.
- `DATA_IN` supplies USB 2.0 `D+`, `D-`, and `GND` to `OUT`; its `VBUS` is
  isolated from the power path.
- `OUT` is the powered device connection.

This board has no USB-PD controller, data repeater, or role-switching circuit.
Its behavior must be validated with the intended power source, host, and device.

## Repository

- `usb-pd-splitter.kicad_pro`, `.kicad_sch`, and `.kicad_pcb` — KiCad sources
- `usb-pd-splitter.kicad_jobset` — native KiCad validation/export jobset
- `hardware/` — project-local symbols, footprints, and 3D models
- `automation/` — reproducible release CLI and unit tests
- `bom/` — reviewed, human-readable BOM snapshot
- `manufacturing/` — fabrication profile and release templates

Generated review and release artifacts belong in `outputs/` and `dist/`; they
are not source files.

## Documentation

- [Design notes](docs/DESIGN.md) — topology and operating assumptions
- [Requirements](docs/requirements.md) — intended interfaces and constraints
- [Connector mapping](docs/connector-mapping.md) — power, data, and CC paths
- [Release checklist](docs/manufacturing/release-process.md) — required release steps
- [Manufacturing tooling decisions](docs/manufacturing/tooling-decisions.md) — release architecture and boundaries
- [BOM guidance](bom/README.md) — tracked snapshot policy

## Release quick start

Install KiCad 10, make `kicad-cli` available on `PATH`, and install `uv`. After
changing fitted parts, refresh the snapshot and run the preflight:

```powershell
uv run --project automation hwrelease export-bom
uv run --project automation hwrelease validate
```

The formal build, JLCPCB draft placement review, packaging, tagging, and draft
publication process is documented in the [release checklist](docs/manufacturing/release-process.md).
No repository command places an order.
