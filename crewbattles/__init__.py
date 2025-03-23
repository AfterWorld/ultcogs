from redbot.core.bot import Red
from .crew import CrewManagement
from .tournament import TournamentSystem

async def setup(bot):
    crew_cog = CrewManagement(bot)
    bot.add_cog(crew_cog)
    
    tournament_cog = TournamentSystem(bot)
    bot.add_cog(tournament_cog)
    
    # Connect the cogs
    tournament_cog.set_crew_manager(crew_cog)
