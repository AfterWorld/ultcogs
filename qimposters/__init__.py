# __init__.py
"""
One Piece Question Imposters - A social deduction game for Red-DiscordBot
"""

from .onepiece_imposters import OnePieceImposters

__red_end_user_data_statement__ = (
    "This cog stores the following user data:\n"
    "- User IDs for game participation tracking\n"
    "- Game scores and statistics during active sessions\n"
    "- No persistent user data is stored beyond active game sessions\n"
    "- All data is cleared when games end or the bot restarts"
)

async def setup(bot):
    """Setup function for loading the cog"""
    try:
        await bot.add_cog(OnePieceImposters(bot))
    except Exception as e:
        # Log any setup errors for debugging
        import logging
        log = logging.getLogger("red.onepiece_imposters")
        log.error(f"Failed to load OnePieceImposters cog: {e}", exc_info=True)
        raise
