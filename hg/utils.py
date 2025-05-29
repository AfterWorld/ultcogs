# utils.py
"""Utility functions for Hunger Games cog"""

import discord
import random
from typing import Dict, List, Optional
from .constants import DISTRICTS, EMOJIS, PLACEMENT_MEDALS, VICTORY_TITLE_ART, PLAYER_TITLES


def format_player_list(players: Dict, show_districts: bool = True, show_status: bool = True) -> str:
    """Format player list for display"""
    if not players:
        return "No players"
    
    lines = []
    for player_id, player_data in players.items():
        line = f"**{player_data['name']}** {player_data.get('title', 'the Nameless')}"
        
        if show_districts:
            district_name = DISTRICTS.get(player_data['district'], f"District {player_data['district']}")
            line += f" - {district_name}"
        
        if show_status:
            if player_data['alive']:
                line += f" {EMOJIS['heart']}"
                if player_data['kills'] > 0:
                    line += f" ({player_data['kills']} kills)"
            else:
                line += f" {EMOJIS['skull']}"
        
        lines.append(line)
    
    return "\n".join(lines)


def get_random_district() -> int:
    """Get a random district number"""
    return random.randint(1, 12)


def get_random_player_title() -> str:
    """Get a random player title/epithet"""
    return random.choice(PLAYER_TITLES)


def format_time_remaining(seconds: int) -> str:
    """Format seconds into a readable time string"""
    if seconds >= 60:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds > 0:
            return f"{minutes}m {remaining_seconds}s"
        return f"{minutes}m"
    return f"{seconds}s"


def create_recruitment_embed(countdown: int, current_players: int = 0) -> discord.Embed:
    """Create the recruitment embed"""
    embed = discord.Embed(
        title="🏹 **THE HUNGER GAMES** 🏹",
        description=f"**A deadly battle royale is about to begin!**\n\n"
                   f"🔥 **React with {EMOJIS['bow']} to enter the arena!**\n"
                   f"⏰ Recruitment ends in **{format_time_remaining(countdown)}**\n\n"
                   f"💰 **Prize Pool:** *Scales with participants*\n"
                   f"🎯 **Sponsor Revivals:** *Possible during the games*\n\n"
                   f"*May the odds be ever in your favor...*",
        color=0x8B0000
    )
    
    if current_players > 0:
        embed.add_field(
            name="👥 **Current Tributes**",
            value=f"{current_players} brave souls",
            inline=True
        )
    
    embed.set_footer(text="React quickly - the arena waits for no one!")
    return embed


def create_game_start_embed(total_players: int) -> discord.Embed:
    """Create the game start embed"""
    embed = discord.Embed(
        title="🎺 **LET THE GAMES BEGIN!** 🎺",
        description=f"**{total_players} tributes enter the arena!**\n\n"
                   f"The Cornucopia gleams in the distance, packed with supplies...\n"
                   f"Who will claim the weapons? Who will flee?\n\n"
                   f"*The countdown begins... 3... 2... 1...*",
        color=0xFF6B35
    )
    
    embed.set_footer(text="The 75th Annual Hunger Games have begun!")
    return embed


def create_player_stats_embed(member_data: Dict, member: discord.Member) -> discord.Embed:
    """Create player statistics embed"""
    embed = discord.Embed(
        title=f"📊 **{member.display_name}'s Hunger Games Stats**",
        color=0x00CED1
    )
    
    wins = member_data.get("wins", 0)
    deaths = member_data.get("deaths", 0)
    kills = member_data.get("kills", 0)
    revives = member_data.get("revives", 0)
    
    total_games = wins + deaths
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    embed.add_field(
        name="🏆 **Victories**",
        value=str(wins),
        inline=True
    )
    
    embed.add_field(
        name="💀 **Deaths**",
        value=str(deaths),
        inline=True
    )
    
    embed.add_field(
        name="⚔️ **Total Kills**",
        value=str(kills),
        inline=True
    )
    
    embed.add_field(
        name="✨ **Revives**",
        value=str(revives),
        inline=True
    )
    
    embed.add_field(
        name="🎮 **Games Played**",
        value=str(total_games),
        inline=True
    )
    
    embed.add_field(
        name="📈 **Win Rate**",
        value=f"{win_rate:.1f}%",
        inline=True
    )
    
    if total_games > 0:
        avg_kills = kills / total_games
        embed.add_field(
            name="🎯 **Avg Kills/Game**",
            value=f"{avg_kills:.1f}",
            inline=True
        )
    
    # Add rank/title based on performance
    if wins >= 10:
        title = "🌟 **Legendary Champion**"
    elif wins >= 5:
        title = "👑 **Elite Victor**"
    elif wins >= 3:
        title = "🥇 **Veteran Survivor**"
    elif wins >= 1:
        title = "🏹 **Arena Survivor**"
    else:
        title = "🆕 **Fresh Tribute**"
    
    embed.add_field(
        name="🎭 **Rank**",
        value=title,
        inline=False
    )
    
    return embed


def create_leaderboard_embed(guild: discord.Guild, top_players: List, stat_type: str = "wins") -> discord.Embed:
    """Create leaderboard embed"""
    stat_names = {
        "wins": "🏆 **Victory Leaderboard**",
        "kills": "⚔️ **Kill Leaderboard**", 
        "deaths": "💀 **Death Leaderboard**",
        "revives": "✨ **Revival Leaderboard**"
    }
    
    embed = discord.Embed(
        title=stat_names.get(stat_type, "📊 **Leaderboard**"),
        color=0xFFD700
    )
    
    if not top_players:
        embed.description = "No statistics available yet!"
        return embed
    
    medals = ["🥇", "🥈", "🥉"]
    description_lines = []
    
    for i, (member_id, stats) in enumerate(top_players[:10]):
        member = guild.get_member(member_id)
        if not member:
            continue
            
        medal = medals[i] if i < 3 else f"**{i+1}.**"
        value = stats.get(stat_type, 0)
        
        description_lines.append(f"{medal} {member.display_name} - {value}")
    
    embed.description = "\n".join(description_lines) if description_lines else "No data available"
    
    return embed


def validate_countdown(countdown: int) -> tuple[bool, str]:
    """Validate countdown time"""
    if countdown < 10:
        return False, "Countdown must be at least 10 seconds!"
    elif countdown > 300:
        return False, "Countdown cannot exceed 5 minutes!"
    return True, ""


def get_event_weights() -> Dict[str, int]:
    """Get event type weights based on game state - now includes crate events"""
    return {
        "death": 30,      # 30% chance (reduced to make room for crates)
        "survival": 25,   # 25% chance  
        "sponsor": 15,    # 15% chance
        "alliance": 15,   # 15% chance
        "crate": 15       # 15% chance (NEW!)
    }


def should_execute_event(alive_count: int, round_num: int) -> bool:
    """Determine if an event should happen this round"""
    # With small player counts, always have events to make it interesting
    if alive_count <= 3:
        return True  # Always have events with 2-3 players
    elif alive_count <= 5:
        return random.random() < 0.95  # 95% chance with 4-5 players
    elif alive_count <= 10:
        return random.random() < 0.8   # 80% chance with 6-10 players
    elif alive_count <= 15:
        return random.random() < 0.7   # 70% chance with 11-15 players
    else:
        return random.random() < 0.6   # 60% chance with 16+ players


def get_game_phase_description(round_num: int, alive_count: int) -> str:
    """Get description of current game phase"""
    if alive_count <= 2:
        return "🔥 **FINAL DUEL** - Only two remain!"
    elif alive_count <= 5:
        return "⚔️ **FINAL FIVE** - The end is near..."
    elif alive_count <= 10:
        return "💀 **TOP TEN** - The arena grows smaller..."
    elif round_num < 5:
        return "🌅 **EARLY GAME** - The hunt begins..."
    elif round_num < 15:
        return "🌞 **MID GAME** - Alliances form and break..."
    else:
        return "🌙 **LATE GAME** - Desperation sets in..."
