from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from plugin.everytestpoint.generator import generate_report
from tests.test_pcb import BOARD


class GeneratorTests(unittest.TestCase):
    def test_generates_self_contained_exports_without_renderer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            board_path = root / "fixture.kicad_pcb"
            board_path.write_text(BOARD, encoding="utf-8")
            board_path.with_suffix(".kicad_pro").write_text(
                json.dumps({"text_variables": {"REVISION": "Rev. 2.4"}}), encoding="utf-8"
            )
            result = generate_report(board_path, output_dir=root / "report", render=False)

            self.assertEqual(result.testpoint_count, 3)
            self.assertTrue(result.index_path.is_file())
            self.assertTrue((result.output_dir / "testpoints.csv").is_file())
            self.assertTrue((result.output_dir / "jigsapp-testpoints.csv").is_file())
            self.assertTrue((result.output_dir / "dft-distances.csv").is_file())
            payload = json.loads((result.output_dir / "testpoints.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["stats"]["testpoints"], 3)
            self.assertEqual(payload["revision"], "2.4")
            self.assertRegex(payload["generated_at"], r"^\d{4}-\d{2}-\d{2}T")
            self.assertEqual(len(payload["dft_pairs"]), 2)
            html = result.index_path.read_text(encoding="utf-8")
            self.assertIn('class="brand-logo"', html)
            self.assertIn('aria-label="Everypin"', html)
            self.assertIn('fill="white"', html)
            self.assertIn('font-family:"Golos Text"', html)
            self.assertIn("data:font/ttf;base64,", html)
            self.assertIn('class="report-kind">Test point report</span>', html)
            self.assertIn("Revision <b>2.4</b>", html)
            self.assertRegex(html, r"Date <b>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}</b>")
            self.assertIn("J1.1", html)
            self.assertIn("DFT spacing", html)
            if node := shutil.which("node"):
                script = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
                self.assertIsNotNone(script)
                checked = subprocess.run(
                    [node, "--check", "-"],
                    input=script.group(1),
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(checked.returncode, 0, checked.stderr)


if __name__ == "__main__":
    unittest.main()
