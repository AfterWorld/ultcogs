"""Local monster portraits: no external image scraping or runtime downloads."""

from pathlib import Path

import discord

# Explicit allowlist prevents retired AI files left by an updater from being used.
ART_VERSION = "redshrike-v1"
ART_KEYS = frozenset({"slime", "revenant", "imp", "mask", "wisp"})
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
        credit = "Art: Stephen (Redshrike) Challener · OpenGameArt.org · CC BY 3.0"
        footer = embed.footer.text or ""
        if credit not in footer:
            embed.set_footer(text=f"{footer} • {credit}" if footer else credit)
