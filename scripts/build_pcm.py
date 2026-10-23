"""Build a reproducible KiCad PCM installation archive."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "every-test-point"
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def read_version() -> str:
    """Return the package version from the single source of truth."""

    return (ROOT / "plugin" / "VERSION").read_text(encoding="utf-8").strip()


def package_metadata() -> bytes:
    """Return archive metadata without repository-only download fields."""

    metadata = json.loads((ROOT / "pcm" / "metadata.json").read_text(encoding="utf-8"))
    metadata["versions"][0]["version"] = read_version()
    for version in metadata["versions"]:
        for key in ("download_url", "download_sha256", "download_size", "install_size"):
            version.pop(key, None)
    return (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def archive_entries() -> list[tuple[str, bytes]]:
    """Collect the exact files allowed in a KiCad plugin package."""

    entries: list[tuple[str, bytes]] = []
    for path in sorted((ROOT / "plugin").rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        relative = path.relative_to(ROOT / "plugin").as_posix()
        entries.append((f"plugins/{relative}", path.read_bytes()))
    entries.extend(
        [
            ("plugins/LICENSE", (ROOT / "LICENSE").read_bytes()),
            ("resources/icon.png", (ROOT / "pcm" / "icon.png").read_bytes()),
            ("metadata.json", package_metadata()),
        ]
    )
    return sorted(entries)


def build_archive(destination: Path | None = None) -> Path:
    """Build the package and return its path."""

    version = read_version()
    destination = destination or ROOT / "dist" / f"{PACKAGE_NAME}-{version}.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(destination, "w") as archive:
        for name, contents in archive_entries():
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, contents, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return destination


def main() -> int:
    destination = build_archive()
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
