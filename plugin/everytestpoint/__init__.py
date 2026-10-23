"""Every Test Point report generator."""

from pathlib import Path

from .generator import GenerationResult, generate_report
from .dft import ProbePair, calculate_probe_pairs
from .pcb import BoardData, TestPoint, extract_board

__all__ = [
    "BoardData",
    "GenerationResult",
    "ProbePair",
    "TestPoint",
    "calculate_probe_pairs",
    "extract_board",
    "generate_report",
]

__version__ = (Path(__file__).resolve().parent.parent / "VERSION").read_text(
    encoding="utf-8"
).strip()
