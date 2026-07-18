# Manufacturing workflow

The KiCad project is the source of truth. Run the release tooling from the repository root:

```powershell
uv run --project automation hwrelease validate
uv run --project automation hwrelease build
uv run --project automation hwrelease inspect
```

Formal releases omit `--allow-dirty`, use a clean commit, and are tagged as
`hardware-vMAJOR.MINOR.PATCH`. Generated packages live under `dist/` and are not
committed. A development build may use `--allow-dirty`; `--allow-warnings` exists
only for diagnosis and is recorded in the manifest.

The checked-in `.kicad_jobset` is the native GUI/CLI fallback and can be run from
KiCad's Jobsets dialog or with:

```powershell
kicad-cli jobset run --stop-on-error --file usb-pd-splitter.kicad_jobset `
  --output "Local release staging" usb-pd-splitter.kicad_pro
```

## Population policy

All components are fitted unless their KiCad DNP attribute is set. A component
intended for hand assembly must be DNP. The release tool compares the fitted
schematic references against the JLCPCB BOM and CPL.

## First-article requirement

Before ordering, upload the generated Gerber, BOM, and CPL as a draft order.
Check every JLCPCB part match, polarity, rotation, and centroid. Record confirmed
exceptions in KiCad using `JLCPCB Rotation Offset`, `JLCPCB Position Offset`, or
`JLCPCB Layer Override`; never hand-edit the release CSV as the lasting fix.
