"""Compare parser pad transforms with KiCad's legacy pcbnew bindings.

Run with KiCad's bundled Python. This is a development diagnostic, not part of the plugin.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from plugin.everytestpoint.pcb import _absolute_pad_position, _at  # noqa: E402
from plugin.everytestpoint.sexpr import children, root_forms  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    args = parser.parse_args()

    source = args.board.read_text(encoding="utf-8")
    expected: dict[str, tuple[tuple[float, float], tuple, tuple, str]] = {}
    for footprint in root_forms(source, {"footprint"}):
        for pad in children(footprint, "pad"):
            uuid_form = next(
                (item for item in pad[1:] if isinstance(item, list) and item and item[0] == "uuid"),
                None,
            )
            if uuid_form and len(uuid_form) > 1:
                layer = next(
                    (item for item in footprint[1:] if isinstance(item, list) and item and item[0] == "layer"),
                    None,
                )
                expected[str(uuid_form[1])] = (
                    _absolute_pad_position(footprint, pad),
                    _at(footprint),
                    _at(pad),
                    str(layer[1]) if layer and len(layer) > 1 else "",
                )

    board = pcbnew.LoadBoard(str(args.board))
    checked = 0
    worst = 0.0
    failures: list[tuple[float, str]] = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            number = str(pad.GetNumber())
            parsed_item = expected.get(pad.m_Uuid.AsString())
            if parsed_item is None:
                continue
            parsed, fp_at, pad_at, layer = parsed_item
            actual = tuple(pcbnew.ToMM(pad.GetCenter()))
            error = max(abs(parsed[0] - actual[0]), abs(parsed[1] - actual[1]))
            worst = max(worst, error)
            checked += 1
            if error > 0.0001:
                failures.append((
                    error,
                    f"{footprint.GetReferenceAsString()}.{number}: layer={layer}, "
                    f"fp_at={fp_at}, pad_at={pad_at}, parsed={parsed}, "
                    f"KiCad={actual}, error={error}",
                ))

    print(f"Checked {checked} pads; worst coordinate error: {worst:.9f} mm")
    for _, failure in sorted(failures, reverse=True)[:30]:
        print(failure)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
