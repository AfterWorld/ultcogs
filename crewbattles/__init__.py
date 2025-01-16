from redbot.core.bot import Red
from .deathmatch import Deathmatch


async def setup(bot: Red):
    """Load the Deathmatch cog."""
    cog = crewbattles(bot)
    await bot.add_cog(cog)

