"""Build the KiCad PCM installation archive."""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"


def main() -> int:
    destination = ROOT / "dist" / f"every-test-point-{VERSION}.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="every-test-point-") as temporary:
        stage = Path(temporary)
        plugins = stage / "plugins"
        shutil.copytree(ROOT / "plugin", plugins)
        metadata = json.loads((ROOT / "pcm" / "metadata.json").read_text(encoding="utf-8"))
        (stage / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                    archive.write(path, path.relative_to(stage).as_posix())
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
