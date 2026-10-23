from __future__ import annotations

import json
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise AssertionError(f"Not a PNG file: {path}")
    return struct.unpack(">II", data[16:24])


class PluginManifestTests(unittest.TestCase):
    def test_pcm_and_plugin_identity_are_release_consistent(self):
        manifest = json.loads((ROOT / "plugin" / "plugin.json").read_text(encoding="utf-8"))
        metadata = json.loads((ROOT / "pcm" / "metadata.json").read_text(encoding="utf-8"))
        version = (ROOT / "plugin" / "VERSION").read_text(encoding="utf-8").strip()

        expected_identifier = "com.github.everypinio.everytestpoint"
        self.assertEqual(manifest["identifier"], expected_identifier)
        self.assertEqual(metadata["identifier"], expected_identifier)
        self.assertEqual(metadata["versions"][0]["version"], version)
        self.assertEqual(metadata["versions"][0]["runtime"], "ipc")
        self.assertEqual(manifest["runtime"]["min_version"], "3.10")

        self.assertEqual(png_size(ROOT / "pcm" / "icon.png"), (64, 64))

    def test_toolbar_action_has_icons_for_both_themes(self):
        manifest = json.loads((ROOT / "plugin" / "plugin.json").read_text(encoding="utf-8"))
        action = manifest["actions"][0]

        self.assertTrue(action["show-button"])
        expected = [
            "icons/everypin-mark-24.png",
            "icons/everypin-mark-48.png",
        ]
        self.assertEqual(action["icons-light"], expected)
        self.assertEqual(action["icons-dark"], expected)

        for relative_path, size in zip(expected, (24, 48), strict=True):
            icon_path = ROOT / "plugin" / relative_path
            self.assertTrue(icon_path.is_file(), icon_path)
            self.assertEqual(png_size(icon_path), (size, size))


if __name__ == "__main__":
    unittest.main()
