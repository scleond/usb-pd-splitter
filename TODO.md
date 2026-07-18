# Manufacturing origin TODO

Goal: establish one explicit, board-relative manufacturing origin so Gerber,
drill, and component-placement outputs use the same coordinate system and fitted
component centroids do not have unexpected negative coordinates.

## 1. Define the convention

- [ ] Set KiCad's drill/place-file origin at the lower-left corner of the finished
  board outline.
- [ ] Document whether the origin is exactly on the `Edge.Cuts` corner or offset
  by a defined margin for boards without a simple rectangular outline.
- [ ] Add the origin policy and permitted coordinate tolerance to
  `manufacturing/profiles/jlcpcb.toml`.
- [ ] Treat shared-origin consistency as the release requirement; positive
  placement coordinates are a derived validation check.

## 2. Make every export use the same origin

- [ ] Update the Python release CLI to use KiCad's drill/place origin for Gerbers,
  Excellon drill files, drill maps, and native position output.
- [ ] Update `usb-pd-splitter.kicad_jobset` with the equivalent origin settings.
- [ ] Confirm IPC-2581, ODB++, IPC-D-356, PDF, and mechanical exports either use
  the same origin or clearly document why their coordinate systems differ.
- [ ] Ensure no export applies an additional unrecorded X/Y translation.

## 3. Add automated validation

- [ ] Read the configured origin and calculate the `Edge.Cuts` board bounding box.
- [ ] Require all fitted CPL references to match the fitted BOM references.
- [ ] Reject fitted centroids with X or Y below the configured rounding tolerance.
- [ ] Reject centroids outside the board bounding box, allowing a documented
  tolerance for edge-mounted connectors whose footprint origins remain on-board.
- [ ] Normalize rotations to 0-359 degrees without changing component positions.
- [ ] Add unit tests for positive coordinates, negative-coordinate rejection,
  boundary tolerances, malformed values, and top/bottom components.

## 4. Improve release traceability

- [ ] Record the manufacturing-origin coordinates, origin type, board bounds, and
  validation tolerance in `manifest.json`.
- [ ] Include a coordinate-validation summary in `hwrelease inspect`.
- [ ] Add the origin convention to fabrication and assembly notes.
- [ ] Explain how to reproduce the origin when this repository becomes a template.

## 5. Validate with actual outputs

- [ ] Regenerate the complete release package from a clean commit.
- [ ] Confirm ERC, DRC, and schematic parity remain at zero findings.
- [ ] Compare Gerber and drill alignment in KiCad Gerber Viewer.
- [ ] Compare the repository-generated CPL against Fabrication Toolkit output.
- [ ] Upload Gerber, BOM, and CPL files to a draft JLCPCB order.
- [ ] Verify every centroid, rotation, layer, and connector placement in JLCPCB's
  assembly preview before approving the convention.
- [ ] Record any required footprint-specific rotation or position corrections in
  KiCad metadata, then regenerate rather than editing the CPL manually.

## Acceptance criteria

- [ ] Gerber, drill, and CPL outputs share one documented manufacturing origin.
- [ ] All fitted component centroids pass board-bounds and coordinate checks.
- [ ] The manifest makes the coordinate system independently auditable.
- [ ] The native jobset and Python release path produce equivalent aligned data.
- [ ] A JLCPCB draft upload confirms correct placement without manual CSV edits.
