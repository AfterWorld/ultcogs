from redbot.core.bot import Red
from .crew import CrewTournament  # Make sure this matches your main class name

async def setup(bot: Red):
    """Load the CrewTournament cog."""
    cog = CrewTournament(bot)  # Instantiate the main cog
    await bot.add_cog(cog)
