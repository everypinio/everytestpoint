from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    from PIL import Image, ImageDraw
except ImportError:  # Pillow is installed by KiCad from plugin/requirements.txt.
    Image = None
    ImageDraw = None

from plugin.everytestpoint.pcb import Bounds
from plugin.everytestpoint.render import RenderGeometry, measure_board_geometry, render_board


@unittest.skipUnless(Image is not None, "Pillow is not installed")
class RenderGeometryTests(unittest.TestCase):
    def test_finds_board_surface_despite_shadow_and_overhanging_model(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "render.png"
            image = Image.new("RGBA", (120, 140), (0, 0, 0, 75))
            draw = ImageDraw.Draw(image)
            draw.rectangle((10, 20, 109, 119), fill=(70, 40, 90, 255))
            draw.rectangle((50, 0, 69, 19), fill=(180, 180, 180, 255))
            image.save(path)

            geometry = measure_board_geometry(path, Bounds(0, 0, 100, 100))

        self.assertEqual(geometry.image_width, 120)
        self.assertEqual(geometry.image_height, 140)
        self.assertEqual(geometry.board_left, 10)
        self.assertEqual(geometry.board_top, 20)
        self.assertEqual(geometry.board_width, 100)
        self.assertEqual(geometry.board_height, 100)

    def test_ignores_wide_model_overhanging_the_board(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "render.png"
            image = Image.new("RGBA", (240, 150), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rectangle((20, 40, 219, 139), fill=(70, 40, 90, 255))
            # The overhang covers most columns, so its taller span is more
            # common than the true board height.
            draw.rectangle((50, 0, 189, 39), fill=(180, 180, 180, 255))
            image.save(path)

            geometry = measure_board_geometry(path, Bounds(0, 0, 200, 100))

        self.assertEqual(geometry.board_left, 20)
        self.assertEqual(geometry.board_top, 40)
        self.assertEqual(geometry.board_width, 200)
        self.assertEqual(geometry.board_height, 100)

    def test_render_uses_colors_from_board_stackup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            board_path = root / "fixture.kicad_pcb"
            board_path.write_text("(kicad_pcb)", encoding="utf-8")
            commands = []

            def fake_run(command, **kwargs):
                commands.append(command)
                output = Path(command[command.index("--output") + 1])
                output.write_bytes(b"render")
                return SimpleNamespace(returncode=0, stderr="", stdout="")

            def fake_geometry(path, bounds):
                return RenderGeometry(path, 200, 100, 0, 0, 200, 100)

            with (
                patch("plugin.everytestpoint.render.subprocess.run", side_effect=fake_run),
                patch("plugin.everytestpoint.render._trim_transparency"),
                patch("plugin.everytestpoint.render.measure_board_geometry", side_effect=fake_geometry),
            ):
                render_board(
                    board_path,
                    root / "images",
                    Bounds(0, 0, 200, 100),
                    kicad_cli=board_path,
                )

        self.assertEqual(len(commands), 2)
        for command in commands:
            self.assertIn("--use-board-stackup-colors", command)


if __name__ == "__main__":
    unittest.main()
