from redbot.core.bot import Red
from .crew import CrewManagement

def setup(bot):
    cog = CrewManagement(bot)  # Updated to use CrewManagement instead of CrewSystem
    bot.add_cog(cog)
