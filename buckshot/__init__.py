# __init__.py
"""
Buckshot Cog for Red-DiscordBot
A strategic Russian Roulette-style game with items and multiplayer support.
"""

from .buckshot import Buckshot

async def setup(bot):
    """Setup function for Red-DiscordBot"""
    cog = Buckshot(bot)
    await bot.add_cog(cog)