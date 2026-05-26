"""
engine/map_loader.py — World Pack ingestion.

A World Pack is a directory or ZIP archive with this structure:

    my_pack/
    ├── pack.json          # metadata and configuration
    ├── map.png            # the base map image (any size; ~2000px recommended)
    └── panoramas/         # optional: wide images keyed by location ID
        ├── A1.jpg
        └── ...

pack.json schema:
{
    "name":        "Earth (Standard)",
    "id":          "earth",
    "version":     "1.0.0",
    "author":      "GridDrop Team",
    "description": "Real-world geography — continents and oceans.",
    "grid_size":   100,
    "map_scale":   1.0,
    "max_distance_override": null,   // null → use engine default diagonal
    "micro_mode":  true,             // false = casual/party (macro grid only)
    "tags":        ["geography", "official"]
}

Packs are cached in memory after first load. The cache key is the pack's
canonical "id" field from pack.json. Reloading is triggered by the admin
command [p]drop reload_pack.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class WorldPack:
    """A loaded, validated World Pack ready for use in a game session."""
    id:           str
    name:         str
    version:      str
    author:       str
    description:  str
    grid_size:    int
    map_scale:    float
    micro_mode:   bool
    tags:         list[str]
    max_distance_override: Optional[float]

    # Raw image bytes — kept in memory after first load.
    # Large maps (~2000px PNG) are typically 3-8 MB; acceptable for a bot.
    map_image: bytes = field(repr=False)

    # Optional panorama lookup: location_id → raw image bytes
    panoramas: dict[str, bytes] = field(default_factory=dict, repr=False)

    @property
    def has_panoramas(self) -> bool:
        return len(self.panoramas) > 0

    @property
    def effective_max_distance(self) -> Optional[float]:
        return self.max_distance_override


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class MapLoader:
    """
    Loads and caches World Packs from disk.

    Usage:
        loader = MapLoader(pack_dir=Path("~/.local/share/griddrop/packs"))
        pack = await loader.load("earth")
    """

    REQUIRED_FIELDS = {"name", "id", "version", "author", "description"}
    DEFAULTS = {
        "grid_size":            100,
        "map_scale":            1.0,
        "micro_mode":           True,
        "max_distance_override": None,
        "tags":                 [],
    }

    def __init__(self, pack_dir: Path) -> None:
        self.pack_dir = pack_dir
        self._cache: dict[str, WorldPack] = {}

    # --- Public API ---

    def load(self, pack_id: str, force_reload: bool = False) -> WorldPack:
        """
        Load a pack by its ID. Raises FileNotFoundError if not found.
        Results are cached; pass force_reload=True to bust the cache.
        """
        if not force_reload and pack_id in self._cache:
            return self._cache[pack_id]

        pack = self._find_and_load(pack_id)
        self._cache[pack_id] = pack
        return pack

    def list_available(self) -> list[dict]:
        """
        Return lightweight metadata for all packs in pack_dir.
        Does NOT load image bytes — suitable for admin listing commands.
        """
        results = []
        if not self.pack_dir.exists():
            return results

        for candidate in sorted(self.pack_dir.iterdir()):
            meta = self._read_meta_only(candidate)
            if meta:
                results.append(meta)
        return results

    def evict(self, pack_id: str) -> bool:
        """Remove a pack from cache. Returns True if it was cached."""
        return self._cache.pop(pack_id, None) is not None

    def evict_all(self) -> None:
        self._cache.clear()

    # --- Internal loading ---

    def _find_and_load(self, pack_id: str) -> WorldPack:
        """Locate a pack by ID in pack_dir (directory or ZIP)."""
        if not self.pack_dir.exists():
            raise FileNotFoundError(f"Pack directory does not exist: {self.pack_dir}")

        # Try directory pack first, then ZIP
        dir_candidate = self.pack_dir / pack_id
        zip_candidate = self.pack_dir / f"{pack_id}.zip"

        if dir_candidate.is_dir():
            return self._load_from_dir(dir_candidate)
        elif zip_candidate.is_file():
            return self._load_from_zip(zip_candidate)
        else:
            # Scan all packs to find one whose pack.json "id" matches
            for candidate in self.pack_dir.iterdir():
                meta = self._read_meta_only(candidate)
                if meta and meta.get("id") == pack_id:
                    if candidate.is_dir():
                        return self._load_from_dir(candidate)
                    elif candidate.suffix == ".zip":
                        return self._load_from_zip(candidate)

        raise FileNotFoundError(
            f"World Pack {pack_id!r} not found in {self.pack_dir}. "
            f"Expected a directory or ZIP named '{pack_id}' with a pack.json inside."
        )

    def _load_from_dir(self, path: Path) -> WorldPack:
        meta_path = path / "pack.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"No pack.json in {path}")

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self._validate_meta(meta)

        map_path = path / "map.png"
        if not map_path.exists():
            raise FileNotFoundError(f"No map.png in {path}")
        map_bytes = map_path.read_bytes()

        panoramas = {}
        pano_dir = path / "panoramas"
        if pano_dir.is_dir():
            for pano_file in pano_dir.iterdir():
                if pano_file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    panoramas[pano_file.stem] = pano_file.read_bytes()

        return self._build_pack(meta, map_bytes, panoramas)

    def _load_from_zip(self, path: Path) -> WorldPack:
        with zipfile.ZipFile(path, "r") as zf:
            names = set(zf.namelist())

            # Find pack.json (may be at root or inside a single subdirectory)
            meta_name = self._find_in_zip(names, "pack.json")
            if not meta_name:
                raise FileNotFoundError(f"No pack.json in ZIP {path}")
            prefix = meta_name[: -len("pack.json")]

            meta = json.loads(zf.read(meta_name).decode("utf-8"))
            self._validate_meta(meta)

            map_name = self._find_in_zip(names, f"{prefix}map.png")
            if not map_name:
                raise FileNotFoundError(f"No map.png in ZIP {path}")
            map_bytes = zf.read(map_name)

            panoramas = {}
            pano_prefix = f"{prefix}panoramas/"
            for name in names:
                if name.startswith(pano_prefix) and not name.endswith("/"):
                    stem = Path(name).stem
                    suffix = Path(name).suffix.lower()
                    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
                        panoramas[stem] = zf.read(name)

        return self._build_pack(meta, map_bytes, panoramas)

    @staticmethod
    def _find_in_zip(names: set[str], target: str) -> Optional[str]:
        """Find a file in a ZIP by its basename, regardless of nesting depth."""
        for name in names:
            if name == target or name.endswith("/" + target):
                return name
        return None

    def _build_pack(self, meta: dict, map_bytes: bytes, panoramas: dict) -> WorldPack:
        return WorldPack(
            id=meta["id"],
            name=meta["name"],
            version=meta["version"],
            author=meta["author"],
            description=meta["description"],
            grid_size=meta.get("grid_size", self.DEFAULTS["grid_size"]),
            map_scale=meta.get("map_scale", self.DEFAULTS["map_scale"]),
            micro_mode=meta.get("micro_mode", self.DEFAULTS["micro_mode"]),
            tags=meta.get("tags", self.DEFAULTS["tags"]),
            max_distance_override=meta.get("max_distance_override"),
            map_image=map_bytes,
            panoramas=panoramas,
        )

    def _validate_meta(self, meta: dict) -> None:
        missing = self.REQUIRED_FIELDS - meta.keys()
        if missing:
            raise ValueError(f"pack.json is missing required fields: {missing}")

        if not isinstance(meta.get("grid_size", 100), int):
            raise ValueError("pack.json: grid_size must be an integer")
        if not isinstance(meta.get("map_scale", 1.0), (int, float)):
            raise ValueError("pack.json: map_scale must be a number")

    def _read_meta_only(self, candidate: Path) -> Optional[dict]:
        """Read only pack.json metadata without loading image bytes."""
        try:
            if candidate.is_dir():
                meta_path = candidate / "pack.json"
                if meta_path.exists():
                    return json.loads(meta_path.read_text(encoding="utf-8"))
            elif candidate.suffix == ".zip":
                with zipfile.ZipFile(candidate, "r") as zf:
                    meta_name = self._find_in_zip(set(zf.namelist()), "pack.json")
                    if meta_name:
                        return json.loads(zf.read(meta_name).decode("utf-8"))
        except Exception:
            pass
        return None
