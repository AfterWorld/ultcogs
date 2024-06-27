from redbot.core.bot import Red
from .main import OnePieceAdventures

async def setup(bot: Red):
    cog = OnePieceAdventures(bot)
    await bot.add_cog(cog)
