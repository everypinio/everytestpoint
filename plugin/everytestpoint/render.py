"""Generate and trim realistic KiCad 3D board renders."""

from __future__ import annotations

import shutil
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median

from .pcb import Bounds


@dataclass(frozen=True)
class RenderGeometry:
    path: Path
    image_width: int
    image_height: int
    board_left: int
    board_top: int
    board_width: int
    board_height: int

    def to_dict(self) -> dict:
        values = asdict(self)
        values.pop("path")
        return values


def find_kicad_cli(explicit: str | Path | None = None) -> Path:
    if explicit:
        candidate = Path(explicit)
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"kicad-cli not found: {candidate}")
    located = shutil.which("kicad-cli") or shutil.which("kicad-cli.exe")
    if located:
        return Path(located)
    common = [
        Path(r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"),
        Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"),
        Path("/usr/bin/kicad-cli"),
        Path("/usr/local/bin/kicad-cli"),
    ]
    for candidate in common:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("kicad-cli was not found")


def _dimensions(bounds: Bounds, long_side: int = 1800) -> tuple[int, int]:
    aspect = bounds.width / bounds.height
    if aspect >= 1:
        return long_side, max(720, round(long_side / aspect))
    return max(720, round(long_side * aspect)), long_side


def _trim_transparency(path: Path) -> None:
    from PIL import Image

    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        alpha_box = rgba.getchannel("A").getbbox()
        if not alpha_box:
            raise RuntimeError(f"KiCad produced an empty render: {path}")
        cropped = rgba.crop(alpha_box)
        cropped.save(path, optimize=True)


def measure_board_geometry(path: Path, bounds: Bounds) -> RenderGeometry:
    """Locate the opaque board surface within an orthographic KiCad render.

    High-quality KiCad renders include translucent shadows and may include 3D
    models beyond Edge.Cuts.  The board itself is fully opaque.  Long repeated
    opaque row/column spans therefore reveal the actual board rectangle and
    give the HTML overlay an exact image-to-millimetre transform.
    """
    from PIL import Image

    with Image.open(path) as image:
        alpha = image.convert("RGBA").getchannel("A").point(
            lambda value: 255 if value >= 250 else 0
        )
        image_width, image_height = alpha.size
        row_boxes = []
        column_boxes = []
        for y in range(image_height):
            box = alpha.crop((0, y, image_width, y + 1)).getbbox()
            if box:
                row_boxes.append((box[0], box[2]))
        for x in range(image_width):
            box = alpha.crop((x, 0, x + 1, image_height)).getbbox()
            if box:
                column_boxes.append((box[1], box[3]))

    if not row_boxes or not column_boxes:
        raise RuntimeError(f"Could not locate the board surface in {path}")

    # A connector or another 3D model can overhang the board across most of one
    # axis.  In that case the most common opaque column/row span belongs to the
    # model, not to the board (for example a wide connector above the top edge).
    # Select the width/height pair whose pixel-per-millimetre scales agree.
    width_candidates = Counter(right - left for left, right in row_boxes).most_common(16)
    height_candidates = Counter(bottom - top for top, bottom in column_boxes).most_common(16)
    candidate_pairs = []
    for board_width, width_support in width_candidates:
        for board_height, height_support in height_candidates:
            x_scale = board_width / bounds.width
            y_scale = board_height / bounds.height
            mismatch = abs(x_scale - y_scale) / max(x_scale, y_scale)
            candidate_pairs.append(
                (mismatch, -(width_support + height_support), board_width, board_height)
            )
    mismatch, _, board_width, board_height = min(candidate_pairs)
    width_rows = [box for box in row_boxes if box[1] - box[0] == board_width]
    height_columns = [box for box in column_boxes if box[1] - box[0] == board_height]
    board_left = round(median(left for left, _ in width_rows))
    board_top = round(median(top for top, _ in height_columns))

    x_scale = board_width / bounds.width
    y_scale = board_height / bounds.height
    if mismatch > 0.02:
        raise RuntimeError(
            f"Board render calibration is inconsistent: {x_scale:.3f} vs {y_scale:.3f} px/mm"
        )

    return RenderGeometry(
        path=path,
        image_width=image_width,
        image_height=image_height,
        board_left=board_left,
        board_top=board_top,
        board_width=board_width,
        board_height=board_height,
    )


def render_board(
    board_path: str | Path,
    output_dir: str | Path,
    bounds: Bounds,
    kicad_cli: str | Path | None = None,
) -> dict[str, RenderGeometry]:
    cli = find_kicad_cli(kicad_cli)
    board_path = Path(board_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    width, height = _dimensions(bounds)
    result: dict[str, RenderGeometry] = {}

    for side in ("top", "bottom"):
        output = output_dir / f"{side}.png"
        command = [
            str(cli),
            "pcb",
            "render",
            "--output",
            str(output),
            "--width",
            str(width),
            "--height",
            str(height),
            "--side",
            side,
            "--background",
            "transparent",
            "--quality",
            "high",
            "--preset",
            "follow_plot_settings",
            "--use-board-stackup-colors",
            str(board_path),
        ]
        completed = subprocess.run(
            command,
            cwd=board_path.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"KiCad {side} render failed ({completed.returncode}): {detail}")
        if not output.is_file():
            raise RuntimeError(f"KiCad did not create {output}")
        _trim_transparency(output)
        result[side] = measure_board_geometry(output, bounds)
    return result
