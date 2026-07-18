import csv
import json
import tempfile
import unittest
from pathlib import Path

from hwrelease.cli import (
    documentation_render_errors,
    documentation_render_paths,
    expected_render_metadata,
    isometric_render_command,
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


if __name__ == "__main__":
    unittest.main()
