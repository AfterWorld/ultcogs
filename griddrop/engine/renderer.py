"""
engine/renderer.py — CPU-bound Pillow image processing.

All public methods are async wrappers around synchronous _draw_* functions.
The sync functions are safe to run in a ProcessPoolExecutor because they
import Pillow locally (avoiding pickling issues with module-level objects)
and accept only plain Python primitives / dataclass-derived tuples.

Three rendering tasks:
  1. generate_macro_grid  — full map with 10×10 overlay (sent at round start)
  2. generate_micro_grid  — cropped sector with 10×10 overlay (ephemeral UI)
  3. generate_reveal       — final composite: target dot + per-player dots + lines

All output is returned as raw bytes (PNG) so the caller can pass directly
to discord.File without touching the filesystem.
"""

from __future__ import annotations

import asyncio
import io
import math
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path
from typing import Optional

from ..models.coordinates import GridPoint, MacroSector, NormalizedPoint

# ---------------------------------------------------------------------------
# Module-level executor — one pool shared across the cog lifetime.
# Initialised lazily so import doesn't spawn processes on cog load.
# ---------------------------------------------------------------------------
_executor: Optional[ProcessPoolExecutor] = None


def get_executor() -> ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(max_workers=4)
    return _executor


def shutdown_executor() -> None:
    """Call from cog_unload() to clean up worker processes."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
        _executor = None


# ---------------------------------------------------------------------------
# Colour palette (RGB tuples — no Discord or Pillow constants at module level)
# ---------------------------------------------------------------------------

GRID_LINE_COLOUR  = (255, 255, 255, 100)   # semi-transparent white grid
GRID_LABEL_COLOUR = (255, 255, 255, 220)   # bright white labels
TARGET_COLOUR     = (255, 215,   0, 255)   # gold — the answer dot
PLAYER_COLOURS    = [                       # one per player, cycling
    (255,  99,  71, 230),  # tomato
    ( 30, 144, 255, 230),  # dodger blue
    (50,  205,  50, 230),  # lime green
    (255, 165,   0, 230),  # orange
    (148,   0, 211, 230),  # dark violet
    (  0, 206, 209, 230),  # dark turquoise
    (255,  20, 147, 230),  # deep pink
    (127, 255,   0, 230),  # chartreuse
]
SECTOR_HIGHLIGHT  = (255, 255,   0,  40)   # faint yellow crop indicator
LINE_COLOUR       = (255, 255, 255, 130)   # lines from target to player dots

# Dot sizes (diameter in pixels, relative to a 1000px base map)
TARGET_DOT_RADIUS  = 12
PLAYER_DOT_RADIUS  = 10
LINE_WIDTH         = 2


# ---------------------------------------------------------------------------
# Synchronous draw functions (run in worker processes)
# ---------------------------------------------------------------------------

def _draw_grid_overlay(
    image_bytes: bytes,
    grid_divisions: int = 10,
    labels: bool = True,
    highlight_sector: Optional[tuple[int, int]] = None,
) -> bytes:
    """
    Overlay a grid on an image. Returns PNG bytes.

    highlight_sector: (row, col) 0-indexed sector to shade (for micro zoom).
    """
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    cell_w = w / grid_divisions
    cell_h = h / grid_divisions

    # Optional sector highlight (shown on macro map before micro zoom)
    if highlight_sector is not None:
        sr, sc = highlight_sector
        x0 = int(sc * cell_w)
        y0 = int(sr * cell_h)
        x1 = int((sc + 1) * cell_w)
        y1 = int((sr + 1) * cell_h)
        draw.rectangle([x0, y0, x1, y1], fill=SECTOR_HIGHLIGHT)

    # Grid lines
    for i in range(1, grid_divisions):
        x = int(i * cell_w)
        draw.line([(x, 0), (x, h)], fill=GRID_LINE_COLOUR, width=1)
    for j in range(1, grid_divisions):
        y = int(j * cell_h)
        draw.line([(0, y), (w, y)], fill=GRID_LINE_COLOUR, width=1)

    # Column labels (1-10) along top, row labels (A-J / a-j) along left
    if labels:
        try:
            font_size = max(12, int(cell_w * 0.18))
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        for i in range(grid_divisions):
            col_label = str(i + 1)
            cx = int(i * cell_w + cell_w * 0.5)
            draw.text((cx, 4), col_label, fill=GRID_LABEL_COLOUR, font=font, anchor="mt")

        is_macro = grid_divisions == 10 and highlight_sector is None
        for j in range(grid_divisions):
            row_label = chr(65 + j) if is_macro else chr(97 + j)
            cy = int(j * cell_h + cell_h * 0.5)
            draw.text((4, cy), row_label, fill=GRID_LABEL_COLOUR, font=font, anchor="lm")

    img = Image.alpha_composite(img, overlay)
    out = io.BytesIO()
    img.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def _crop_sector(image_bytes: bytes, macro: tuple[int, int], padding: float = 0.0) -> bytes:
    """
    Crop to a single macro sector (row, col) and return PNG bytes.
    padding: fractional extra context on each edge (0.05 = 5% bleed).
    """
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    w, h = img.size
    row, col = macro
    divisions = 10

    cell_w = w / divisions
    cell_h = h / divisions

    x0 = max(0, (col * cell_w) - padding * cell_w)
    y0 = max(0, (row * cell_h) - padding * cell_h)
    x1 = min(w, ((col + 1) * cell_w) + padding * cell_w)
    y1 = min(h, ((row + 1) * cell_h) + padding * cell_h)

    cropped = img.crop((int(x0), int(y0), int(x1), int(y1)))

    out = io.BytesIO()
    cropped.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def _draw_reveal(
    image_bytes: bytes,
    target: tuple[float, float],
    guesses: list[tuple[int, float, float]],  # (user_id, x, y)
    grid_size: int = 100,
) -> bytes:
    """
    Composite the reveal image:
      - Draw grid lines (faint)
      - Draw line from each player dot to the target dot
      - Draw each player's dot (colour-coded)
      - Draw the target dot (gold) on top

    Returns PNG bytes.
    guesses: list of (user_id, x, y) in grid-space [0, grid_size).
    """
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    w, h = img.size

    # Normalisation helpers
    def gx(grid_x: float) -> int:
        return int((grid_x / grid_size) * w)

    def gy(grid_y: float) -> int:
        return int((grid_y / grid_size) * h)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Faint grid (10×10 macro only on reveal)
    cell_w = w / 10
    cell_h = h / 10
    grid_faint = (255, 255, 255, 40)
    for i in range(1, 10):
        draw.line([(int(i * cell_w), 0), (int(i * cell_w), h)], fill=grid_faint, width=1)
    for j in range(1, 10):
        draw.line([(0, int(j * cell_h)), (w, int(j * cell_h))], fill=grid_faint, width=1)

    tx, ty = gx(target[0]), gy(target[1])

    # Lines from target to each guess
    for idx, (_, px, py) in enumerate(guesses):
        colour = PLAYER_COLOURS[idx % len(PLAYER_COLOURS)]
        line_colour = colour[:3] + (LINE_COLOUR[3],)
        draw.line([(tx, ty), (gx(px), gy(py))], fill=line_colour, width=LINE_WIDTH)

    # Player dots
    for idx, (_, px, py) in enumerate(guesses):
        colour = PLAYER_COLOURS[idx % len(PLAYER_COLOURS)]
        cx, cy = gx(px), gy(py)
        r = PLAYER_DOT_RADIUS
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=colour, outline=(255, 255, 255, 180), width=1)

    # Target dot (drawn last so it sits on top)
    r = TARGET_DOT_RADIUS
    draw.ellipse(
        [(tx - r, ty - r), (tx + r, ty + r)],
        fill=TARGET_COLOUR,
        outline=(255, 255, 255, 255),
        width=2,
    )
    # Gold star marker inside
    draw.ellipse([(tx - 4, ty - 4), (tx + 4, ty + 4)], fill=(200, 160, 0, 255))

    img = Image.alpha_composite(img, overlay)
    out = io.BytesIO()
    img.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def _draw_viewport_crop(
    image_bytes: bytes,
    panel: str,  # "left" | "center" | "right"
    overlap: float = 0.15,
) -> bytes:
    """
    Crop a wide panoramic image into a viewport panel for the look-around mechanic.
    overlap: fractional overlap between panels to prevent hard edges.
    """
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size

    third = w / 3
    slop = int(third * overlap)

    if panel == "left":
        x0, x1 = 0, int(third) + slop
    elif panel == "right":
        x0, x1 = int(2 * third) - slop, w
    else:  # center
        x0 = int(third) - slop
        x1 = int(2 * third) + slop

    cropped = img.crop((x0, 0, x1, h))
    out = io.BytesIO()
    cropped.save(out, format="PNG", optimize=True)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Async public API
# ---------------------------------------------------------------------------

class ImageEngine:
    """
    Async facade over the synchronous Pillow draw functions.
    All heavy work runs in the ProcessPoolExecutor so the bot's event loop
    is never blocked by image I/O or compositing.
    """

    def __init__(self) -> None:
        self._pool = get_executor()

    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._pool, partial(fn, *args, **kwargs))

    # --- Macro map (full map + 10×10 grid sent at round start) ---

    async def generate_macro_grid(
        self,
        base_image_bytes: bytes,
        highlight_sector: Optional[MacroSector] = None,
    ) -> bytes:
        hs = (highlight_sector.row, highlight_sector.col) if highlight_sector else None
        return await self._run(
            _draw_grid_overlay,
            base_image_bytes,
            10,
            True,
            hs,
        )

    # --- Micro map (cropped sector + 10×10 sub-grid for precision targeting) ---

    async def generate_micro_grid(
        self,
        base_image_bytes: bytes,
        macro: MacroSector,
    ) -> bytes:
        # Step 1: crop to sector (in executor)
        cropped = await self._run(_crop_sector, base_image_bytes, (macro.row, macro.col), 0.05)
        # Step 2: overlay micro grid on the crop (separate executor call)
        return await self._run(_draw_grid_overlay, cropped, 10, True, None)

    # --- Reveal composite (target + player dots + connection lines) ---

    async def generate_reveal(
        self,
        base_image_bytes: bytes,
        target: GridPoint,
        guesses: list[tuple[int, GridPoint]],  # (user_id, point)
        grid_size: int = 100,
    ) -> bytes:
        guess_triples = [(uid, pt.x, pt.y) for uid, pt in guesses]
        return await self._run(
            _draw_reveal,
            base_image_bytes,
            (target.x, target.y),
            guess_triples,
            grid_size,
        )

    # --- Viewport panel (panorama look-around mechanic) ---

    async def generate_viewport(
        self,
        panorama_bytes: bytes,
        panel: str,  # "left" | "center" | "right"
    ) -> bytes:
        assert panel in ("left", "center", "right"), f"Invalid panel: {panel!r}"
        return await self._run(_draw_viewport_crop, panorama_bytes, panel)
