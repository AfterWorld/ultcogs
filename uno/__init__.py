"""
Uno Game Cog Package
A comprehensive Uno card game implementation for Red-DiscordBot V3
"""

from .uno import setup

__red_end_user_data_statement__ = (
    "This cog stores game session data temporarily while games are active. "
    "No persistent user data is stored beyond the current game session. "
    "Game data is automatically cleaned up when games end or timeout."
)