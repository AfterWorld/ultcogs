from redbot.core.bot import Red
from .bounty import BountyBattle


async def setup(bot: Red):
    """Load the Deathmatch cog."""
    cog = BountyBattle(bot)
    await bot.add_cog(cog)