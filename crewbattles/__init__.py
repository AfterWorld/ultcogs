from redbot.core.bot import Red
from .crew import CrewManagement

async def setup(bot: Red):
    """Load the CrewSystem cog."""
    cog = CrewSystem(bot)  # Instantiate the main cog
    await bot.add_cog(cog)
