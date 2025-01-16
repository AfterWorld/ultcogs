from redbot.core.bot import Red
from .crew import CrewTournament


async def setup(bot: Red):
    """Load the Deathmatch cog."""
    cog = CrewTournament(bot)
    await bot.add_cog(cog)

