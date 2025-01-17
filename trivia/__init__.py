from redbot.core.bot import Red
from .trivia import Trivia


async def setup(bot: Red):
    """Load the Deathmatch cog."""
    cog = Trivia(bot)
    await bot.add_cog(cog)
