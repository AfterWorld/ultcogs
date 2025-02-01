from redbot.core.bot import Red
from .bountybattle import BountyBattle


async def setup(bot: Red):
    """Load the BountyBattle cog."""
    cog = BountyBattle(bot)
    await bot.add_cog(cog)