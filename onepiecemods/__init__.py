# onepiecemods/__init__.py - Updated with Advanced Integration
from .onepiecemods import OnePieceMods
from .utils.config_manager import ConfigManager
from .utils.webhook_logger import WebhookLogger
import logging

logger = logging.getLogger("red.onepiecemods")

async def setup(bot):
    """Load the OnePieceMods cog with advanced features."""
    try:
        # Create the main cog instance
        cog = OnePieceMods(bot)
        
        # Initialize advanced components
        config_manager = ConfigManager(bot, cog.config)
        webhook_logger = WebhookLogger(bot, config_manager)
        
        # Inject advanced components into the cog
        cog.config_manager = config_manager
        cog.webhook_logger = webhook_logger
        
        # Start the background task when cog is loaded
        bot.loop.create_task(cog.init_task())
        
        # Add the cog to the bot
        await bot.add_cog(cog)
        
        logger.info("One Piece Mods loaded successfully with advanced features")
        
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
            
            # Clean up webhook data for all guilds
            if hasattr(cog, 'webhook_logger'):
                for guild in bot.guilds:
                    await cog.webhook_logger.cleanup_guild_data(guild.id)
        
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
    "ConfigManager", 
    "WebhookLogger",
    "setup",
    "teardown"
]
