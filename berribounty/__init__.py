"""
One Piece Discord Bot Cog
=========================

A comprehensive One Piece themed Discord bot cog featuring:

* Interactive battle system with devil fruit abilities
* Berries economy with daily rewards, work, and gambling
* Devil fruit collection with mastery progression
* Achievement system with unlockable titles
* Admin management tools

Modules:
    core: Main cog class and command definitions
    ui: User interface components (views, modals, etc.)
    commands: Command handler classes
    models: Data models for players, battles, etc.
    managers: Business logic managers
    constants: Configuration data and constants

Usage:
    Load this cog into your Red-DiscordBot instance:
    ```python
    await bot.load_extension('onepiece')
    ```

Requirements:
    - Red-DiscordBot 3.5+
    - discord.py 2.0+
    - Python 3.8+

Author: UltPanda
Version: 1.0.0
License: MIT
"""

from .core import OnePiece

__version__ = "1.0.0"
__author__ = "UltPanda"
__license__ = "MIT"
__all__ = ["OnePiece", "setup"]

# Version information
version_info = (1, 0, 0)

async def setup(bot):
    """
    Setup function for loading the cog.
    
    Args:
        bot: The Red-DiscordBot instance
        
    Raises:
        Exception: If cog setup fails
    """
    try:
        cog = OnePiece(bot)
        await bot.add_cog(cog)
        print(f"[One Piece] Cog loaded successfully (v{__version__})")
    except Exception as e:
        print(f"[One Piece] Failed to load cog: {e}")
        raise

async def teardown(bot):
    """
    Teardown function for unloading the cog.
    
    Args:
        bot: The Red-DiscordBot instance
    """
    print("[One Piece] Cog unloaded")