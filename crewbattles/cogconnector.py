from redbot.core import commands
import discord

class CogConnector:
    """
    A utility class that connects the CrewTournament and TournamentSystem cogs.
    This allows them to communicate and share data while remaining separate.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.crew_cog = None
        self.tournament_cog = None
    
    async def initialize(self):
        """Initialize the connection between cogs."""
        # Wait for bot to be ready
        await self.bot.wait_until_ready()
        
        # Get the crew cog
        self.crew_cog = self.bot.get_cog("CrewTournament")
        if not self.crew_cog:
            print("WARNING: CrewTournament cog not found. Some features may not work correctly.")
        
        # Get the tournament cog
        self.tournament_cog = self.bot.get_cog("TournamentSystem")
        if not self.tournament_cog:
            print("WARNING: TournamentSystem cog not found. Some features may not work correctly.")
        
        # Connect the cogs if both are available
        if self.crew_cog and self.tournament_cog:
            print("Connecting CrewTournament and TournamentSystem cogs...")
            self.tournament_cog.set_crew_manager(self.crew_cog)
            print("Cogs connected successfully!")
        else:
            print("Could not connect cogs. Please make sure both cogs are loaded.")
            
    @commands.Cog.listener()
    async def on_cog_add(self, cog):
        """Detect when a cog is added and connect if needed."""
        if cog.__class__.__name__ == "CrewTournament":
            self.crew_cog = cog
            print("CrewTournament cog detected.")
            if self.tournament_cog:
                self.tournament_cog.set_crew_manager(self.crew_cog)
                print("Connected TournamentSystem to CrewTournament cog.")
        
        elif cog.__class__.__name__ == "TournamentSystem":
            self.tournament_cog = cog
            print("TournamentSystem cog detected.")
            if self.crew_cog:
                self.tournament_cog.set_crew_manager(self.crew_cog)
                print("Connected TournamentSystem to CrewTournament cog.")

def setup(bot):
    """Set up the connector."""
    connector = CogConnector(bot)
    bot.loop.create_task(connector.initialize())
    bot.add_listener(connector.on_cog_add)
    print("Cog Connector initialized")
