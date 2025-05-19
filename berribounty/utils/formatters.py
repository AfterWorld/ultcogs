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

def format_health_bar(current: int, maximum: int, length: int = 20) -> str:
    """Create a health bar using Unicode characters."""
    if maximum <= 0:
        return "▱" * length
    
    filled = int((current / maximum) * length)
    empty = length - filled
    
    # Use different characters based on health percentage
    health_percent = current / maximum
    if health_percent > 0.6:
        fill_char = "█"  # Green
    elif health_percent > 0.3:
        fill_char = "▓"  # Yellow
    else:
        fill_char = "▒"  # Red
    
    return fill_char * filled + "▱" * empty

def format_mp_bar(current: int, maximum: int = 100, length: int = 20) -> str:
    """Create an MP bar using Unicode characters."""
    if maximum <= 0:
        return "▱" * length
    
    filled = int((current / maximum) * length)
    empty = length - filled
    
    return "▰" * filled + "▱" * empty

def create_embed_field_chunks(content: str, max_length: int = 1024) -> List[str]:
    """Split content into chunks that fit in embed fields."""
    if len(content) <= max_length:
        return [content]
    
    chunks = []
    current_chunk = ""
    
    for line in content.split('\n'):
        if len(current_chunk + line + '\n') > max_length:
            if current_chunk:
                chunks.append(current_chunk.rstrip())
                current_chunk = line + '\n'
            else:
                # Single line too long, split it
                while len(line) > max_length:
                    chunks.append(line[:max_length])
                    line = line[max_length:]
                current_chunk = line + '\n'
        else:
            current_chunk += line + '\n'
    
    if current_chunk:
        chunks.append(current_chunk.rstrip())
    
    return chunks

def format_leaderboard(data: List[tuple], title: str, value_formatter=None) -> discord.Embed:
    """Create a formatted leaderboard embed."""
    embed = discord.Embed(
        title=f"🏆 {title}",
        color=discord.Color.gold()
    )
    
    if not data:
        embed.description = "No data available yet!"
        return embed
    
    medals = ["🥇", "🥈", "🥉"]
    leaderboard_text = ""
    
    for i, (player_name, value) in enumerate(data[:10]):  # Top 10
        rank = i + 1
        medal = medals[i] if i < 3 else f"{rank}."
        
        if value_formatter:
            formatted_value = value_formatter(value)
        else:
            formatted_value = str(value)
        
        leaderboard_text += f"{medal} **{player_name}** - {formatted_value}\n"
    
    embed.description = leaderboard_text
    embed.set_footer(text=f"Top {min(len(data), 10)} players")
    
    return embed

def format_devil_fruit_info(fruit_name: str, fruit_data: Dict[str, Any]) -> discord.Embed:
    """Format devil fruit information into an embed."""
    embed = discord.Embed(
        title=f"🍎 {fruit_name}",
        description=fruit_data.get("description", "A mysterious devil fruit..."),
        color=discord.Color.red() if "rare" in fruit_data.get("rarity", "") else discord.Color.orange()
    )
    
    # Basic info
    embed.add_field(
        name="Type",
        value=fruit_data.get("type", "Unknown"),
        inline=True
    )
    
    embed.add_field(
        name="Category",
        value=fruit_data.get("category", "Unknown"),
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

def format_battle_log_entry(entry: Dict[str, Any]) -> str:
    """Format a battle log entry."""
    timestamp = datetime.fromtimestamp(entry.get("timestamp", 0))
    time_str = timestamp.strftime("%H:%M:%S")
    message = entry.get("message", "")
    
    return f"`{time_str}` {message}"

def format_achievement(achievement: Dict[str, Any]) -> str:
    """Format an achievement for display."""
    name = achievement.get("name", "Unknown Achievement")
    description = achievement.get("description", "")
    reward = achievement.get("reward", {})
    
    reward_text = ""
    if reward:
        if "berries" in reward:
            reward_text += f" (+{reward['berries']:,} ฿)"
        if "title" in reward:
            reward_text += f" (Title: {reward['title']})"
    
    return f"**{name}**{reward_text}\n*{description}*"

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

class ProgressBar:
    """Create customizable progress bars."""
    
    def __init__(self, length: int = 20):
        self.length = length
    
    def create(self, current: int, maximum: int, 
               filled_char: str = "█", empty_char: str = "▱") -> str:
        """Create a progress bar."""
        if maximum <= 0:
            return empty_char * self.length
        
        filled = int((current / maximum) * self.length)
        empty = self.length - filled
        
        return filled_char * filled + empty_char * empty
    
    def create_with_percentage(self, current: int, maximum: int,
                             filled_char: str = "█", empty_char: str = "▱") -> str:
        """Create a progress bar with percentage."""
        bar = self.create(current, maximum, filled_char, empty_char)
        percentage = (current / maximum * 100) if maximum > 0 else 0
        return f"{bar} {percentage:.1f}%"

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

def format_large_number(number: int) -> str:
    """Format large numbers with suffixes (K, M, B)."""
    if number < 1000:
        return str(number)
    elif number < 1_000_000:
        return f"{number/1000:.1f}K"
    elif number < 1_000_000_000:
        return f"{number/1_000_000:.1f}M"
    else:
        return f"{number/1_000_000_000:.1f}B"

def create_status_indicator(status: str) -> str:
    """Create a colored status indicator."""
    indicators = {
        "online": "🟢",
        "idle": "🟡", 
        "dnd": "🔴",
        "offline": "⚫",
        "active": "🟢",
        "inactive": "🔴",
        "ready": "✅",
        "busy": "🟡",
        "error": "❌"
    }
    return indicators.get(status.lower(), "⚪")