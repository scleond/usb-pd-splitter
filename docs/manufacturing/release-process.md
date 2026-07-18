# Hardware release process

1. Update the KiCad title-block revision and `HW_VERSION` project variable.
2. Confirm all fitted parts have Manufacturer, MPN, and LCSC Part # fields.
3. Mark every hand-assembled component DNP.
4. Save the schematic, update the PCB from the schematic, refill zones, and save.
5. Run `uv run --project automation hwrelease validate` until all metadata gates pass.
6. Run the native KiCad jobset or ERC/DRC and resolve every non-excluded finding.
7. Commit the complete design and run `uv run --project automation hwrelease build` from a clean tree.
8. Run `hwrelease inspect`, verify checksums, and compare BOM/CPL with Fabrication Toolkit.
9. Optionally generate InteractiveHtmlBom for internal review or hand-assembly guidance.
10. Perform a draft JLCPCB upload and resolve every match, centroid, side, and rotation warning.
11. Run `uv run --project automation hwrelease package` to create the complete release archive and checksum.
12. Tag and push the approved commit as `hardware-vX.Y.Z`.
13. After `gh auth login`, create a guarded draft with
    `uv run --project automation hwrelease publish --draft --placement-reviewed`.
14. Inspect every GitHub asset, then publish the draft explicitly in GitHub or with
    `gh release edit hardware-vX.Y.Z --draft=false --latest`.
15. Inspect and document the first article before approving repeat builds.
