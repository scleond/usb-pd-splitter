from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_FIELDS = ("Manufacturer", "MPN", "LCSC Part #")
PROPERTY_RE = re.compile(r'\(property\s+"([^"]+)"\s+"([^"]*)"')
MODEL_EXTENSIONS = {".step", ".stp", ".wrl", ".obj", ".ply", ".gltf", ".glb"}
ISOMETRIC_RENDER_SETTINGS = (
    "--width", "1600",
    "--height", "900",
    "--side", "top",
    "--background", "opaque",
    "--quality", "high",
    "--floor",
    "--perspective",
    "--zoom", "0.7",
    "--rotate", "-45,0,45",
)


@dataclass(frozen=True)
class Part:
    reference: str
    value: str
    footprint: str
    dnp: bool
    fields: dict[str, str]


@dataclass(frozen=True)
class ReleasePackage:
    release_dir: Path
    archive: Path
    archive_checksum: Path
    tag: str


def project_root(start: Path | None = None) -> Path:
    path = (start or Path.cwd()).resolve()
    for candidate in (path, *path.parents):
        if list(candidate.glob("*.kicad_pro")):
            return candidate
    raise SystemExit("No KiCad project found in this directory or its parents")


def load_profile(root: Path) -> dict:
    with (root / "manufacturing/profiles/jlcpcb.toml").open("rb") as handle:
        return tomllib.load(handle)


def project_files(root: Path) -> tuple[Path, Path, Path]:
    projects = list(root.glob("*.kicad_pro"))
    if len(projects) != 1:
        raise ValueError(f"Expected one .kicad_pro file, found {len(projects)}")
    stem = projects[0].stem
    return projects[0], root / f"{stem}.kicad_sch", root / f"{stem}.kicad_pcb"


def symbol_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks: list[str] = []
    current: list[str] = []
    depth = 0
    collecting = False
    for line in lines:
        if not collecting and re.match(r"^\s*\(symbol\s*$", line):
            collecting = True
            current = [line]
            depth = line.count("(") - line.count(")")
            continue
        if collecting:
            current.append(line)
            depth += line.count("(") - line.count(")")
            if depth == 0:
                block = "\n".join(current)
                if "(lib_id " in block:
                    blocks.append(block)
                collecting = False
    return blocks


def parse_parts(schematic: Path) -> list[Part]:
    parts: list[Part] = []
    for block in symbol_blocks(schematic.read_text(encoding="utf-8")):
        fields = dict(PROPERTY_RE.findall(block))
        ref = fields.get("Reference", "")
        if not ref or ref.startswith("#"):
            continue
        parts.append(
            Part(
                reference=ref,
                value=fields.get("Value", ""),
                footprint=fields.get("Footprint", ""),
                dnp="(dnp yes)" in block,
                fields=fields,
            )
        )
    return sorted(parts, key=lambda item: natural_key(item.reference))


def natural_key(value: str) -> tuple:
    return tuple(int(piece) if piece.isdigit() else piece for piece in re.split(r"(\d+)", value))


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def documentation_render_paths(root: Path, slug: str) -> tuple[Path, Path]:
    base = root / "docs/assets" / f"{slug}-isometric"
    return base.with_suffix(".png"), base.with_suffix(".render.json")


def standard_3d_model_directory(kicad: str, kicad_major: int) -> Path:
    variable = f"KICAD{kicad_major}_3DMODEL_DIR"
    candidates: list[Path] = []
    configured = os.environ.get(variable)
    if configured:
        candidates.append(Path(configured))

    executable = shutil.which(kicad)
    if not executable and Path(kicad).is_file():
        executable = kicad
    if executable:
        install_root = Path(executable).resolve().parent.parent
        candidates.append(install_root / "share/kicad/3dmodels")

    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()

    checked = ", ".join(str(candidate) for candidate in candidates) or "no candidate paths"
    raise RuntimeError(f"Unable to resolve {variable}; checked {checked}")


def kicad_profile_directories(kicad_major: int) -> list[Path]:
    version = f"{kicad_major}.0"
    if os.name == "nt":
        directories: list[Path] = []
        if appdata := os.environ.get("APPDATA"):
            directories.append(Path(appdata) / "kicad" / version)
        if local_appdata := os.environ.get("LOCALAPPDATA"):
            directories.append(Path(local_appdata) / "KiCad" / version)
        return directories

    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return [config_home / "kicad" / version]


def ensure_kicad_profile_access(kicad_major: int, directories: list[Path] | None = None) -> None:
    profile_directories = directories if directories is not None else kicad_profile_directories(kicad_major)
    for directory in profile_directories:
        try:
            if not directory.exists():
                continue
            if not directory.is_dir():
                raise RuntimeError(f"KiCad profile path is not a directory: {directory}")
            next(directory.iterdir(), None)
        except OSError as error:
            raise RuntimeError(
                f"KiCad profile is not readable: {directory}. "
                "Run the render with normal user-profile access; restricted renders can silently omit 3D models."
            ) from error


def isometric_render_command(
    kicad: str,
    pcb: Path,
    output: Path,
    model_directory: Path,
    kicad_major: int,
) -> list[str]:
    return [
        kicad,
        "pcb",
        "render",
        "--define-var",
        f"KICAD{kicad_major}_3DMODEL_DIR={model_directory}",
        "--output",
        str(output),
        *ISOMETRIC_RENDER_SETTINGS,
        str(pcb),
    ]


def render_source_hashes(root: Path, pro: Path, pcb: Path) -> dict[str, str]:
    sources = [pro, pcb]
    model_root = root / "hardware/3d_models"
    if model_root.exists():
        sources.extend(
            path
            for path in sorted(model_root.rglob("*"))
            if path.is_file() and path.suffix.lower() in MODEL_EXTENSIONS
        )
    return {path.relative_to(root).as_posix(): sha256(path) for path in sources}


def expected_render_metadata(root: Path, profile: dict, pro: Path, pcb: Path) -> dict:
    return {
        "schema": 1,
        "renderer": "kicad-cli pcb render",
        "kicad_major": profile["project"]["kicad_major"],
        "settings": list(ISOMETRIC_RENDER_SETTINGS),
        "sources": render_source_hashes(root, pro, pcb),
    }


def documentation_render_errors(root: Path, profile: dict, pro: Path, pcb: Path) -> list[str]:
    image, metadata_path = documentation_render_paths(root, profile["project"]["slug"])
    if not image.exists():
        return [f"Missing README render: {image.relative_to(root)} (run hwrelease render-docs)"]
    if not metadata_path.exists():
        return [f"Missing README render metadata: {metadata_path.relative_to(root)} (run hwrelease render-docs)"]
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [f"Invalid README render metadata: {metadata_path.relative_to(root)} (run hwrelease render-docs)"]
    expected = expected_render_metadata(root, profile, pro, pcb)
    recorded = {key: metadata.get(key) for key in expected}
    if recorded != expected:
        return ["README render is stale relative to its PCB, project, models, or render settings (run hwrelease render-docs)"]
    if metadata.get("image_sha256") != sha256(image):
        return ["README render checksum does not match its metadata (run hwrelease render-docs)"]
    return []


def render_isometric(root: Path, pcb: Path, output: Path, kicad: str, required: bool = True) -> None:
    kicad_major = load_profile(root)["project"]["kicad_major"]
    ensure_kicad_profile_access(kicad_major)
    output.parent.mkdir(parents=True, exist_ok=True)
    model_directory = standard_3d_model_directory(kicad, kicad_major)
    run(
        isometric_render_command(kicad, pcb, output, model_directory, kicad_major),
        root,
        required=required,
    )
    if required and not output.exists():
        raise RuntimeError(f"KiCad did not create the requested render: {output}")


def render_docs(root: Path) -> Path:
    profile = load_profile(root)
    pro, _sch, pcb = project_files(root)
    kicad = shutil.which("kicad-cli")
    if not kicad:
        raise RuntimeError("kicad-cli is not available on PATH")
    image, metadata_path = documentation_render_paths(root, profile["project"]["slug"])
    render_isometric(root, pcb, image, kicad)
    metadata = expected_render_metadata(root, profile, pro, pcb)
    metadata["image_sha256"] = sha256(image)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return image


def title_revision(path: Path) -> str | None:
    match = re.search(r'\(title_block.*?\(rev\s+"([^"]+)"\)', path.read_text(encoding="utf-8"), re.S)
    return match.group(1) if match else None


def validate(root: Path, allow_dirty: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    profile = load_profile(root)
    try:
        pro, sch, pcb = project_files(root)
    except ValueError as exc:
        return [str(exc)], warnings
    for path in (pro, sch, pcb, root / f"{pro.stem}.kicad_jobset"):
        if not path.exists():
            errors.append(f"Missing required file: {path.relative_to(root)}")
    expected_rev = profile["project"]["revision"]
    for path in (sch, pcb):
        if path.exists() and title_revision(path) != expected_rev:
            errors.append(f"{path.name} title-block revision is not {expected_rev}")
    settings = json.loads(pro.read_text(encoding="utf-8"))
    variables = settings.get("text_variables", {})
    if variables.get("HW_REVISION") != expected_rev:
        errors.append("HW_REVISION project variable disagrees with profile")
    if variables.get("HW_VERSION") != profile["project"]["version"]:
        errors.append("HW_VERSION project variable disagrees with profile")
    if pro.exists() and pcb.exists():
        errors.extend(documentation_render_errors(root, profile, pro, pcb))
    parts = parse_parts(sch)
    if not parts:
        errors.append("No physical schematic parts were found")
    for part in parts:
        if not part.footprint:
            errors.append(f"{part.reference}: missing footprint")
        if not part.dnp:
            for field in REQUIRED_FIELDS:
                if not part.fields.get(field, "").strip():
                    errors.append(f"{part.reference}: fitted part missing {field}")
    dirty = bool(git(root, "status", "--porcelain"))
    if dirty and not allow_dirty:
        errors.append("Git working tree is dirty (use --allow-dirty for development builds)")
    if any(root.glob("~*.lck")):
        warnings.append("KiCad lock file detected; save and close editors before a formal build")
    return errors, warnings


def run(command: list[str], root: Path, required: bool = True) -> subprocess.CompletedProcess[str]:
    shown = " ".join(command)
    print(f"+ {shown}")
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode and required:
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        raise RuntimeError(f"Command failed ({result.returncode}): {shown}")
    return result


def check_report(path: Path, kind: str, allow_warnings: bool) -> dict[str, int]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("sheets"):
        violations = [item for sheet in report["sheets"] for item in sheet.get("violations", [])]
    else:
        violations = [
            item
            for section in ("violations", "unconnected_items", "schematic_parity")
            for item in report.get(section, [])
        ]
    counts = {
        severity: sum(item.get("severity") == severity for item in violations)
        for severity in ("error", "warning", "exclusion")
    }
    if counts["error"]:
        raise RuntimeError(f"{kind} contains {counts['error']} error(s); see {path}")
    if counts["warning"] and not allow_warnings:
        raise RuntimeError(
            f"{kind} contains {counts['warning']} warning(s); resolve/exclude them or use --allow-warnings for a development build"
        )
    return counts


def write_jlc_bom(parts: list[Part], output: Path) -> set[str]:
    groups: dict[tuple[str, str, str, str], list[str]] = {}
    for part in parts:
        if part.dnp:
            continue
        key = (part.value, part.footprint, part.fields["LCSC Part #"], part.fields["MPN"])
        groups.setdefault(key, []).append(part.reference)
    refs: set[str] = set()
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Manufacturer", "MPN"])
        for (value, footprint, lcsc, mpn), designators in sorted(groups.items()):
            designators.sort(key=natural_key)
            refs.update(designators)
            manufacturer = next(p.fields["Manufacturer"] for p in parts if p.reference == designators[0])
            writer.writerow([value, ",".join(designators), footprint, lcsc, manufacturer, mpn])
    return refs


def convert_cpl(native: Path, output: Path) -> set[str]:
    with native.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))
    aliases = {
        "Designator": ("Ref", "Designator"),
        "Mid X": ("PosX", "Mid X"),
        "Mid Y": ("PosY", "Mid Y"),
        "Rotation": ("Rot", "Rotation"),
        "Layer": ("Side", "Layer"),
    }
    refs: set[str] = set()
    with output.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(aliases))
        writer.writeheader()
        for row in rows:
            converted = {name: next((row.get(key, "") for key in keys if key in row), "") for name, keys in aliases.items()}
            converted["Layer"] = {"top": "Top", "bottom": "Bottom", "front": "Top", "back": "Bottom"}.get(converted["Layer"].lower(), converted["Layer"])
            try:
                converted["Rotation"] = f"{float(converted['Rotation']) % 360:g}"
            except ValueError as exc:
                raise RuntimeError(f"Invalid rotation for {converted['Designator']}: {converted['Rotation']}") from exc
            refs.add(converted["Designator"])
            writer.writerow(converted)
    return refs


def zip_directory(source: Path, target: Path, *, excluded_suffixes: frozenset[str] = frozenset()) -> None:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file() and path.suffix.lower() not in excluded_suffixes:
                archive.write(path, path.relative_to(source))


def release_identity(profile: dict) -> tuple[str, str]:
    project = profile["project"]
    release_name = f"{project['slug']}-rev-{project['revision'].lower()}-v{project['version']}"
    tag = f"{profile['release']['tag_prefix']}{project['version']}"
    return release_name, tag


def verify_release_checksums(release: Path) -> None:
    sums_path = release / "SHA256SUMS"
    if not sums_path.exists():
        raise RuntimeError(f"Missing release checksums: {sums_path}")
    expected_files: set[Path] = set()
    release_resolved = release.resolve()
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        try:
            expected_hash, relative_text = line.split("  ", 1)
        except ValueError as exc:
            raise RuntimeError(f"Malformed checksum line in {sums_path}: {line!r}") from exc
        relative = Path(relative_text)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"Unsafe path in {sums_path}: {relative_text}")
        target = (release / relative).resolve()
        try:
            target.relative_to(release_resolved)
        except ValueError as exc:
            raise RuntimeError(f"Checksum path escapes release directory: {relative_text}") from exc
        if not target.is_file():
            raise RuntimeError(f"Release file listed in checksums is missing: {relative_text}")
        if sha256(target) != expected_hash:
            raise RuntimeError(f"Release checksum mismatch: {relative_text}")
        expected_files.add(relative)
    actual_files = {
        path.relative_to(release)
        for path in release.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    }
    if actual_files != expected_files:
        raise RuntimeError(
            f"Release checksum coverage mismatch: unlisted={sorted(actual_files-expected_files)}, "
            f"missing={sorted(expected_files-actual_files)}"
        )


def csv_references(path: Path, column: str) -> set[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        return {
            reference.strip()
            for row in rows
            for reference in row.get(column, "").split(",")
            if reference.strip()
        }


def verify_release(root: Path, release: Path, profile: dict) -> dict:
    manifest_path = release / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"Missing release manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    head = git(root, "rev-parse", "HEAD")
    if manifest.get("git_commit") != head or manifest.get("git_dirty"):
        raise RuntimeError("Release was not built cleanly from the current commit; rebuild it before packaging")
    if manifest.get("project") != profile["project"]:
        raise RuntimeError("Release manifest project/version does not match the current manufacturing profile")
    pro, sch, pcb = project_files(root)
    current_sources = {path.name: sha256(path) for path in (pro, sch, pcb)}
    if manifest.get("source_sha256") != current_sources:
        raise RuntimeError("Release source hashes do not match the current KiCad sources; rebuild it before packaging")
    validation = manifest.get("validation", {})
    for kind in ("erc", "drc"):
        counts = validation.get(kind, {})
        if counts.get("error", 0) or counts.get("warning", 0):
            raise RuntimeError(f"Release manifest contains nonzero {kind.upper()} findings")
    if validation.get("warnings_allowed"):
        raise RuntimeError("Release was built with warnings allowed and cannot be formally packaged")
    verify_release_checksums(release)
    bom = release / "assembly/jlcpcb-bom.csv"
    cpl = release / "assembly/jlcpcb-cpl.csv"
    bom_refs = csv_references(bom, "Designator")
    cpl_refs = csv_references(cpl, "Designator")
    if bom_refs != cpl_refs:
        raise RuntimeError(
            f"BOM/CPL fitted reference mismatch: BOM-only={sorted(bom_refs-cpl_refs)}, "
            f"CPL-only={sorted(cpl_refs-bom_refs)}"
        )
    for required in (release / "fabrication/jlcpcb-gerbers.zip", bom, cpl):
        if not required.is_file():
            raise RuntimeError(f"Missing required manufacturing asset: {required}")
    return manifest


def create_release_archive(release: Path, archive: Path) -> Path:
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive.with_name(f".{archive.name}.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as target:
            for path in sorted(release.rglob("*")):
                if path.is_file():
                    target.write(path, Path(release.name) / path.relative_to(release))
        os.replace(temporary, archive)
    finally:
        if temporary.exists():
            temporary.unlink()
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    checksum.write_text(f"{sha256(archive)}  {archive.name}\n", encoding="ascii")
    return checksum


def package_release(root: Path, allow_dirty: bool = False) -> ReleasePackage:
    errors, warnings = validate(root, allow_dirty=allow_dirty)
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        raise RuntimeError("Package preflight failed:\n- " + "\n- ".join(errors))
    profile = load_profile(root)
    release_name, tag = release_identity(profile)
    dist = root / profile["release"]["output_dir"]
    release = dist / release_name
    if not release.exists():
        release = build(root, allow_dirty=allow_dirty, allow_warnings=False)
    verify_release(root, release, profile)
    archive = dist / f"{release_name}.zip"
    checksum = create_release_archive(release, archive)
    return ReleasePackage(release, archive, checksum, tag)


def github_release_command(gh: str, package: ReleasePackage, profile: dict, commit: str) -> list[str]:
    project = profile["project"]
    title = f"{project['title']} hardware v{project['version']} (Rev {project['revision']})"
    notes = (
        f"Hardware revision {project['revision']}, version {project['version']}.\n\n"
        f"Clean manufacturing package built from commit `{commit}` with zero ERC/DRC warnings or errors. "
        "The complete archive includes Gerbers, drill files, JLCPCB BOM/CPL, assembly drawings, "
        "schematic PDF, STEP model, 3D renders, exchange files, validation reports, manifest, and checksums."
    )
    release = package.release_dir
    assets = [
        package.archive,
        package.archive_checksum,
        release / "SHA256SUMS",
        release / "fabrication/jlcpcb-gerbers.zip",
        release / "assembly/jlcpcb-bom.csv",
        release / "assembly/jlcpcb-cpl.csv",
    ]
    return [
        gh,
        "release",
        "create",
        package.tag,
        *(str(path) for path in assets),
        "--draft",
        "--verify-tag",
        "--title",
        title,
        "--notes",
        notes,
    ]


def verify_remote_tag(root: Path, tag: str) -> str:
    head = git(root, "rev-parse", "HEAD")
    local = subprocess.run(
        ["git", "rev-parse", f"{tag}^{{}}"], cwd=root, text=True, capture_output=True, check=False
    )
    if local.returncode or local.stdout.strip() != head:
        raise RuntimeError(f"Local tag {tag} must exist and resolve to current commit {head}")
    remote = run(["git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"], root)
    refs = {}
    for line in remote.stdout.splitlines():
        commit, ref = line.split(maxsplit=1)
        refs[ref] = commit
    remote_commit = refs.get(f"refs/tags/{tag}^{{}}", refs.get(f"refs/tags/{tag}"))
    if remote_commit != head:
        raise RuntimeError(f"Remote tag {tag} is missing or does not resolve to current commit {head}")
    return head


def publish_draft(root: Path, placement_reviewed: bool) -> ReleasePackage:
    if not placement_reviewed:
        raise RuntimeError("Refusing GitHub release: pass --placement-reviewed after checking the JLCPCB preview")
    package = package_release(root)
    gh = shutil.which("gh")
    if not gh:
        raise RuntimeError("GitHub CLI is not available on PATH")
    run([gh, "auth", "status", "-h", "github.com"], root)
    commit = verify_remote_tag(root, package.tag)
    profile = load_profile(root)
    run(github_release_command(gh, package, profile, commit), root)
    return package


def build(root: Path, allow_dirty: bool, allow_warnings: bool, keep_failed: bool = False) -> Path:
    errors, warnings = validate(root, allow_dirty=allow_dirty)
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        raise RuntimeError("Preflight failed:\n- " + "\n- ".join(errors))
    profile = load_profile(root)
    pro, sch, pcb = project_files(root)
    release_name, _tag = release_identity(profile)
    dist = root / profile["release"]["output_dir"]
    dist.mkdir(exist_ok=True)
    final = dist / release_name
    if final.exists():
        raise RuntimeError(f"Release directory already exists: {final}; remove it explicitly before rebuilding")
    temp = Path(tempfile.mkdtemp(prefix=f".{release_name}-", dir=dist))
    try:
        for folder in ("validation", "fabrication/raw", "assembly", "mechanical", "documentation", "exchange"):
            (temp / folder).mkdir(parents=True, exist_ok=True)
        kicad = shutil.which("kicad-cli")
        if not kicad:
            raise RuntimeError("kicad-cli is not available on PATH")
        run([kicad, "sch", "erc", "--output", str(temp / "validation/erc.json"), "--format", "json", "--severity-all", str(sch)], root)
        erc_counts = check_report(temp / "validation/erc.json", "ERC", allow_warnings)
        run([kicad, "pcb", "drc", "--output", str(temp / "validation/drc.json"), "--format", "json", "--all-track-errors", "--schematic-parity", "--severity-all", "--refill-zones", str(pcb)], root)
        drc_counts = check_report(temp / "validation/drc.json", "DRC", allow_warnings)
        run([kicad, "pcb", "export", "gerbers", "--output", str(temp / "fabrication/raw"), "--layers", "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts", "--subtract-soldermask", "--check-zones", str(pcb)], root)
        run([kicad, "pcb", "export", "drill", "--output", str(temp / "fabrication/raw"), "--format", "excellon", "--drill-origin", "absolute", "--excellon-units", "mm", "--excellon-separate-th", "--generate-map", "--map-format", "pdf", "--generate-report", "--report-path", str(temp / "validation/drill-report.txt"), str(pcb)], root)
        run([kicad, "pcb", "export", "pos", "--output", str(temp / "assembly/native-position.csv"), "--side", "both", "--format", "csv", "--units", "mm", "--exclude-dnp", str(pcb)], root)
        run([kicad, "sch", "export", "pdf", "--output", str(temp / "documentation/schematic.pdf"), "--black-and-white", str(sch)], root)
        run([kicad, "pcb", "export", "pdf", "--output", str(temp / "assembly/assembly-front.pdf"), "--layers", "F.Fab,F.Silkscreen", "--common-layers", "Edge.Cuts", "--hide-DNP-footprints-on-fab-layers", "--sketch-pads-on-fab-layers", "--black-and-white", "--mode-single", "--check-zones", str(pcb)], root)
        run([kicad, "pcb", "export", "pdf", "--output", str(temp / "assembly/assembly-back.pdf"), "--layers", "B.Fab,B.Silkscreen", "--common-layers", "Edge.Cuts", "--mirror", "--hide-DNP-footprints-on-fab-layers", "--sketch-pads-on-fab-layers", "--black-and-white", "--mode-single", "--check-zones", str(pcb)], root)
        run([kicad, "pcb", "export", "step", "--output", str(temp / "mechanical/board.step"), "--force", "--no-dnp", str(pcb)], root, required=False)
        run([kicad, "pcb", "render", "--output", str(temp / "mechanical/board-front.png"), "--side", "top", "--quality", "high", str(pcb)], root, required=False)
        run([kicad, "pcb", "render", "--output", str(temp / "mechanical/board-back.png"), "--side", "bottom", "--quality", "high", str(pcb)], root, required=False)
        render_isometric(root, pcb, temp / "mechanical/board-isometric.png", kicad)
        run([kicad, "pcb", "export", "ipcd356", "--output", str(temp / "fabrication/board.d356"), str(pcb)], root)
        run([kicad, "pcb", "export", "ipc2581", "--output", str(temp / "exchange/board-ipc2581.zip"), "--compress", "--version", "C", "--units", "mm", "--bom-col-mfg-pn", "MPN", "--bom-col-mfg", "Manufacturer", "--bom-col-dist-pn", "LCSC Part #", "--bom-col-dist", "LCSC/JLCPCB", "--bom-rev", profile["project"]["revision"], str(pcb)], root, required=False)
        run([kicad, "pcb", "export", "odb", "--output", str(temp / "exchange/board-odb.zip"), "--compression", "zip", "--units", "mm", str(pcb)], root, required=False)
        # Drill-map PDFs remain in fabrication/raw for human review, but JLCPCB's
        # fabrication upload should contain only machine-consumable Gerber/drill files.
        zip_directory(
            temp / "fabrication/raw",
            temp / "fabrication/jlcpcb-gerbers.zip",
            excluded_suffixes=frozenset({".pdf"}),
        )
        parts = parse_parts(sch)
        bom_refs = write_jlc_bom(parts, temp / "assembly/jlcpcb-bom.csv")
        cpl_refs = convert_cpl(temp / "assembly/native-position.csv", temp / "assembly/jlcpcb-cpl.csv")
        if bom_refs != cpl_refs:
            raise RuntimeError(f"BOM/CPL fitted reference mismatch: BOM-only={sorted(bom_refs-cpl_refs)}, CPL-only={sorted(cpl_refs-bom_refs)}")
        for name in ("fabrication-notes.md", "assembly-notes.md", "inspection-checklist.md"):
            shutil.copy2(root / "manufacturing/templates" / name, temp / "documentation" / name)
        manifest = {
            "schema": 1,
            "project": profile["project"],
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "git_commit": git(root, "rev-parse", "HEAD"),
            "git_dirty": bool(git(root, "status", "--porcelain")),
            "kicad_version": run([kicad, "version"], root).stdout.strip(),
            "profile": profile,
            "validation": {"erc": erc_counts, "drc": drc_counts, "warnings_allowed": allow_warnings},
            "fitted_references": sorted(bom_refs, key=natural_key),
            "source_sha256": {path.name: sha256(path) for path in (pro, sch, pcb)},
        }
        (temp / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        files = [path for path in temp.rglob("*") if path.is_file() and path.name != "SHA256SUMS"]
        sums = "\n".join(f"{sha256(path)}  {path.relative_to(temp).as_posix()}" for path in sorted(files)) + "\n"
        (temp / "SHA256SUMS").write_text(sums, encoding="utf-8")
        os.replace(temp, final)
        return final
    except Exception:
        if keep_failed:
            print(f"Failed staging directory retained: {temp}", file=sys.stderr)
        else:
            shutil.rmtree(temp, ignore_errors=True)
        raise


def inspect(root: Path) -> None:
    profile = load_profile(root)
    dist = root / profile["release"]["output_dir"]
    releases = sorted((path for path in dist.glob("*-rev-*-v*") if path.is_dir()), key=lambda path: path.stat().st_mtime)
    if not releases:
        raise RuntimeError("No generated releases found")
    release = releases[-1]
    manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
    print(f"Release: {release.name}")
    print(f"Commit: {manifest['git_commit']} (dirty={manifest['git_dirty']})")
    print(f"KiCad: {manifest['kicad_version']}")
    print(f"Fitted: {', '.join(manifest['fitted_references'])}")
    print(f"Files: {sum(1 for path in release.rglob('*') if path.is_file())}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="hwrelease")
    parser.add_argument("command", choices=("validate", "build", "inspect", "render-docs", "package", "publish"))
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--keep-failed", action="store_true")
    parser.add_argument("--draft", action="store_true", help="Required for publish; public publishing stays manual")
    parser.add_argument("--placement-reviewed", action="store_true")
    args = parser.parse_args()
    root = project_root(args.project_root)
    try:
        if args.command == "validate":
            errors, warnings = validate(root, allow_dirty=args.allow_dirty)
            for warning in warnings:
                print(f"WARNING: {warning}")
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                raise SystemExit(1)
            print("Release metadata and BOM preflight passed")
        elif args.command == "build":
            print(f"Release created: {build(root, args.allow_dirty, args.allow_warnings, args.keep_failed)}")
        elif args.command == "inspect":
            inspect(root)
        elif args.command == "render-docs":
            print(f"README render created: {render_docs(root)}")
        elif args.command == "package":
            package = package_release(root, allow_dirty=args.allow_dirty)
            print(f"Release archive created: {package.archive}")
            print(f"Archive checksum created: {package.archive_checksum}")
        else:
            if not args.draft:
                raise RuntimeError("Publish only creates drafts; pass --draft explicitly")
            package = publish_draft(root, args.placement_reviewed)
            print(f"Draft GitHub release created for {package.tag}")
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
