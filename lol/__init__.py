# lol/__init__.py
from .core import LeagueOfLegends

async def setup(bot):
    cog = LeagueOfLegends(bot)
    await bot.add_cog(cog)