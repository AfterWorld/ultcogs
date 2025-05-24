# onepiecemods/__init__.py - Simplified Version
from .onepiecemods import OnePieceMods
import logging

logger = logging.getLogger("red.onepiecemods")

async def setup(bot):
    """Load the OnePieceMods cog."""
    try:
        # Create the main cog instance
        cog = OnePieceMods(bot)
        
        # Start the background task when cog is loaded
        bot.loop.create_task(cog.init_task())
        
        # Add the cog to the bot
        await bot.add_cog(cog)
        
        logger.info("One Piece Mods loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load One Piece Mods: {e}")
        raise

async def teardown(bot):
    """Clean up when the cog is unloaded."""
    try:
        cog = bot.get_cog("OnePieceMods")
        if cog:
            # Clean up background tasks
            if hasattr(cog, 'bg_task') and cog.bg_task:
                cog.bg_task.cancel()
            
            if hasattr(cog, 'init_casetypes_task') and cog.init_casetypes_task:
                cog.init_casetypes_task.cancel()
        
        logger.info("One Piece Mods unloaded successfully")
        
    except Exception as e:
        logger.error(f"Error during One Piece Mods teardown: {e}")

# Export version info
__version__ = "2.0.0"
__author__ = "One Piece Mods Team"
__description__ = "Advanced One Piece themed moderation system for Discord"

# Export main classes for external use
__all__ = [
    "OnePieceMods",
    "setup",
    "teardown"
]