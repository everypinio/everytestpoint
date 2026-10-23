from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_pcm import build_archive, read_version


class ReleasePackageTests(unittest.TestCase):
    def test_pcm_build_is_reproducible_and_has_expected_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / f"every-test-point-{read_version()}.zip"
            second = Path(temporary) / "second" / first.name
            build_archive(first)
            build_archive(second)

            self.assertEqual(
                hashlib.sha256(first.read_bytes()).digest(),
                hashlib.sha256(second.read_bytes()).digest(),
            )
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
                self.assertIn("metadata.json", names)
                self.assertIn("resources/icon.png", names)
                self.assertIn("plugins/plugin.json", names)
                self.assertIn("plugins/VERSION", names)
                self.assertIn("plugins/LICENSE", names)
                self.assertTrue(
                    all(
                        name.startswith(("plugins/", "resources/"))
                        or name == "metadata.json"
                        for name in names
                    )
                )
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))

                metadata = json.loads(archive.read("metadata.json"))
                version = metadata["versions"][0]
                self.assertEqual(version["version"], read_version())
                self.assertFalse(any(key.startswith("download_") for key in version))


if __name__ == "__main__":
    unittest.main()
