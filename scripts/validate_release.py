"""Validate source manifests and a built KiCad PCM archive."""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IDENTIFIER = "com.github.everypinio.everytestpoint"
SCHEMAS = {
    "pcm": (
        "pcm.v2.schema.json",
        "https://go.kicad.org/pcm/schemas/v2",
    ),
    "api": (
        "api.v1.schema.json",
        "https://go.kicad.org/api/schemas/v1",
    ),
}


class ValidationError(RuntimeError):
    """Raised when release inputs are inconsistent."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValidationError("PCM icon is not a PNG file")
    return struct.unpack(">II", data[16:24])


def schema_candidates(filename: str) -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get("KICAD_SCHEMA_DIR")
    if configured:
        candidates.append(Path(configured) / filename)
    candidates.extend(
        [
            Path("C:/Program Files/KiCad/10.0/share/kicad/schemas") / filename,
            Path("/usr/share/kicad/schemas") / filename,
            Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/schemas") / filename,
        ]
    )
    return candidates


def load_schema(filename: str, url: str) -> dict[str, Any]:
    for candidate in schema_candidates(filename):
        if candidate.is_file():
            return load_json(candidate)
    with urllib.request.urlopen(url, timeout=20) as response:  # noqa: S310 - fixed KiCad URL
        return json.load(response)


def validate_schema(instance: dict[str, Any], schema_key: str) -> None:
    try:
        import jsonschema
    except ImportError as error:
        raise ValidationError(
            "jsonschema is required; install requirements-dev.txt"
        ) from error
    filename, url = SCHEMAS[schema_key]
    try:
        schema = load_schema(filename, url)
    except (OSError, ValueError) as error:
        raise ValidationError(f"Could not load KiCad schema {url}: {error}") from error
    try:
        jsonschema.Draft7Validator(schema).validate(instance)
    except jsonschema.ValidationError as error:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValidationError(f"{schema_key} schema error at {location}: {error.message}") from error


def validate_sources(tag: str | None = None) -> tuple[str, dict[str, Any], dict[str, Any]]:
    version = (ROOT / "plugin" / "VERSION").read_text(encoding="utf-8").strip()
    pcm = load_json(ROOT / "pcm" / "metadata.json")
    plugin = load_json(ROOT / "plugin" / "plugin.json")

    if not version or any(not part.isdigit() for part in version.split(".")):
        raise ValidationError(f"Invalid VERSION value: {version!r}")
    if tag and tag != f"v{version}":
        raise ValidationError(f"Git tag {tag!r} does not match VERSION v{version}")
    if pcm.get("identifier") != EXPECTED_IDENTIFIER:
        raise ValidationError("PCM identifier does not match the permanent public identifier")
    if plugin.get("identifier") != EXPECTED_IDENTIFIER:
        raise ValidationError("plugin.json identifier does not match PCM metadata")
    if pcm["versions"][0]["version"] != version:
        raise ValidationError("pcm/metadata.json version does not match plugin/VERSION")
    if len(pcm["versions"]) != 1:
        raise ValidationError("Package metadata must contain exactly one version")
    if pcm["versions"][0].get("runtime") != "ipc":
        raise ValidationError("PCM metadata must declare the ipc runtime")
    if tag and pcm["versions"][0].get("status") not in {"testing", "stable"}:
        raise ValidationError("Tagged releases must have PCM status testing or stable")
    if any(key.startswith("download_") for key in pcm["versions"][0]):
        raise ValidationError("Archive metadata must not contain repository-only download fields")

    repository = "https://github.com/everypinio/everytestpoint"
    resources = pcm.get("resources", {})
    if resources.get("repository") != repository:
        raise ValidationError("PCM repository URL is missing or incorrect")
    if resources.get("issues") != f"{repository}/issues":
        raise ValidationError("PCM issue tracker URL is missing or incorrect")

    for action in plugin.get("actions", []):
        entrypoint = ROOT / "plugin" / action["entrypoint"]
        if not entrypoint.is_file():
            raise ValidationError(f"Missing action entrypoint: {entrypoint}")
        for key in ("icons-light", "icons-dark"):
            for relative in action.get(key, []):
                if not (ROOT / "plugin" / relative).is_file():
                    raise ValidationError(f"Missing action icon: {relative}")

    validate_schema(pcm, "pcm")
    validate_schema(plugin, "api")
    return version, pcm, plugin


def validate_archive(path: Path, version: str) -> None:
    if not path.is_file():
        raise ValidationError(f"Archive does not exist: {path}")
    expected_name = f"every-test-point-{version}.zip"
    if path.name != expected_name:
        raise ValidationError(f"Archive must be named {expected_name}")

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValidationError("Archive contains duplicate paths")
        if "metadata.json" not in names or "resources/icon.png" not in names:
            raise ValidationError("Archive is missing metadata.json or resources/icon.png")
        if "plugins/plugin.json" not in names or "plugins/VERSION" not in names:
            raise ValidationError("Archive is missing plugin.json or VERSION")
        if any(
            not (name.startswith("plugins/") or name.startswith("resources/") or name == "metadata.json")
            for name in names
        ):
            raise ValidationError("Archive contains files outside the PCM layout")
        if any("__pycache__" in name or name.endswith((".pyc", ".pyo")) for name in names):
            raise ValidationError("Archive contains Python cache files")

        metadata = json.loads(archive.read("metadata.json"))
        if metadata["identifier"] != EXPECTED_IDENTIFIER:
            raise ValidationError("Archive metadata identifier is incorrect")
        if metadata["versions"][0]["version"] != version:
            raise ValidationError("Archive metadata version is incorrect")
        if archive.read("plugins/VERSION").decode("utf-8").strip() != version:
            raise ValidationError("Archive VERSION is incorrect")
        if png_size(archive.read("resources/icon.png")) != (64, 64):
            raise ValidationError("PCM icon must be exactly 64x64 pixels")

        archived_plugin = json.loads(archive.read("plugins/plugin.json"))
        if archived_plugin["identifier"] != metadata["identifier"]:
            raise ValidationError("Archived plugin and PCM identifiers do not match")
        validate_schema(metadata, "pcm")
        validate_schema(archived_plugin, "api")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, help="PCM archive to validate")
    parser.add_argument("--tag", help="Release tag, for example v0.2.3")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        version, _, _ = validate_sources(args.tag)
        archive = args.archive or ROOT / "dist" / f"every-test-point-{version}.zip"
        validate_archive(archive.resolve(), version)
    except (ValidationError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(f"release validation failed: {error}", file=sys.stderr)
        return 1
    print(f"release validation passed: v{version} ({archive})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
