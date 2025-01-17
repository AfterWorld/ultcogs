from redbot.core.bot import Red
from .onepiece import OnePiece


async def setup(bot: Red):
    """Load the Deathmatch cog."""
    cog = OnePieceRPG(bot)
    await bot.add_cog(cog)
