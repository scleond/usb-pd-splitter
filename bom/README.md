# Bill of materials

Store reviewed, human-readable BOM exports here. Prefer a filename that identifies
the schematic revision or release, for example `usb-pd-splitter-r0.csv`.

Refresh the tracked snapshot with `uv run --project automation hwrelease export-bom`
after a fitted-part change. `hwrelease validate` rejects a stale snapshot.

Machine-generated or temporary exports that do not belong in version control should
go under `outputs/` instead.
