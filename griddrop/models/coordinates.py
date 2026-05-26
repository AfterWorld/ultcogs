"""
Coordinate primitives for GridDrop.

Two-tiered grid system:
  Macro grid: 10×10 sectors (A-J, 1-10)
  Micro grid: 10×10 cells within each sector
  Effective resolution: 100×100 = 10,000 unique points on the map

All coordinates are zero-indexed internally; display conversion is handled
at the UI layer (engine/renderer.py and ui/embeds.py).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class MacroSector:
    """
    A sector on the macro 10×10 grid.

    row: 0-9  (displayed as A-J)
    col: 0-9  (displayed as 1-10)
    """
    row: int  # 0-9
    col: int  # 0-9

    def __post_init__(self) -> None:
        if not (0 <= self.row <= 9):
            raise ValueError(f"MacroSector row must be 0-9, got {self.row}")
        if not (0 <= self.col <= 9):
            raise ValueError(f"MacroSector col must be 0-9, got {self.col}")

    @property
    def label(self) -> str:
        """Human-readable label, e.g. 'D4'."""
        return f"{chr(65 + self.row)}{self.col + 1}"

    @classmethod
    def from_label(cls, label: str) -> "MacroSector":
        """Parse a label like 'D4' back into a MacroSector."""
        label = label.strip().upper()
        if len(label) < 2:
            raise ValueError(f"Invalid MacroSector label: {label!r}")
        row = ord(label[0]) - 65
        col = int(label[1:]) - 1
        return cls(row=row, col=col)


@dataclass(frozen=True)
class MicroCell:
    """
    A cell on the micro 10×10 grid within a MacroSector.

    row: 0-9  (displayed as a-j)
    col: 0-9  (displayed as 1-10)
    """
    row: int  # 0-9
    col: int  # 0-9

    def __post_init__(self) -> None:
        if not (0 <= self.row <= 9):
            raise ValueError(f"MicroCell row must be 0-9, got {self.row}")
        if not (0 <= self.col <= 9):
            raise ValueError(f"MicroCell col must be 0-9, got {self.col}")

    @property
    def label(self) -> str:
        """Human-readable label, e.g. 'c7'."""
        return f"{chr(97 + self.row)}{self.col + 1}"


@dataclass(frozen=True)
class GridPoint:
    """
    A fully-resolved point in the 100×100 effective coordinate space.

    x: 0-99  (macro_col * 10 + micro_col)
    y: 0-99  (macro_row * 10 + micro_row)

    Origin (0, 0) is top-left of the map.
    """
    x: float  # 0.0 – 99.0
    y: float  # 0.0 – 99.0

    def __post_init__(self) -> None:
        if not (0.0 <= self.x <= 99.0):
            raise ValueError(f"GridPoint x must be 0-99, got {self.x}")
        if not (0.0 <= self.y <= 99.0):
            raise ValueError(f"GridPoint y must be 0-99, got {self.y}")

    @classmethod
    def from_tiers(cls, macro: MacroSector, micro: MicroCell) -> "GridPoint":
        """Combine macro sector + micro cell into a resolved GridPoint."""
        x = macro.col * 10 + micro.col
        y = macro.row * 10 + micro.row
        return cls(x=float(x), y=float(y))

    @classmethod
    def from_macro_only(cls, macro: MacroSector) -> "GridPoint":
        """
        Resolve to the centre of a macro sector.
        Used when micro-targeting is disabled (casual/party mode).
        """
        x = macro.col * 10 + 4.5
        y = macro.row * 10 + 4.5
        return cls(x=x, y=y)

    @property
    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass(frozen=True)
class NormalizedPoint:
    """
    A point expressed as fractions of map width/height (0.0 – 1.0).
    Used for World Pack-agnostic operations (pixel mapping, reveal rendering).
    """
    nx: float  # 0.0 – 1.0
    ny: float  # 0.0 – 1.0

    @classmethod
    def from_grid_point(cls, point: GridPoint, grid_size: int = 100) -> "NormalizedPoint":
        return cls(nx=point.x / grid_size, ny=point.y / grid_size)

    def to_pixel(self, image_width: int, image_height: int) -> tuple[int, int]:
        """Map to pixel coordinates for Pillow rendering."""
        return (int(self.nx * image_width), int(self.ny * image_height))
