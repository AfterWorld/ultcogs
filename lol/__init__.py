"""
Advanced League of Legends Cog for Red-DiscordBot

A comprehensive League of Legends integration featuring:
- Advanced live game analysis with win probability calculations
- Community achievements and leaderboards  
- Enhanced Discord embeds with interactive elements
- League Client (LCU) integration for auto-accept and real-time features
- Professional-grade analytics and performance tracking

Author: UltPanda
Version: 2.0.0
Red-DiscordBot Version: 3.4.0+
"""

from .advancedlol import AdvancedLoLv2

__red_end_user_data_statement__ = (
    "This cog stores Discord user IDs, summoner names, regions, and achievement data. "
    "Users can request deletion of their data via the bot commands. "
    "Riot API keys are stored globally for bot functionality. "
    "No personal data is shared with third parties."
)

__version__ = "2.0.0"
__author__ = "Advanced LoL Cog Developer"


async def setup(bot):
    """Load the Advanced LoL cog"""
    cog = AdvancedLoLv2(bot)
    await bot.add_cog(cog)


def teardown(bot):
    """Unload the Advanced LoL cog"""
    # Cleanup is handled in cog_unload
    pass
