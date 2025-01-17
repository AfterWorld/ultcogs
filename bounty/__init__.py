from redbot.core.bot import Red
from .bounty import BountyCog


async def setup(bot: Red):
    """Load the Deathmatch cog."""
    cog = BountyCog(bot)
    await bot.add_cog(cog)

