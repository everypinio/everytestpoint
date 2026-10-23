"""Extract board bounds and test points from a modern KiCad PCB file."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .sexpr import SExprError, child, children, root_forms

_TP_REFERENCE = re.compile(r"^TP(?:\d+|[_-].+|$)", re.IGNORECASE)
_GROUND = re.compile(r"(^|[/_+.-])(GND|AGND|DGND|PGND)([/_+.-]|$)", re.IGNORECASE)
_POWER = re.compile(
    r"(^|[/_+.-])(?:VCC|VDD|VBAT|VIN|VOUT|[+-]?\d+(?:V\d+|V)?)([/_+.-]|$)", re.IGNORECASE
)
_DEBUG = re.compile(r"JTAG|SWD|UART|DEBUG|RESET|BOOT|TCK|TMS|TDI|TDO|TRST", re.IGNORECASE)
_ANALOG = re.compile(r"ADC|DAC|ANALOG|SENSE|TEMP|CURRENT|VREF", re.IGNORECASE)


@dataclass(frozen=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    def to_dict(self) -> dict:
        return {**asdict(self), "width": self.width, "height": self.height}


@dataclass(frozen=True)
class TestPoint:
    id: str
    source_ref: str
    source_pad: str
    value: str
    net: str
    side: str
    footprint_side: str
    x_mm: float
    y_mm: float
    absolute_x_mm: float
    absolute_y_mm: float
    top_left_x_mm: float
    top_left_y_mm: float
    pad_type: str
    category: str
    selection_reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BoardData:
    name: str
    source: str
    revision: str
    bounds: Bounds
    aux_origin: tuple[float, float] | None
    testpoints: tuple[TestPoint, ...]
    total_nets: int

    @property
    def covered_nets(self) -> int:
        return len({point.net for point in self.testpoints if point.net})

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "source": self.source,
            "revision": self.revision,
            "bounds": self.bounds.to_dict(),
            "aux_origin": list(self.aux_origin) if self.aux_origin else None,
            "testpoints": [point.to_dict() for point in self.testpoints],
            "stats": {
                "testpoints": len(self.testpoints),
                "covered_nets": self.covered_nets,
                "total_nets": self.total_nets,
            },
        }


def _number(value: str) -> float:
    return float(value)


def _at(expr: list) -> tuple[float, float, float]:
    item = child(expr, "at")
    if not item or len(item) < 3:
        return 0.0, 0.0, 0.0
    return _number(item[1]), _number(item[2]), _number(item[3]) if len(item) > 3 else 0.0


def _property_map(footprint: list) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in children(footprint, "property"):
        if len(item) >= 3:
            result[str(item[1])] = str(item[2])
    return result


def _has_testpoint_property(pad: list) -> bool:
    prop = child(pad, "property")
    return bool(prop and any(str(value).lower() == "pad_prop_testpoint" for value in prop[1:]))


def _pad_layers(pad: list) -> tuple[str, ...]:
    item = child(pad, "layers")
    return tuple(str(value) for value in item[1:]) if item else ()


def _absolute_pad_position(footprint: list, pad: list) -> tuple[float, float]:
    fx, fy, angle = _at(footprint)
    px, py, _ = _at(pad)
    # KiCad board coordinates use X right / Y down, so a positive footprint
    # angle has the opposite sign from the conventional mathematical rotation.
    # Pad coordinates in a .kicad_pcb file are already mirrored for footprints
    # placed on B.Cu, so no additional side-dependent reflection is needed.
    radians = math.radians(-angle)
    return (
        fx + px * math.cos(radians) - py * math.sin(radians),
        fy + px * math.sin(radians) + py * math.cos(radians),
    )


def _side(footprint: list, pad: list) -> tuple[str, str]:
    fp_layer = child(footprint, "layer")
    footprint_side = "bottom" if fp_layer and len(fp_layer) > 1 and fp_layer[1] == "B.Cu" else "top"
    layers = _pad_layers(pad)
    pad_kind = str(pad[2]) if len(pad) > 2 else ""
    if pad_kind in {"thru_hole", "np_thru_hole"} or "*.Cu" in layers or (
        "F.Cu" in layers and "B.Cu" in layers
    ):
        return "both", footprint_side
    if "B.Cu" in layers:
        return "bottom", footprint_side
    if "F.Cu" in layers:
        return "top", footprint_side
    return footprint_side, footprint_side


def _net(pad: list) -> str:
    item = child(pad, "net")
    return str(item[-1]) if item and len(item) > 1 else ""


def _category(net: str) -> str:
    if _GROUND.search(net):
        return "Ground"
    if _POWER.search(net):
        return "Power"
    if _DEBUG.search(net):
        return "Debug"
    if _ANALOG.search(net):
        return "Analog"
    if re.search(r"(?:_P|_N|\+|-)($|[/_.])", net, re.IGNORECASE):
        return "Differential"
    return "Signal"


def _point_pairs(expr: list) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for item in expr[1:]:
        if not isinstance(item, list) or not item:
            continue
        if item[0] in {"start", "end", "mid", "center", "xy"} and len(item) >= 3:
            try:
                result.append((_number(item[1]), _number(item[2])))
            except ValueError:
                pass
        result.extend(_point_pairs(item))
    return result


def _circle_bounds(expr: list) -> list[tuple[float, float]]:
    center = child(expr, "center")
    end = child(expr, "end")
    if not center or not end or len(center) < 3 or len(end) < 3:
        return _point_pairs(expr)
    cx, cy = _number(center[1]), _number(center[2])
    radius = math.hypot(_number(end[1]) - cx, _number(end[2]) - cy)
    return [(cx - radius, cy - radius), (cx + radius, cy + radius)]


def _arc_bounds(expr: list) -> list[tuple[float, float]]:
    named = {name: child(expr, name) for name in ("start", "mid", "end")}
    if any(item is None or len(item) < 3 for item in named.values()):
        return _point_pairs(expr)
    start, mid, end = [(_number(named[name][1]), _number(named[name][2])) for name in named]
    ax, ay = start
    bx, by = mid
    cx, cy = end
    determinant = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(determinant) < 1e-12:
        return [start, mid, end]
    ux = (
        (ax * ax + ay * ay) * (by - cy)
        + (bx * bx + by * by) * (cy - ay)
        + (cx * cx + cy * cy) * (ay - by)
    ) / determinant
    uy = (
        (ax * ax + ay * ay) * (cx - bx)
        + (bx * bx + by * by) * (ax - cx)
        + (cx * cx + cy * cy) * (bx - ax)
    ) / determinant
    radius = math.hypot(ax - ux, ay - uy)

    def angle(point: tuple[float, float]) -> float:
        return math.atan2(point[1] - uy, point[0] - ux) % (2 * math.pi)

    a0, am, a1 = angle(start), angle(mid), angle(end)
    ccw_sweep = (a1 - a0) % (2 * math.pi)
    use_ccw = (am - a0) % (2 * math.pi) <= ccw_sweep + 1e-9

    def on_arc(candidate: float) -> bool:
        if use_ccw:
            return (candidate - a0) % (2 * math.pi) <= ccw_sweep + 1e-9
        return (a0 - candidate) % (2 * math.pi) <= (a0 - a1) % (2 * math.pi) + 1e-9

    points = [start, mid, end]
    for candidate in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2):
        if on_arc(candidate):
            points.append((ux + radius * math.cos(candidate), uy + radius * math.sin(candidate)))
    return points


def _edge_points(expr: list) -> list[tuple[float, float]]:
    layer = child(expr, "layer")
    if not layer or "Edge.Cuts" not in layer[1:]:
        return []
    if expr[0] == "gr_circle":
        return _circle_bounds(expr)
    if expr[0] == "gr_arc":
        return _arc_bounds(expr)
    return _point_pairs(expr)


def _aux_origin(setup: list | None) -> tuple[float, float] | None:
    item = child(setup, "aux_axis_origin") if setup else None
    return (_number(item[1]), _number(item[2])) if item and len(item) >= 3 else None


def _title_block_revision(title_block: list | None) -> str:
    item = child(title_block, "rev") if title_block else None
    return str(item[1]).strip() if item and len(item) >= 2 else ""


def _schematic_revision(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        source = path.read_text(encoding="utf-8")
        title_block = next(root_forms(source, {"title_block"}, root_name="kicad_sch"), None)
    except (OSError, SExprError):
        return ""
    return _title_block_revision(title_block)


def _project_revision(board_path: Path, pcb_revision: str) -> str:
    project_path = board_path.with_suffix(".kicad_pro")
    if project_path.is_file():
        try:
            project = json.loads(project_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            project = {}
        variables = project.get("text_variables", {}) if isinstance(project, dict) else {}
        if isinstance(variables, dict):
            normalized = {str(key).casefold(): str(value).strip() for key, value in variables.items()}
            for key in ("revision", "rev", "pcb_revision", "sch_revision"):
                if value := normalized.get(key):
                    return re.sub(r"^rev(?:ision)?[.\s:]*", "", value, flags=re.IGNORECASE) or value
    if pcb_revision:
        return pcb_revision
    return _schematic_revision(board_path.with_suffix(".kicad_sch"))


def extract_board(path: str | Path) -> BoardData:
    board_path = Path(path)
    source = board_path.read_text(encoding="utf-8")
    keep = {"setup", "title_block", "net", "footprint", "gr_line", "gr_arc", "gr_rect", "gr_circle", "gr_poly", "gr_curve"}

    setup: list | None = None
    title_block: list | None = None
    footprints: list[list] = []
    edge_points: list[tuple[float, float]] = []
    net_names: set[str] = set()
    for form in root_forms(source, keep):
        if form[0] == "setup":
            setup = form
        elif form[0] == "title_block":
            title_block = form
        elif form[0] == "footprint":
            footprints.append(form)
        elif form[0] == "net" and len(form) > 1:
            if name := str(form[-1]):
                net_names.add(name)
        elif form[0].startswith("gr_"):
            edge_points.extend(_edge_points(form))

    if not edge_points:
        # A useful fallback for incomplete boards: bound the report by footprint origins.
        edge_points = [(_at(fp)[0], _at(fp)[1]) for fp in footprints]
    if not edge_points:
        raise ValueError("No Edge.Cuts geometry or footprints found")

    xs, ys = zip(*edge_points)
    bounds = Bounds(min(xs), min(ys), max(xs), max(ys))
    if bounds.width <= 0 or bounds.height <= 0:
        raise ValueError("Board bounds have zero width or height")

    raw_points: list[dict] = []
    for footprint in footprints:
        library_id = str(footprint[1]) if len(footprint) > 1 else ""
        properties = _property_map(footprint)
        reference = properties.get("Reference", "")
        value = properties.get("Value", "")
        conventional = bool(_TP_REFERENCE.match(reference) or "testpoint" in library_id.lower())
        pads = children(footprint, "pad")
        # KiCad 10 stores the net name directly on pads and may omit the old
        # root-level numeric net table entirely.
        net_names.update(name for pad in pads if (name := _net(pad)))
        selected = [pad for pad in pads if conventional or _has_testpoint_property(pad)]
        for ordinal, pad in enumerate(selected, start=1):
            pad_number = str(pad[1]) if len(pad) > 1 else ""
            absolute_x, absolute_y = _absolute_pad_position(footprint, pad)
            side, footprint_side = _side(footprint, pad)
            net = _net(pad)
            reason = "fabrication_property" if _has_testpoint_property(pad) else "testpoint_footprint"
            raw_points.append(
                {
                    "reference": reference or library_id or "TP",
                    "pad_number": pad_number,
                    "value": value,
                    "absolute_x": absolute_x,
                    "absolute_y": absolute_y,
                    "side": side,
                    "footprint_side": footprint_side,
                    "net": net,
                    "pad_type": "THRU" if side == "both" else "SMT",
                    "reason": reason,
                    "ordinal": ordinal,
                    "selected_count": len(selected),
                }
            )

    points: list[TestPoint] = []
    used_ids: dict[str, int] = {}
    for item in raw_points:
        ref = item["reference"]
        pad_number = item["pad_number"]
        point_id = ref if item["selected_count"] == 1 and _TP_REFERENCE.match(ref) else f"{ref}.{pad_number or item['ordinal']}"
        count = used_ids.get(point_id, 0) + 1
        used_ids[point_id] = count
        if count > 1:
            point_id = f"{point_id}-{count}"
        absolute_x = item["absolute_x"]
        absolute_y = item["absolute_y"]
        points.append(
            TestPoint(
                id=point_id,
                source_ref=ref,
                source_pad=pad_number,
                value=item["value"],
                net=item["net"],
                side=item["side"],
                footprint_side=item["footprint_side"],
                x_mm=round(absolute_x - bounds.min_x, 4),
                y_mm=round(bounds.max_y - absolute_y, 4),
                absolute_x_mm=round(absolute_x, 4),
                absolute_y_mm=round(absolute_y, 4),
                top_left_x_mm=round(absolute_x - bounds.min_x, 4),
                top_left_y_mm=round(absolute_y - bounds.min_y, 4),
                pad_type=item["pad_type"],
                category=_category(item["net"]),
                selection_reason=item["reason"],
            )
        )

    points.sort(key=lambda point: (point.source_ref.casefold(), point.source_pad.casefold()))
    return BoardData(
        name=board_path.stem,
        source=str(board_path.resolve()),
        revision=_project_revision(board_path, _title_block_revision(title_block)),
        bounds=bounds,
        aux_origin=_aux_origin(setup),
        testpoints=tuple(points),
        total_nets=len(net_names),
    )
