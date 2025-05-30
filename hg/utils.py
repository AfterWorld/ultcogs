# utils.py - IMPROVED VERSION
"""Enhanced utility functions for Hunger Games cog with better error handling"""

import discord
import random
import logging
from typing import Dict, List, Optional, Tuple, Union
from .constants import DISTRICTS, EMOJIS, PLACEMENT_MEDALS, VICTORY_TITLE_ART, PLAYER_TITLES
from .config import game_config_manager

# Set up logging
logger = logging.getLogger(__name__)

class PlayerListFormatter:
    """Handles player list formatting with various options"""
    
    @staticmethod
    def format_player_list(players: Dict, show_districts: bool = True, 
                          show_status: bool = True, max_players: Optional[int] = None) -> str:
        """Format player list for display with error handling"""
        try:
            if not players:
                return "No players"
            
            lines = []
            player_items = list(players.items())
            
            # Limit number of players shown if specified
            if max_players and len(player_items) > max_players:
                player_items = player_items[:max_players]
                truncated = True
            else:
                truncated = False
            
            for player_id, player_data in player_items:
                line = PlayerListFormatter._format_single_player(
                    player_data, show_districts, show_status
                )
                if line:
                    lines.append(line)
            
            result = "\n".join(lines)
            
            # Add truncation notice if needed
            if truncated:
                remaining = len(players) - max_players
                result += f"\n*... and {remaining} more players*"
            
            return result if result else "No valid players"
            
        except Exception as e:
            logger.error(f"Error formatting player list: {e}")
            return f"Error displaying {len(players)} players"
    
    @staticmethod
    def _format_single_player(player_data: Dict, show_districts: bool, show_status: bool) -> str:
        """Format a single player entry"""
        try:
            name = player_data.get('name', 'Unknown')
            title = player_data.get('title', 'the Nameless')
            line = f"**{name}** {title}"
            
            if show_districts:
                district_num = player_data.get('district', 1)
                district_name = DISTRICTS.get(district_num, f"District {district_num}")
                line += f" - {district_name}"
            
            if show_status:
                if player_data.get('alive', False):
                    line += f" {EMOJIS.get('heart', '❤️')}"
                    kills = player_data.get('kills', 0)
                    if kills > 0:
                        line += f" ({kills} kills)"
                else:
                    line += f" {EMOJIS.get('skull', '💀')}"
            
            return line
            
        except Exception as e:
            logger.error(f"Error formatting single player: {e}")
            return f"**{player_data.get('name', 'Unknown')}** (display error)"


class RandomGenerators:
    """Handles random generation for game elements"""
    
    @staticmethod
    def get_random_district() -> int:
        """Get a random district number (1-12)"""
        return random.randint(1, 12)
    
    @staticmethod
    def get_random_player_title() -> str:
        """Get a random player title/epithet with fallback"""
        try:
            if not PLAYER_TITLES:
                return "the Brave"
            return random.choice(PLAYER_TITLES)
        except Exception as e:
            logger.error(f"Error getting random title: {e}")
            return "the Survivor"
    
    @staticmethod
    def get_random_victory_art() -> str:
        """Get random victory art with fallback"""
        try:
            if not VICTORY_TITLE_ART:
                return "```\n🏹 THE HUNGER GAMES 🏹\n```"
            return random.choice(VICTORY_TITLE_ART)
        except Exception as e:
            logger.error(f"Error getting victory art: {e}")
            return "```\n🏹 THE HUNGER GAMES 🏹\n```"


class TimeFormatter:
    """Handles time formatting and countdown display"""
    
    @staticmethod
    def format_time_remaining(seconds: int) -> str:
        """Format seconds into a readable time string"""
        try:
            if seconds < 0:
                return "0s"
            
            if seconds >= 3600:  # 1 hour or more
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                remaining_seconds = seconds % 60
                
                parts = [f"{hours}h"]
                if minutes > 0:
                    parts.append(f"{minutes}m")
                if remaining_seconds > 0:
                    parts.append(f"{remaining_seconds}s")
                
                return " ".join(parts)
            elif seconds >= 60:
                minutes = seconds // 60
                remaining_seconds = seconds % 60
                if remaining_seconds > 0:
                    return f"{minutes}m {remaining_seconds}s"
                return f"{minutes}m"
            else:
                return f"{seconds}s"
        except Exception as e:
            logger.error(f"Error formatting time: {e}")
            return f"{seconds}s"
    
    @staticmethod
    def get_urgency_color(seconds: int) -> int:
        """Get color based on time urgency"""
        try:
            if seconds <= 10:
                return 0xFF0000  # Red - urgent
            elif seconds <= 30:
                return 0xFF8000  # Orange - warning
            elif seconds <= 60:
                return 0xFFFF00  # Yellow - caution
            else:
                return 0x00FF00  # Green - plenty of time
        except Exception:
            return 0x808080  # Gray - default


class EmbedBuilder:
    """Handles creation of various Discord embeds"""
    
    @staticmethod
    def create_recruitment_embed(countdown: int, current_players: int = 0) -> discord.Embed:
        """Create the recruitment embed with enhanced formatting"""
        try:
            time_str = TimeFormatter.format_time_remaining(countdown)
            color = TimeFormatter.get_urgency_color(countdown)
            
            description = (
                f"**A deadly battle royale is about to begin!**\n\n"
                f"🔥 **React with {EMOJIS.get('bow', '🏹')} to enter the arena!**\n"
                f"⏰ Recruitment ends in **{time_str}**\n\n"
                f"💰 **Prize Pool:** *Scales with participants*\n"
                f"🎯 **Sponsor Revivals:** *Possible during the games*\n\n"
                f"*May the odds be ever in your favor...*"
            )
            
            embed = discord.Embed(
                title="🏹 **THE HUNGER GAMES** 🏹",
                description=description,
                color=color
            )
            
            if current_players > 0:
                embed.add_field(
                    name="👥 **Current Tributes**",
                    value=f"{current_players} brave souls",
                    inline=True
                )
            
            # Add different footer messages based on time
            if countdown <= 30:
                footer_text = "⚠️ Last chance to join!"
            elif countdown <= 60:
                footer_text = "⏰ Time running out!"
            else:
                footer_text = "React quickly - the arena waits for no one!"
            
            embed.set_footer(text=footer_text)
            return embed
            
        except Exception as e:
            logger.error(f"Error creating recruitment embed: {e}")
            return discord.Embed(
                title="🏹 Hunger Games",
                description="Battle royale starting soon!",
                color=0x8B0000
            )
    
    @staticmethod
    def create_game_start_embed(total_players: int) -> discord.Embed:
        """Create the game start embed with player count awareness"""
        try:
            if total_players <= 4:
                title = "⚡ **LIGHTNING ROUND BEGINS!** ⚡"
                description = (
                    f"**{total_players} tributes enter the arena!**\n\n"
                    f"With so few competitors, this will be intense and fast-paced!\n"
                    f"Every move matters... every second counts...\n\n"
                    f"*The countdown begins... 3... 2... 1...*"
                )
                color = 0xFF4500  # Orange-red for intensity
            elif total_players <= 8:
                title = "🔥 **SMALL ARENA SHOWDOWN!** 🔥"
                description = (
                    f"**{total_players} tributes enter the arena!**\n\n"
                    f"A compact but fierce battle awaits!\n"
                    f"The Cornucopia gleams with opportunity...\n\n"
                    f"*The countdown begins... 3... 2... 1...*"
                )
                color = 0xFF6B35  # Orange
            else:
                title = "🎺 **LET THE GAMES BEGIN!** 🎺"
                description = (
                    f"**{total_players} tributes enter the arena!**\n\n"
                    f"The Cornucopia gleams in the distance, packed with supplies...\n"
                    f"Who will claim the weapons? Who will flee?\n\n"
                    f"*The countdown begins... 3... 2... 1...*"
                )
                color = 0xFF6B35  # Standard orange
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=color
            )
            
            embed.set_footer(text="The Hunger Games have begun!")
            return embed
            
        except Exception as e:
            logger.error(f"Error creating game start embed: {e}")
            return discord.Embed(
                title="🎺 Game Starting!",
                description=f"{total_players} players have entered the arena!",
                color=0xFF6B35
            )
    
    @staticmethod
    def create_player_stats_embed(member_data: Dict, member: discord.Member) -> discord.Embed:
        """Create player statistics embed with enhanced metrics"""
        try:
            embed = discord.Embed(
                title=f"📊 **{member.display_name}'s Hunger Games Stats**",
                color=0x00CED1
            )
            
            # Basic stats
            wins = member_data.get("wins", 0)
            deaths = member_data.get("deaths", 0)
            kills = member_data.get("kills", 0)
            revives = member_data.get("revives", 0)
            
            total_games = wins + deaths
            win_rate = (wins / total_games * 100) if total_games > 0 else 0
            
            # Primary stats (top row)
            embed.add_field(name="🏆 **Victories**", value=str(wins), inline=True)
            embed.add_field(name="💀 **Deaths**", value=str(deaths), inline=True)
            embed.add_field(name="⚔️ **Total Kills**", value=str(kills), inline=True)
            
            # Secondary stats (middle row)
            embed.add_field(name="✨ **Revives**", value=str(revives), inline=True)
            embed.add_field(name="🎮 **Games Played**", value=str(total_games), inline=True)
            embed.add_field(name="📈 **Win Rate**", value=f"{win_rate:.1f}%", inline=True)
            
            # Advanced stats if games played
            if total_games > 0:
                avg_kills = kills / total_games
                embed.add_field(
                    name="🎯 **Avg Kills/Game**",
                    value=f"{avg_kills:.1f}",
                    inline=True
                )
                
                survival_rate = (wins / total_games * 100) if total_games > 0 else 0
                embed.add_field(
                    name="🛡️ **Survival Rate**", 
                    value=f"{survival_rate:.1f}%",
                    inline=True
                )
                
                if kills > 0:
                    kd_ratio = kills / deaths if deaths > 0 else kills
                    embed.add_field(
                        name="⚡ **K/D Ratio**",
                        value=f"{kd_ratio:.2f}",
                        inline=True
                    )
            
            # Rank/title based on performance
            title, title_color = StatsCalculator.calculate_player_rank(wins, total_games, kills)
            embed.add_field(
                name="🎭 **Rank**",
                value=title,
                inline=False
            )
            
            # Set embed color based on rank
            embed.color = title_color
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating player stats embed: {e}")
            return discord.Embed(
                title=f"📊 {member.display_name}'s Stats",
                description="Error loading statistics",
                color=0xFF0000
            )
    
    @staticmethod
    def create_leaderboard_embed(guild: discord.Guild, top_players: List, stat_type: str = "wins") -> discord.Embed:
        """Create leaderboard embed with enhanced formatting"""
        try:
            stat_names = {
                "wins": "🏆 **Victory Leaderboard**",
                "kills": "⚔️ **Kill Leaderboard**", 
                "deaths": "💀 **Death Leaderboard**",
                "revives": "✨ **Revival Leaderboard**"
            }
            
            colors = {
                "wins": 0xFFD700,     # Gold
                "kills": 0xFF4500,    # Red
                "deaths": 0x696969,   # Gray
                "revives": 0x32CD32   # Green
            }
            
            embed = discord.Embed(
                title=stat_names.get(stat_type, "📊 **Leaderboard**"),
                color=colors.get(stat_type, 0xFFD700)
            )
            
            if not top_players:
                embed.description = "No statistics available yet!"
                return embed
            
            # Create leaderboard entries
            description_lines = []
            medals = ["🥇", "🥈", "🥉"]
            
            for i, (member_id, stats) in enumerate(top_players[:10]):
                member = guild.get_member(member_id)
                if not member:
                    continue
                
                # Medal or position number
                if i < 3:
                    position = medals[i]
                else:
                    position = f"**{i+1}.**"
                
                value = stats.get(stat_type, 0)
                
                # Add context for certain stats
                if stat_type == "wins" and stats.get("deaths", 0) > 0:
                    total_games = stats.get("wins", 0) + stats.get("deaths", 0)
                    win_rate = (stats.get("wins", 0) / total_games * 100) if total_games > 0 else 0
                    description_lines.append(f"{position} {member.display_name} - {value} wins ({win_rate:.1f}%)")
                elif stat_type == "kills" and stats.get("deaths", 0) > 0:
                    kd_ratio = value / stats.get("deaths", 1)
                    description_lines.append(f"{position} {member.display_name} - {value} kills (K/D: {kd_ratio:.2f})")
                else:
                    description_lines.append(f"{position} {member.display_name} - {value}")
            
            embed.description = "\n".join(description_lines) if description_lines else "No data available"
            
            # Add footer with additional info
            if top_players:
                total_tracked = len(top_players)
                embed.set_footer(text=f"Showing top 10 of {total_tracked} players")
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating leaderboard embed: {e}")
            return discord.Embed(
                title="📊 Leaderboard",
                description="Error loading leaderboard data",
                color=0xFF0000
            )
    
    @staticmethod
    def create_alive_players_embed(game: Dict, alive_players: List[str]) -> discord.Embed:
        """Create embed showing current alive players with enhanced info"""
        try:
            embed = discord.Embed(
                title="❤️ **ALIVE TRIBUTES** ❤️",
                color=0x00FF00
            )
            
            if not alive_players:
                embed.description = "💀 No survivors remain!"
                return embed
            
            # Sort players by kills (most dangerous first)
            sorted_players = sorted(
                [(pid, game["players"][pid]) for pid in alive_players],
                key=lambda x: (x[1].get("kills", 0), x[1].get("name", "")),
                reverse=True
            )
            
            # Create player list
            player_lines = []
            for i, (player_id, player_data) in enumerate(sorted_players):
                name = player_data.get("name", "Unknown")
                title = player_data.get("title", "the Nameless")
                kills = player_data.get("kills", 0)
                revives = player_data.get("revives", 0)
                
                line = f"**{name}** {title}"
                
                # Add district
                district_num = player_data.get("district", 1)
                district_name = DISTRICTS.get(district_num, f"District {district_num}")
                line += f" - {district_name}"
                
                # Add stats
                stats = []
                if kills > 0:
                    stats.append(f"⚔️ {kills} kills")
                if revives > 0:
                    stats.append(f"✨ {revives} revives")
                
                if stats:
                    line += f" ({', '.join(stats)})"
                
                player_lines.append(line)
            
            embed.description = "\n".join(player_lines)
            
            # Stats section
            total_players = len(game.get("players", {}))
            current_round = game.get("round", 0)
            
            embed.add_field(
                name="📊 **Game Stats**",
                value=f"**Round:** {current_round}\n**Survivors:** {len(alive_players)}/{total_players}",
                inline=True
            )
            
            # Most dangerous player
            if sorted_players and sorted_players[0][1].get("kills", 0) > 0:
                top_player = sorted_players[0][1]
                embed.add_field(
                    name="⚔️ **Most Dangerous**",
                    value=f"**{top_player['name']}** ({top_player['kills']} kills)",
                    inline=True
                )
            
            embed.set_footer(text="Use `.hungergames status` for more details")
            return embed
            
        except Exception as e:
            logger.error(f"Error creating alive players embed: {e}")
            return discord.Embed(
                title="❤️ Alive Players",
                description="Error loading player information",
                color=0xFF0000
            )


class StatsCalculator:
    """Handles statistical calculations and rankings"""
    
    @staticmethod
    def calculate_player_rank(wins: int, total_games: int, kills: int) -> Tuple[str, int]:
        """Calculate player rank title and color based on performance"""
        try:
            if wins >= 10:
                return "🌟 **Legendary Champion**", 0xFFD700  # Gold
            elif wins >= 5:
                return "👑 **Elite Victor**", 0xFF6B35      # Orange
            elif wins >= 3:
                return "🥇 **Veteran Survivor**", 0xC0C0C0  # Silver
            elif wins >= 1:
                return "🏹 **Arena Survivor**", 0xCD7F32    # Bronze
            elif total_games >= 5:
                return "💀 **Battle-Hardened**", 0x800080   # Purple
            else:
                return "🆕 **Fresh Tribute**", 0x008000     # Green
        except Exception as e:
            logger.error(f"Error calculating rank: {e}")
            return "🎮 **Player**", 0x808080


class ValidationUtils:
    """Enhanced validation utilities"""
    
    @staticmethod
    def validate_countdown(countdown: int) -> tuple[bool, str]:
        """Validate countdown with enhanced error messages"""
        return game_config_manager.validate_countdown(countdown)
    
    @staticmethod
    def validate_game_state(game: Dict) -> bool:
        """Validate game state integrity"""
        return game_config_manager.validate_game_state(game)
    
    @staticmethod
    def validate_player_exists(game: Dict, player_id: str) -> bool:
        """Check if player exists in game"""
        try:
            return player_id in game.get("players", {})
        except Exception:
            return False


class GameStateUtils:
    """Utilities for game state management"""
    
    @staticmethod
    def get_event_weights() -> Dict[str, int]:
        """Get default event weights"""
        return game_config_manager.game_config.DEFAULT_EVENT_WEIGHTS.copy()
    
    @staticmethod
    def should_execute_event(alive_count: int, round_num: int) -> bool:
        """Determine if an event should happen this round"""
        # With combined events system, we always want events
        return True
    
    @staticmethod
    def get_game_phase_description(round_num: int, alive_count: int) -> str:
        """Get description of current game phase"""
        try:
            config = game_config_manager.game_config
            
            if alive_count <= config.FINAL_DUEL_THRESHOLD:
                return "🔥 **FINAL DUEL** - Only two remain!"
            elif alive_count <= config.ENDGAME_THRESHOLD:
                return "⚔️ **FINAL FIVE** - The end is near..."
            elif alive_count <= 10:
                return "💀 **TOP TEN** - The arena grows smaller..."
            elif round_num < 5:
                return "🌅 **EARLY GAME** - The hunt begins..."
            elif round_num < 15:
                return "🌞 **MID GAME** - Alliances form and break..."
            else:
                return "🌙 **LATE GAME** - Desperation sets in..."
        except Exception as e:
            logger.error(f"Error getting game phase description: {e}")
            return f"Round {round_num} - {alive_count} players remaining"


# Convenience functions (backwards compatibility)
def format_player_list(players: Dict, show_districts: bool = True, show_status: bool = True) -> str:
    """Backwards compatible function"""
    return PlayerListFormatter.format_player_list(players, show_districts, show_status)

def get_random_district() -> int:
    """Backwards compatible function"""
    return RandomGenerators.get_random_district()

def get_random_player_title() -> str:
    """Backwards compatible function"""
    return RandomGenerators.get_random_player_title()

def format_time_remaining(seconds: int) -> str:
    """Backwards compatible function"""
    return TimeFormatter.format_time_remaining(seconds)

def create_recruitment_embed(countdown: int, current_players: int = 0) -> discord.Embed:
    """Backwards compatible function"""
    return EmbedBuilder.create_recruitment_embed(countdown, current_players)

def create_game_start_embed(total_players: int) -> discord.Embed:
    """Backwards compatible function"""
    return EmbedBuilder.create_game_start_embed(total_players)

def create_player_stats_embed(member_data: Dict, member: discord.Member) -> discord.Embed:
    """Backwards compatible function"""
    return EmbedBuilder.create_player_stats_embed(member_data, member)

def create_leaderboard_embed(guild: discord.Guild, top_players: List, stat_type: str = "wins") -> discord.Embed:
    """Backwards compatible function"""
    return EmbedBuilder.create_leaderboard_embed(guild, top_players, stat_type)

def validate_countdown(countdown: int) -> tuple[bool, str]:
    """Backwards compatible function"""
    return ValidationUtils.validate_countdown(countdown)

def get_event_weights() -> Dict[str, int]:
    """Backwards compatible function"""
    return GameStateUtils.get_event_weights()

def should_execute_event(alive_count: int, round_num: int) -> bool:
    """Backwards compatible function"""
    return GameStateUtils.should_execute_event(alive_count, round_num)

def get_game_phase_description(round_num: int, alive_count: int) -> str:
    """Backwards compatible function"""
    return GameStateUtils.get_game_phase_description(round_num, alive_count)
