from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from plugin.everytestpoint.dft import calculate_probe_pairs
from plugin.everytestpoint.pcb import extract_board
from tests.test_pcb import BOARD


class DftTests(unittest.TestCase):
    def test_calculates_only_pairs_accessible_from_the_same_side(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.kicad_pcb"
            path.write_text(BOARD, encoding="utf-8")
            pairs = calculate_probe_pairs(extract_board(path))

        by_points = {frozenset((pair.point_a, pair.point_b)): pair for pair in pairs}
        self.assertNotIn(frozenset(("TP1", "J1.1")), by_points)
        self.assertEqual(by_points[frozenset(("TP1", "J1.2"))].sides, ("top",))
        self.assertEqual(by_points[frozenset(("J1.1", "J1.2"))].sides, ("bottom",))
        self.assertAlmostEqual(
            by_points[frozenset(("J1.1", "J1.2"))].distance_mm,
            2.8284,
            places=4,
        )


if __name__ == "__main__":
    unittest.main()
