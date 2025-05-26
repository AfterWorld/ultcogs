"""
Advanced League of Legends Cog for Red-DiscordBot - Fixed Version

A comprehensive League of Legends integration featuring:
- Advanced live game analysis with win probability calculations
- Community achievements and leaderboards  
- Enhanced Discord embeds with interactive elements
- League Client (LCU) integration for auto-accept and real-time features
- Professional-grade analytics and performance tracking

This version includes graceful error handling for missing dependencies.

Author: UltPanda
Version: 2.0.1
Red-DiscordBot Version: 3.4.0+
"""

import logging

# Set up logging for the package
logger = logging.getLogger(__name__)

# Try to import the main cog class with error handling
try:
    from .advancedlol import AdvancedLoLv2
    COG_LOADED = True
    logger.info("Advanced LoL cog package loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import main cog class: {e}")
    COG_LOADED = False
    AdvancedLoLv2 = None
except Exception as e:
    logger.error(f"Unexpected error loading cog package: {e}")
    COG_LOADED = False
    AdvancedLoLv2 = None

__red_end_user_data_statement__ = (
    "This cog stores Discord user IDs, summoner names, regions, and achievement data. "
    "Users can request deletion of their data via the bot commands. "
    "Riot API keys are stored globally for bot functionality. "
    "No personal data is shared with third parties."
)

__version__ = "2.0.1"
__author__ = "Advanced LoL Cog Developer"


async def setup(bot):
    """Load the Advanced LoL cog with error handling"""
    if not COG_LOADED or AdvancedLoLv2 is None:
        raise RuntimeError(
            "Advanced LoL cog failed to load. Check the following:\n"
            "1. All required files are present in the cog directory\n"
            "2. Dependencies are installed: pip install aiohttp\n"
            "3. Check bot logs for specific error details"
        )
    
    try:
        cog = AdvancedLoLv2(bot)
        await bot.add_cog(cog)
        logger.info("Advanced LoL cog added to bot successfully")
    except Exception as e:
        logger.error(f"Error adding cog to bot: {e}")
        raise


async def teardown(bot):
    """Unload the Advanced LoL cog"""
    try:
        # Cleanup is handled in cog_unload
        logger.info("Advanced LoL cog teardown completed")
    except Exception as e:
        logger.error(f"Error during cog teardown: {e}")


# Version and compatibility checks
def check_dependencies():
    """Check if required dependencies are available"""
    missing_deps = []
    optional_deps = []
    
    # Check required dependencies
    try:
        import aiohttp
    except ImportError:
        missing_deps.append("aiohttp")
    
    # Check optional dependencies
    try:
        import websockets
    except ImportError:
        optional_deps.append("websockets (for LCU features)")
    
    try:
        import psutil
    except ImportError:
        optional_deps.append("psutil (for LCU auto-detection)")
    
    return missing_deps, optional_deps


def get_installation_help():
    """Get help text for installation issues"""
    missing_deps, optional_deps = check_dependencies()
    
    help_text = "Advanced LoL Cog Installation Help\n" + "=" * 40 + "\n\n"
    
    if missing_deps:
        help_text += "❌ REQUIRED dependencies missing:\n"
        help_text += f"   Install with: pip install {' '.join(missing_deps)}\n\n"
    else:
        help_text += "✅ All required dependencies are installed\n\n"
    
    if optional_deps:
        help_text += "⚠️  Optional dependencies (for enhanced features):\n"
        for dep in optional_deps:
            help_text += f"   • {dep}\n"
        help_text += f"   Install with: pip install {' '.join([d.split()[0] for d in optional_deps])}\n\n"
    
    help_text += "📋 Manual Installation Steps:\n"
    help_text += "1. Place all cog files in: [botdir]/cogs/AdvancedLoL/\n"
    help_text += "2. Install dependencies: pip install -r requirements.txt\n"
    help_text += "3. Load the cog: [p]load AdvancedLoL\n"
    help_text += "4. Set API key: [p]lol setkey RGAPI-your-key-here\n\n"
    
    help_text += "🔧 Troubleshooting:\n"
    help_text += "• Check bot logs for specific error messages\n"
    help_text += "• Ensure Red-DiscordBot version 3.4.0+\n"
    help_text += "• Verify file permissions in cog directory\n"
    help_text += "• Restart bot after installing dependencies\n"
    
    return help_text


# Export main components for external use
__all__ = [
    'AdvancedLoLv2',
    'setup',
    'teardown',
    'check_dependencies',
    'get_installation_help',
    '__version__',
    '__author__'
]

# Log package status on import
if COG_LOADED:
    missing_deps, optional_deps = check_dependencies()
    if missing_deps:
        logger.warning(f"Missing required dependencies: {', '.join(missing_deps)}")
    if optional_deps:
        logger.info(f"Optional dependencies not installed: {', '.join(optional_deps)}")
else:
    logger.error("Advanced LoL cog package failed to load - check imports and dependencies")
