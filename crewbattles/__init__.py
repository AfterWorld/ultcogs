from redbot.core import commands
from .crew import CrewManagement
from .tournament import TournamentSystem

class CombinedCrewSystem(commands.Cog):
    """Main cog that combines crew and tournament functionality"""
    
    def __init__(self, bot):
        self.bot = bot
        self.crew_manager = CrewManagement(bot, self)
        self.tournament_system = TournamentSystem(bot, self)
    
    
def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(CombinedCrewSystem(bot))
