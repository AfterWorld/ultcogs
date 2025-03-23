from redbot.core.bot import Red
from .crew import CrewSystem  # Updated to match your actual class name

async def setup(bot: Red):
    """Load the CrewSystem cog."""
    cog = CrewSystem(bot)  # Instantiate the main cog
    await bot.add_cog(cog)
