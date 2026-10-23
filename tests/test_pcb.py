from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from plugin.everytestpoint.pcb import extract_board


BOARD = r'''(kicad_pcb
  (version 20260101)
  (generator pcbnew)
  (general (thickness 1.6))
  (setup (aux_axis_origin 10 20))
  (net 0 "")
  (net 1 "GND")
  (net 2 "+3V3")
  (gr_rect (start 10 20) (end 50 50) (stroke (width 0.05) (type default)) (fill none) (layer "Edge.Cuts"))
  (footprint "TestPoint:TestPoint_Pad_D1.0mm"
    (layer "F.Cu")
    (at 20 25 90)
    (property "Reference" "TP1")
    (property "Value" "RESET")
    (pad "1" smd circle (at 2 0) (size 1 1) (layers "F.Cu" "F.Mask") (net 1 "GND"))
  )
  (footprint "Connector:Header"
    (layer "B.Cu")
    (at 40 40 90)
    (property "Reference" "J1")
    (property "Value" "HEADER")
    (pad "1" smd circle (at 2 0) (size 1 1) (layers "B.Cu" "B.Mask") (net 2 "+3V3") (property pad_prop_testpoint))
    (pad "2" thru_hole circle (at 0 2) (size 1 1) (drill 0.5) (layers "*.Cu" "*.Mask") (net 1 "GND") (property pad_prop_testpoint))
  )
)'''

THROUGH_HOLE_BOARD = r'''(kicad_pcb
  (version 20260101)
  (generator pcbnew)
  (gr_rect (start 0 0) (end 20 20) (stroke (width 0.05) (type default)) (fill none) (layer "Edge.Cuts"))
  (footprint "Connector:Header"
    (layer "F.Cu")
    (at 5 5)
    (property "Reference" "J1")
    (property "Value" "FITTED_TOP")
    (attr through_hole)
    (pad "1" thru_hole circle (at 0 0) (size 1 1) (drill 0.5) (layers "*.Cu" "*.Mask") (net 1 "TOP_COMPONENT") (property pad_prop_testpoint))
  )
  (footprint "Connector:Header"
    (layer "B.Cu")
    (at 10 5)
    (property "Reference" "J2")
    (property "Value" "FITTED_BOTTOM")
    (attr through_hole)
    (pad "1" thru_hole circle (at 0 0) (size 1 1) (drill 0.5) (layers "*.Cu" "*.Mask") (net 2 "BOTTOM_COMPONENT") (property pad_prop_testpoint))
  )
  (footprint "Connector:Header"
    (layer "F.Cu")
    (at 15 5)
    (property "Reference" "J3")
    (property "Value" "NOT_FITTED")
    (attr through_hole dnp)
    (pad "1" thru_hole circle (at 0 0) (size 1 1) (drill 0.5) (layers "*.Cu" "*.Mask") (net 3 "EMPTY_HOLE") (property pad_prop_testpoint))
  )
)'''


class ExtractBoardTests(unittest.TestCase):
    def test_extracts_conventional_and_fabrication_property_points(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.kicad_pcb"
            path.write_text(BOARD, encoding="utf-8")
            path.with_suffix(".kicad_sch").write_text(
                '(kicad_sch (title_block (rev "1.7")))', encoding="utf-8"
            )
            board = extract_board(path)

        self.assertEqual((board.bounds.min_x, board.bounds.min_y), (10.0, 20.0))
        self.assertEqual((board.bounds.max_x, board.bounds.max_y), (50.0, 50.0))
        self.assertEqual(board.aux_origin, (10.0, 20.0))
        self.assertEqual(board.revision, "1.7")
        self.assertEqual(len(board.testpoints), 3)
        self.assertEqual(board.total_nets, 2)
        self.assertEqual(board.covered_nets, 2)
        by_id = {point.id: point for point in board.testpoints}
        self.assertEqual(by_id["TP1"].net, "GND")
        self.assertAlmostEqual(by_id["TP1"].absolute_x_mm, 20.0)
        self.assertAlmostEqual(by_id["TP1"].absolute_y_mm, 23.0)
        self.assertEqual(by_id["J1.1"].side, "bottom")
        self.assertAlmostEqual(by_id["J1.1"].absolute_x_mm, 40.0)
        self.assertAlmostEqual(by_id["J1.1"].absolute_y_mm, 38.0)
        self.assertEqual(by_id["J1.2"].side, "top")
        self.assertEqual(by_id["J1.2"].pad_type, "THRU")
        self.assertEqual(by_id["J1.2"].category, "Ground")

    def test_through_hole_access_depends_on_mounting_side_and_dnp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.kicad_pcb"
            path.write_text(THROUGH_HOLE_BOARD, encoding="utf-8")
            board = extract_board(path)

        by_id = {point.id: point for point in board.testpoints}
        self.assertEqual(by_id["J1.1"].side, "bottom")
        self.assertEqual(by_id["J1.1"].footprint_side, "top")
        self.assertEqual(by_id["J2.1"].side, "top")
        self.assertEqual(by_id["J2.1"].footprint_side, "bottom")
        self.assertEqual(by_id["J3.1"].side, "both")
        self.assertEqual(by_id["J3.1"].pad_type, "THRU")


if __name__ == "__main__":
    unittest.main()
