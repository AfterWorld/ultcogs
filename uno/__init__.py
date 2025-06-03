"""
Uno Game Cog Package
A comprehensive Uno card game implementation for Red-Discord bots
"""

from .uno_backup import UnoCog, setup

__version__ = "1.0.0"
__author__ = "Uno Cog Developer"
__description__ = "A comprehensive Uno card game cog with Discord UI integration"

# Package exports
__all__ = [
    "UnoCog",
    "setup",
]

# Package information
__package_info__ = {
    "name": "uno",
    "version": __version__,
    "description": __description__,
    "author": __author__,
    "requires": [
        "discord.py>=2.0.0",
        "Pillow>=8.0.0",
    ],
    "min_bot_version": "3.5.0",
    "min_python_version": [3, 8, 0],
}