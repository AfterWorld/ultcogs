"""Local monster portraits: no external image scraping or runtime downloads."""

from pathlib import Path

import discord

# Explicit allowlist prevents retired AI files left by an updater from being used.
ART_VERSION = "redshrike-v2"
ART_KEYS = frozenset({"slime", "revenant", "imp", "mask", "wisp", "beetle", "raizen"})
ART_DIR = Path(__file__).parent / "assets" / "monsters"


def art_path(key):
    return ART_DIR / f"{key}.jpg" if key in ART_KEYS else None


def artwork(embed, key):
    path = art_path(key)
    if path and path.is_file():
        thumbnail(embed, key)
        return {"file": discord.File(path, filename=f"{key}.jpg")}
    return {}


def thumbnail(embed, key):
    path = art_path(key)
    if path and path.is_file():
        embed.set_thumbnail(url=f"attachment://{key}.jpg")
        license_name = "CC BY-SA 3.0 · commissioned by Bertram" if key == "raizen" else "CC BY 3.0"
        credit = "Art: Stephen (Redshrike) Challener · OpenGameArt.org · " + license_name
        footer = embed.footer.text or ""
        if credit not in footer:
            embed.set_footer(text=f"{footer} • {credit}" if footer else credit)
