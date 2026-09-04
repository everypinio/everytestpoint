"""Standalone command-line interface for development and CI."""

from __future__ import annotations

import argparse
from pathlib import Path

from .generator import generate_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an interactive KiCad test-point map")
    parser.add_argument("board", type=Path, help="Input .kicad_pcb file")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--kicad-cli", type=Path)
    parser.add_argument("--no-render", action="store_true")
    args = parser.parse_args()
    result = generate_report(
        args.board,
        output_dir=args.output_dir,
        kicad_cli=args.kicad_cli,
        render=not args.no_render,
    )
    print(f"Generated {result.testpoint_count} test points: {result.index_path}")
    if result.render_error:
        print(f"Render note: {result.render_error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
