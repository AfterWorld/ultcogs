import discord

def error_embed(message: str) -> discord.Embed:
    return discord.Embed(description=message, color=0xe74c3c)

def success_embed(message: str) -> discord.Embed:
    return discord.Embed(description=message, color=0x2ecc71)
