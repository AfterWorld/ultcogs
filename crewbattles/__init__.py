from .crew import CrewManagement
from .tournament import TournamentSystem

async def setup(bot):
    crew_cog = CrewManagement(bot)
    await bot.add_cog(crew_cog)
    
    tournament_cog = TournamentSystem(bot)
    tournament_cog.set_crew_manager(crew_cog)  
    await bot.add_cog(tournament_cog)
