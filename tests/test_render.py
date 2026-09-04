from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:  # Pillow is installed by KiCad from plugin/requirements.txt.
    Image = None
    ImageDraw = None

from plugin.everytestpoint.pcb import Bounds
from plugin.everytestpoint.render import measure_board_geometry


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


if __name__ == "__main__":
    unittest.main()
