#!/usr/bin/env python3
"""KiCad 10 IPC action entrypoint."""

from __future__ import annotations

import sys
import traceback
import webbrowser
from pathlib import Path

from kipy import KiCad

from everytestpoint.generator import generate_report


def _board_path(board) -> Path:
    name = Path(board.name)
    if name.is_absolute():
        return name
    return Path(board.get_project().path) / name


def main() -> int:
    try:
        kicad = KiCad()
        board = kicad.get_board()
        board.save()

        board_path = _board_path(board).resolve()
        if not board_path.is_file():
            raise FileNotFoundError(f"The open board has not been saved to disk: {board_path}")

        cli = Path(kicad.get_kicad_binary_path("kicad-cli"))
        output_dir = board_path.parent / f"{board_path.stem}-testpoints"
        result = generate_report(board_path, output_dir=output_dir, kicad_cli=cli)

        print(
            f"Every Test Point: generated {result.testpoint_count} test points in "
            f"{result.index_path}"
        )
        webbrowser.open(result.index_path.as_uri())
        return 0
    except Exception as exc:  # KiCad reports stdout/stderr in the plugin warning UI.
        print(f"Every Test Point failed: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
