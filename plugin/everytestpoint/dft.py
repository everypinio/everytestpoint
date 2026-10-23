"""Probe-spacing calculations for design-for-test reports."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .pcb import BoardData, TestPoint


@dataclass(frozen=True)
class ProbePair:
    point_a: str
    net_a: str
    point_b: str
    net_b: str
    sides: tuple[str, ...]
    distance_mm: float

    def to_dict(self) -> dict:
        values = asdict(self)
        values["sides"] = list(self.sides)
        return values


def accessible_sides(point: TestPoint) -> frozenset[str]:
    if point.side == "both":
        return frozenset(("top", "bottom"))
    return frozenset((point.side,))


def calculate_probe_pairs(board: BoardData) -> tuple[ProbePair, ...]:
    """Return every pair that can place two probes on the same fixture side."""
    pairs: list[ProbePair] = []
    points = board.testpoints
    for index, first in enumerate(points):
        for second in points[index + 1 :]:
            common_sides = accessible_sides(first) & accessible_sides(second)
            if not common_sides:
                continue
            distance = math.hypot(
                first.absolute_x_mm - second.absolute_x_mm,
                first.absolute_y_mm - second.absolute_y_mm,
            )
            pairs.append(
                ProbePair(
                    point_a=first.id,
                    net_a=first.net,
                    point_b=second.id,
                    net_b=second.net,
                    sides=tuple(side for side in ("top", "bottom") if side in common_sides),
                    distance_mm=round(distance, 4),
                )
            )
    pairs.sort(key=lambda pair: (pair.distance_mm, pair.point_a.casefold(), pair.point_b.casefold()))
    return tuple(pairs)
