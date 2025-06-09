"""
OPE (One Piece Engagement) - Ultimate One Piece Engagement System for Red-DiscordBot

A comprehensive One Piece themed engagement system featuring:
- Daily challenges with themed content
- Multi-difficulty trivia system  
- Auto trivia posting
- Point system and rankings
- Leaderboards and achievements
- Easy file-based content management

Author: UltPanda
Version: 1.0.0
"""

from .ope import OnePieceMaster

__red_end_user_data_statement__ = (
    "This cog stores user data including points earned, trivia statistics, "
    "daily streaks, achievements, and participation in challenges. "
    "This data is used to track progress, display leaderboards, and provide "
    "a gamified experience. Users can request deletion of their data."
)


async def setup(bot):
    """Load the OPE (One Piece Engagement) cog"""
    cog = OPE(bot)
    await bot.add_cog(cog)


async def teardown(bot):
    """Clean up when unloading the cog"""
    cog = bot.get_cog("OPE")
    if cog:
        # Cancel any running tasks
        if hasattr(cog, 'daily_challenge_task'):
            cog.daily_challenge_task.cancel()
        if hasattr(cog, 'auto_trivia_task'):
            cog.auto_trivia_task.cancel()
