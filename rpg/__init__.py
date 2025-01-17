from redbot.core.bot import Red
from .onepiece import OnePieceRPG


async def setup(bot: Red):
    """Load the RPG cog."""
    cog = OnePieceRPG(bot)
    await bot.add_cog(cog)
