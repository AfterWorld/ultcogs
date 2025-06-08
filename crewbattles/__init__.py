"""
__init__.py
Package initialization and main cog setup for root directory structure
"""

from .crew import CrewManagement

# Import migration setup
try:
    from .migration import setup_migration
    MIGRATION_AVAILABLE = True
except ImportError:
    MIGRATION_AVAILABLE = False

try:
    from .tournament import TournamentSystem
    TOURNAMENT_AVAILABLE = True
except ImportError:
    TOURNAMENT_AVAILABLE = False

# Package version
__version__ = "2.0.0"
__author__ = "UltPanda"

# Export main cog for Red-DiscordBot
__red_end_user_data_statement__ = (
    "This cog stores crew membership data, user IDs, role IDs, "
    "crew statistics, and user activity timestamps. "
    "All data is stored locally and can be deleted upon request."
)

# Main setup function for Red-DiscordBot
async def setup(bot):
    """Setup function for Red-DiscordBot cog loading"""
    
    # Create and setup the main crew management cog
    crew_cog = CrewManagement(bot)
    
    # Add migration functionality if available
    if MIGRATION_AVAILABLE:
        try:
            setup_migration(crew_cog)
        except Exception as e:
            print(f"Failed to setup migration: {e}")
    
    # Add the cog to the bot
    await bot.add_cog(crew_cog)
    
    # Setup tournament system if available
    if TOURNAMENT_AVAILABLE:
        try:
            tournament_cog = TournamentSystem(bot)
            tournament_cog.set_crew_manager(crew_cog)  
            await bot.add_cog(tournament_cog)
        except Exception as e:
            print(f"Failed to load tournament system: {e}")

# Package exports
__all__ = [
    "CrewManagement",
    "setup"
]