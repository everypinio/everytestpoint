"""Generate KiCad repository metadata and a checksum for a release archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from validate_release import ValidationError, validate_schema

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    version = (ROOT / "plugin" / "VERSION").read_text(encoding="utf-8").strip()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "dist" / f"every-test-point-{version}.zip",
    )
    parser.add_argument("--download-url", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "metadata.repository.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    archive = args.archive.resolve()
    if not archive.is_file():
        print(f"archive not found: {archive}", file=sys.stderr)
        return 1
    parsed_url = urlparse(args.download_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        print("download URL must be a public HTTPS URL", file=sys.stderr)
        return 1

    contents = archive.read_bytes()
    digest = hashlib.sha256(contents).hexdigest()
    with zipfile.ZipFile(archive) as package:
        install_size = sum(item.file_size for item in package.infolist())
        metadata = json.loads(package.read("metadata.json"))

    version = metadata["versions"][0]
    version.update(
        {
            "download_url": args.download_url,
            "download_sha256": digest,
            "download_size": len(contents),
            "install_size": install_size,
        }
    )
    try:
        validate_schema(metadata, "pcm")
    except ValidationError as error:
        print(f"repository metadata validation failed: {error}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(args.output)
    print(checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
