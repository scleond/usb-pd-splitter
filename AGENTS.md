# Hardware-agent rules

- The KiCad schematic and PCB are authoritative; generated files are not.
- Before changing manufacturing data, read `manufacturing/profiles/jlcpcb.toml` and
  `docs/manufacturing/release-process.md`.
- Every fitted physical part requires `Manufacturer`, `MPN`, and `LCSC Part #` in
  both schematic and synchronized PCB metadata.
- A part intended for hand assembly must be DNP. Every non-DNP reference must occur
  in both the JLCPCB BOM and CPL.
- Run `uv run --project automation hwrelease validate` and the unit tests after
  metadata changes. A formal build must use a clean tree and zero KiCad findings.
- Do not edit `outputs/` or `dist/` artifacts as a source fix. Do not place an order,
  upload files, tag a release, or push changes without explicit human authorization.
- AI/MCP edits require review of the source diff plus ERC, DRC, schematic parity,
  BOM/CPL reference parity, and the JLCPCB placement preview.
