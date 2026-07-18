# Manufacturing tooling decisions

Reviewed 2026-07-18 for KiCad 10 and JLCPCB assembly.

## Selected architecture

1. KiCad files are the single source of truth for design, population, and sourcing.
2. The native `.kicad_jobset` is the transparent GUI/CLI export fallback.
3. The repository-local `hwrelease` Python CLI is the reproducible release gate and
   packager. It invokes `kicad-cli`; it does not reimplement Gerber or drill plotting.
4. JLCPCB Fabrication Toolkit is an independent pre-order cross-check, not the sole
   release generator. Compare its BOM/CPL and the JLCPCB upload preview to the release.
5. InteractiveHtmlBom is optional internal documentation for visual inspection and
   hand assembly. It is not a fabrication source file.
6. Generated artifacts stay in ignored `outputs/` and `dist/`; the package manifest,
   source hashes, and `SHA256SUMS` provide traceability.

The Python gate is authoritative for schematic parity. KiCad 10.0.4's jobset DRC can
report that it cannot fetch a schematic netlist while still returning job success;
the jobset therefore runs ordinary DRC, while `hwrelease` invokes the direct DRC CLI
with `--schematic-parity` and parses all three JSON result sections.

KiCad 10 supports reusable jobsets and first-party command-line ERC, DRC, Gerber,
position, BOM, PDF, STEP, IPC-2581, ODB++, and related exports:
https://docs.kicad.org/10.0/en/cli/cli.html

JLCPCB's KiCad 10 guidance recommends Fabrication Toolkit for a one-click JLC-ready
cross-check and documents the required BOM/CPL columns:
https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad

Fabrication Toolkit:
https://github.com/bennymeg/Fabrication-Toolkit

InteractiveHtmlBom:
https://github.com/openscopeproject/InteractiveHtmlBom

## Python boundary

Python owns policy that KiCad does not: metadata completeness, revision agreement,
clean-tree enforcement, DNP population rules, BOM/CPL reference parity, JLC column
mapping, normalized 0-359 degree rotations, package naming, manifests, and checksums.
The standard library is sufficient at runtime, and `uv` provides a reproducible entry
point on Windows, macOS, and Linux.
Native KiCad X/Y placement coordinates are preserved; JLCPCB's documented KiCad 10
workflow accepts the native coordinate data after column mapping. The mandatory draft
upload remains the final centroid/orientation check.

## AI and MCP boundary

Community MCP servers now cover KiCad analysis, editing, validation, and exports, but
they differ in file-format strategy, KiCad/Python coupling, and maturity. Candidates
worth reevaluating before adoption include:

- `mixelpixx/KiCAD-MCP-Server` for broad KiCad/JLC workflows.
- `Seeed-Studio/kicad-mcp-server` for KiCad Python/API-oriented inspection and edits.
- `oaslananka-lab/kicad-mcp-pro` for profile-based validation/export workflows.
- `rjwalters/kicad-tools` for standalone parsing and transactional agent sessions.

No MCP server is part of the release trust boundary today. Agents should call the same
checked-in validation/build commands as humans, work only inside the repository, and
leave ordering, release tags, warning exclusions, and placement-preview approval to a
human. This keeps future MCP adoption interchangeable instead of coupling the template
to one fast-moving community server.
