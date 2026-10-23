"""High-level report generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .pcb import extract_board
from .render import render_board
from .report import write_csv, write_dft_csv, write_html, write_jigsapp_csv, write_json


@dataclass(frozen=True)
class GenerationResult:
    output_dir: Path
    index_path: Path
    testpoint_count: int
    render_error: str | None


def generate_report(
    board_path: str | Path,
    output_dir: str | Path | None = None,
    kicad_cli: str | Path | None = None,
    render: bool = True,
) -> GenerationResult:
    board_path = Path(board_path).resolve()
    board = extract_board(board_path)
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    destination = Path(output_dir) if output_dir else board_path.parent / f"{board_path.stem}-testpoints"
    destination = destination.resolve()
    images = destination / "images"
    destination.mkdir(parents=True, exist_ok=True)

    render_error: str | None = None
    renders = {}
    if render:
        try:
            renders = render_board(board_path, images, board.bounds, kicad_cli=kicad_cli)
        except Exception as exc:
            render_error = str(exc)
    else:
        render_error = "Rendering was disabled"

    write_csv(board, destination / "testpoints.csv")
    write_dft_csv(board, destination / "dft-distances.csv")
    write_jigsapp_csv(board, destination / "jigsapp-testpoints.csv")
    write_json(
        board,
        destination / "testpoints.json",
        render_error=render_error,
        render_geometry=renders,
        generated_at=generated_at,
    )
    index_path = destination / "index.html"
    write_html(
        board,
        index_path,
        renders_available=bool(renders),
        render_error=render_error,
        render_geometry=renders,
        generated_at=generated_at,
    )
    return GenerationResult(destination, index_path, len(board.testpoints), render_error)
