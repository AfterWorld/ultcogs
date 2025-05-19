"""Formatting utilities for the One Piece bot."""

import discord
from typing import Union, List, Dict, Any
from datetime import datetime, timedelta

def format_berries(amount: int) -> str:
    """Format berries with proper comma separation and symbol."""
    return f"{amount:,} ฿"

def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a percentage value."""
    return f"{value:.{decimals}f}%"

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def format_timestamp(timestamp: float, style: str = "R") -> str:
    """Format timestamp for Discord."""
    return f"<t:{int(timestamp)}:{style}>"

def format_battle_stats(stats: Dict[str, Any]) -> str:
    """Format battle statistics for display."""
    return (
        f"**Damage Dealt:** {stats.get('damage_dealt', 0):,}\n"
        f"**Damage Taken:** {stats.get('damage_taken', 0):,}\n"
        f"**Healing Done:** {stats.get('healing_done', 0):,}\n"
        f"**Critical Hits:** {stats.get('critical_hits', 0)}\n"
        f"**Perfect Wins:** {stats.get('perfect_wins', 0)}"
    )

def format_devil_fruit_info(fruit_name: str, fruit_data: Dict[str, Any]) -> discord.Embed:
    """Format devil fruit information into an embed."""
    embed = discord.Embed(
        title=f"🍎 {fruit_name}",
        description=fruit_data.get("description", "A mysterious devil fruit..."),
        color=discord.Color.red()
    )
    
    # Basic info
    embed.add_field(
        name="Type",
        value=fruit_data.get("type", "Unknown"),
        inline=True
    )
    
    # Abilities
    if "abilities" in fruit_data:
        abilities_text = "\n".join([f"• {ability}" for ability in fruit_data["abilities"]])
        embed.add_field(
            name="Abilities",
            value=abilities_text,
            inline=False
        )
    
    # Special moves
    if "moves" in fruit_data:
        moves_text = ""
        for move in fruit_data["moves"][:5]:  # Limit to 5 moves
            moves_text += f"**{move['name']}** - {move.get('description', 'Special move')}\n"
        
        if moves_text:
            embed.add_field(
                name="Special Moves",
                value=moves_text,
                inline=False
            )
    
    # Weaknesses
    if "weaknesses" in fruit_data:
        weaknesses_text = "\n".join([f"• {weakness}" for weakness in fruit_data["weaknesses"]])
        embed.add_field(
            name="⚠️ Weaknesses",
            value=weaknesses_text,
            inline=False
        )
    
    return embed

def format_time_remaining(seconds: int) -> str:
    """Format time remaining in a user-friendly way."""
    if seconds <= 0:
        return "Ready now!"
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h {remaining_minutes}m"
