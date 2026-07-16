"""Data file loading helpers for Voyage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_json(name: str) -> Any:
    """Load a JSON data file from the cog's data directory."""
    path = DATA_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))
