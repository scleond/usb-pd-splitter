# Hardware release process

Use this checklist for every hardware release. The workflow below is organized into a simple sequence: prepare the design, validate it, review manufacturing outputs, package the release, and publish it.

## 1. Prepare the design

- Update the KiCad title-block revision and `HW_VERSION` project variable.
- Confirm every fitted part has Manufacturer, MPN, and LCSC Part # in both schematic and PCB metadata.
- Mark every hand-assembled component as DNP.
- Save the schematic, update the PCB from the schematic, refill zones, and save again.

## 2. Validate the design

- Run `uv run --project automation hwrelease export-bom` after any fitted-part change.
- Run `uv run --project automation hwrelease validate` until all metadata gates pass.
- Run the native KiCad jobset to generate local review outputs, and run ERC/DRC with schematic parity; resolve every non-excluded finding. The formal builder performs the parity check.
- Review the front/back assembly PDFs and STEP model in `outputs/jobset/`, then review their formal-build counterparts in `dist/<release>/assembly/` and `dist/<release>/mechanical/`.
- Add board-specific drawing notes in PCB Editor on `Dwgs.User` or `Cmts.User` so they appear in the PDFs.

## 3. Prepare for release

- Commit the complete design.
- Run `uv run --project automation hwrelease build` from a clean tree.
- Run `uv run --project automation hwrelease inspect`, verify checksums, and compare the BOM/CPL with Fabrication Toolkit.
- Optionally generate InteractiveHtmlBom for internal review or hand-assembly guidance.

## 4. Review manufacturing data

- Perform a draft JLCPCB upload and resolve every match, centroid, side, and rotation warning.
- Review the BOM, CPL, and placement preview before approving the upload.

## 5. Package and publish

- Run `uv run --project automation hwrelease package` to create the complete release archive and checksum.
- Tag and push the approved commit as `hardware-vX.Y.Z`.
- After `gh auth login`, create a guarded draft with `uv run --project automation hwrelease publish --draft --placement-reviewed`.
- Inspect every GitHub asset, then publish the draft explicitly in GitHub or with `gh release edit hardware-vX.Y.Z --draft=false --latest`.

## 6. Follow up after release

- Inspect and document the first article before approving repeat builds.
