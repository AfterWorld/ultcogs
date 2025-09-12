from __future__ import annotations
import discord
from discord.ext.commands import Context
from datetime import datetime
from typing import Optional
from .constants import COLORS


def make_embed(title: Optional[str] = None, description: Optional[str] = None, color: str = "info") -> discord.Embed:
    return discord.Embed(
        title=title,
        description=description,
        color=COLORS.get(color, COLORS["info"])
    )


def error_embed(description: str) -> discord.Embed:
    return make_embed("❌ Error", description, "error")


def success_embed(description: str) -> discord.Embed:
    return make_embed("✅ Success", description, "success")


def update_embed_field(embed: discord.Embed, name: str, value: str, inline: bool = False):
    for i, field in enumerate(embed.fields):
        if field.name == name:
            embed.set_field_at(i, name=name, value=value, inline=inline)
            return
    embed.add_field(name=name, value=value, inline=inline)
