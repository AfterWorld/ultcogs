import discord
from redbot.core.utils.chat_formatting import humanize_number
from .constants import EMBED_COLOR_ERR, EMBED_COLOR_OK

def make_embed(title: str = None, description: str = None, color: int = EMBED_COLOR_OK):
    return discord.Embed(title=title, description=description, color=color)

def error_embed(description: str):
    return make_embed(title="❌ Error", description=description, color=EMBED_COLOR_ERR)
