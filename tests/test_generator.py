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
            result = generate_report(board_path, output_dir=root / "report", render=False)

            self.assertEqual(result.testpoint_count, 3)
            self.assertTrue(result.index_path.is_file())
            self.assertTrue((result.output_dir / "testpoints.csv").is_file())
            self.assertTrue((result.output_dir / "jigsapp-testpoints.csv").is_file())
            payload = json.loads((result.output_dir / "testpoints.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["stats"]["testpoints"], 3)
            html = result.index_path.read_text(encoding="utf-8")
            self.assertIn("Every Test Point", html)
            self.assertIn("J1.1", html)
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
