# Hardware release process

1. Update the KiCad title-block revision and `HW_VERSION` project variable.
2. Confirm all fitted parts have Manufacturer, MPN, and LCSC Part # fields.
3. Mark every hand-assembled component DNP.
4. Save the schematic, update the PCB from the schematic, refill zones, and save.
5. Run `uv run --project automation hwrelease export-bom` after any fitted-part change.
6. Run `uv run --project automation hwrelease validate` until all metadata gates pass.
7. Run the native KiCad jobset or ERC/DRC and resolve every non-excluded finding. The jobset writes local review outputs to `outputs/jobset/`, including front/back assembly PDFs and a STEP model; the formal builder recreates them in `dist/`. Review the drawings and STEP model. Add board-specific drawing notes in PCB Editor on `Dwgs.User` or `Cmts.User` so they appear in the PDFs.
8. Commit the complete design and run `uv run --project automation hwrelease build` from a clean tree.
9. Run `hwrelease inspect`, verify checksums, and compare BOM/CPL with Fabrication Toolkit.
10. Optionally generate InteractiveHtmlBom for internal review or hand-assembly guidance.
11. Perform a draft JLCPCB upload and resolve every match, centroid, side, and rotation warning.
12. Run `uv run --project automation hwrelease package` to create the complete release archive and checksum.
13. Tag and push the approved commit as `hardware-vX.Y.Z`.
14. After `gh auth login`, create a guarded draft with
    `uv run --project automation hwrelease publish --draft --placement-reviewed`.
15. Inspect every GitHub asset, then publish the draft explicitly in GitHub or with
    `gh release edit hardware-vX.Y.Z --draft=false --latest`.
16. Inspect and document the first article before approving repeat builds.
