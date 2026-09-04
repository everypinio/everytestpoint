"""Every Test Point report generator."""

from .generator import GenerationResult, generate_report
from .pcb import BoardData, TestPoint, extract_board

__all__ = [
    "BoardData",
    "GenerationResult",
    "TestPoint",
    "extract_board",
    "generate_report",
]

__version__ = "0.1.0"
