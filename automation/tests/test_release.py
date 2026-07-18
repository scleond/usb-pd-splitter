import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from hwrelease.cli import (
    ReleasePackage,
    create_release_archive,
    documentation_render_errors,
    documentation_render_paths,
    expected_render_metadata,
    github_release_command,
    isometric_render_command,
    release_identity,
    sha256,
    convert_cpl,
    natural_key,
    parse_parts,
)


ROOT = Path(__file__).resolve().parents[2]


class ReleaseTests(unittest.TestCase):
    def test_natural_sort(self):
        self.assertEqual(sorted(["J10", "J2", "J1"], key=natural_key), ["J1", "J2", "J10"])

    def test_project_parts_are_fully_sourced(self):
        parts = parse_parts(ROOT / "usb-pd-splitter.kicad_sch")
        self.assertEqual([part.reference for part in parts], ["J1", "J2", "J3", "R1", "R2"])
        fitted = [part for part in parts if not part.dnp]
        self.assertTrue(all(part.fields.get("Manufacturer") for part in fitted))
        self.assertTrue(all(part.fields.get("MPN") for part in fitted))
        self.assertTrue(all(part.fields.get("LCSC Part #") for part in fitted))

    def test_cpl_uses_jlc_headers_and_normalized_rotation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "native.csv"
            target = Path(directory) / "jlc.csv"
            source.write_text("Ref,PosX,PosY,Rot,Side\nJ1,10,-20,-90,top\n", encoding="utf-8")
            self.assertEqual(convert_cpl(source, target), {"J1"})
            with target.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row, {"Designator": "J1", "Mid X": "10", "Mid Y": "-20", "Rotation": "270", "Layer": "Top"})

    def test_isometric_render_command_is_fixed_and_raytraced(self):
        command = isometric_render_command("kicad-cli", Path("board.kicad_pcb"), Path("image.png"))
        self.assertEqual(command[:5], ["kicad-cli", "pcb", "render", "--output", "image.png"])
        self.assertIn("high", command)
        self.assertIn("--floor", command)
        self.assertIn("--perspective", command)
        self.assertEqual(command[command.index("--rotate") + 1], "-45,0,45")

    def test_documentation_render_path_and_freshness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pro = root / "board.kicad_pro"
            pcb = root / "board.kicad_pcb"
            pro.write_text("project", encoding="utf-8")
            pcb.write_text("board-v1", encoding="utf-8")
            profile = {"project": {"slug": "test-board", "kicad_major": 10}}
            image, metadata_path = documentation_render_paths(root, "test-board")
            self.assertEqual(image.relative_to(root).as_posix(), "docs/assets/test-board-isometric.png")
            image.parent.mkdir(parents=True)
            image.write_bytes(b"rendered image")
            metadata = expected_render_metadata(root, profile, pro, pcb)
            metadata["image_sha256"] = sha256(image)
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            self.assertEqual(documentation_render_errors(root, profile, pro, pcb), [])
            pcb.write_text("board-v2", encoding="utf-8")
            self.assertIn("stale", documentation_render_errors(root, profile, pro, pcb)[0])

    def test_release_identity_uses_hardware_tag_prefix(self):
        profile = {
            "project": {"slug": "widget", "revision": "B", "version": "2.3.4"},
            "release": {"tag_prefix": "hardware-v"},
        }
        self.assertEqual(release_identity(profile), ("widget-rev-b-v2.3.4", "hardware-v2.3.4"))

    def test_release_archive_contains_root_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root / "widget-rev-a-v1.0.0"
            release.mkdir()
            (release / "manifest.json").write_text("{}", encoding="utf-8")
            archive = root / "widget-rev-a-v1.0.0.zip"
            checksum = create_release_archive(release, archive)
            self.assertTrue(archive.is_file())
            self.assertEqual(checksum.read_text(encoding="ascii"), f"{sha256(archive)}  {archive.name}\n")
            with zipfile.ZipFile(archive) as handle:
                self.assertEqual(handle.namelist(), ["widget-rev-a-v1.0.0/manifest.json"])

    def test_github_release_command_is_always_draft_and_verifies_tag(self):
        root = Path("dist/widget-rev-a-v1.0.0")
        package = ReleasePackage(root, Path("dist/widget.zip"), Path("dist/widget.zip.sha256"), "hardware-v1.0.0")
        profile = {
            "project": {"slug": "widget", "title": "Widget", "revision": "A", "version": "1.0.0"},
            "release": {"tag_prefix": "hardware-v"},
        }
        command = github_release_command("gh", package, profile, "abc123")
        self.assertEqual(command[:4], ["gh", "release", "create", "hardware-v1.0.0"])
        self.assertIn("--draft", command)
        self.assertIn("--verify-tag", command)
        self.assertNotIn("--latest", command)


if __name__ == "__main__":
    unittest.main()
