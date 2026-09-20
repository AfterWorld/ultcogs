"""Local monster portraits: no external image scraping or runtime downloads."""

from pathlib import Path

import discord

from .content import MONSTERS

ART_DIR = Path(__file__).parent / "assets" / "monsters"


def art_path(key):
    return ART_DIR / f"{key}.jpg" if key in MONSTERS else None


def artwork(embed, key):
    path = art_path(key)
    if path and path.is_file():
        embed.set_thumbnail(url=f"attachment://{key}.jpg")
        return {"file": discord.File(path, filename=f"{key}.jpg")}
    return {}


def thumbnail(embed, key):
    path = art_path(key)
    if path and path.is_file():
        embed.set_thumbnail(url=f"attachment://{key}.jpg")
