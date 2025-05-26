"""
Enhanced Discord Embed Builder - Minimal Version

Simplified embed creation with basic styling and themes.
"""

import discord
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmbedTheme:
    """Theme configuration for embeds"""
    primary_color: int
    secondary_color: int
    success_color: int
    warning_color: int
    error_color: int
    accent_color: int


class EmbedStyles:
    """Predefined embed styles and themes"""
    
    # Color schemes
    THEMES = {
        "default": EmbedTheme(0x0596aa, 0x34495e, 0x2ecc71, 0xf39c12, 0xe74c3c, 0x9b59b6),
        "dark": EmbedTheme(0x2c3e50, 0x34495e, 0x27ae60, 0xe67e22, 0xc0392b, 0x8e44ad),
        "light": EmbedTheme(0x3498db, 0x95a5a6, 0x2ecc71, 0xf39c12, 0xe74c3c, 0x9b59b6),
        "gaming": EmbedTheme(0x00ff88, 0x1abc9c, 0x2ecc71, 0xf39c12, 0xff4757, 0xe056fd),
        "professional": EmbedTheme(0x2c3e50, 0x34495e, 0x27ae60, 0xe67e22, 0xc0392b, 0x8e44ad)
    }
    
    # Team colors for League
    TEAM_COLORS = {
        "100": 0x4ecdc4,  # Blue team
        "200": 0xff6b6b   # Red team
    }
    
    # Rank colors
    RANK_COLORS = {
        "IRON": 0x8d6e63,
        "BRONZE": 0xcd7f32,
        "SILVER": 0xc0c0c0,
        "GOLD": 0xffd700,
        "PLATINUM": 0x00e676,
        "EMERALD": 0x50c878,
        "DIAMOND": 0x40e0d0,
        "MASTER": 0x9c27b0,
        "GRANDMASTER": 0xff5722,
        "CHALLENGER": 0xf44336
    }
    
    # Achievement rarity colors
    RARITY_COLORS = {
        "common": 0x95a5a6,
        "uncommon": 0x2ecc71,
        "rare": 0x3498db,
        "epic": 0x9b59b6,
        "legendary": 0xf39c12,
        "mythic": 0xe74c3c
    }


class EnhancedEmbedBuilder:
    """Simplified embed builder with basic advanced features"""
    
    def __init__(self, champion_data: Dict, theme: str = "gaming"):
        self.champion_data = champion_data
        self.theme = EmbedStyles.THEMES.get(theme, EmbedStyles.THEMES["gaming"])
        self.champion_icon_base = "https://raw.githubusercontent.com/AfterWorld/ultcogs/main/lol/championicons"
        
        # Role emojis for visual appeal
        self.role_emojis = {
            "ADC": "⚔️",
            "Support": "🛡️", 
            "Mid": "🔥",
            "Jungle": "🌲",
            "Top": "🗡️",
            "UTILITY": "🛡️",
            "MARKSMAN": "⚔️",
            "MAGE": "🔥",
            "ASSASSIN": "🗡️",
            "FIGHTER": "⚔️",
            "TANK": "🛡️"
        }
        
        # Performance indicators
        self.performance_emojis = {
            "excellent": "🔥",
            "good": "⚡",
            "average": "⚔️",
            "poor": "😐",
            "unknown": "❓"
        }
        
        # Game phase emojis
        self.phase_emojis = {
            "Early Game": "🌅",
            "Mid Game": "☀️", 
            "Late Game": "🌙"
        }
    
    async def create_live_game_embed_v2(self, game_data: Dict, analytics, win_prob: Dict = None) -> List[discord.Embed]:
        """Create enhanced live game embeds with basic analytics"""
        try:
            embeds = []
            
            # Calculate win probability if not provided
            if not win_prob and analytics:
                try:
                    win_prob_obj = await analytics.calculate_win_probability(game_data)
                    win_prob = {
                        "100": win_prob_obj.blue_team_prob,
                        "200": win_prob_obj.red_team_prob
                    }
                except Exception as e:
                    logger.error(f"Error calculating win probability: {e}")
                    win_prob = {"100": 50.0, "200": 50.0}
            
            if not win_prob:
                win_prob = {"100": 50.0, "200": 50.0}
            
            # Main game overview embed
            main_embed = await self._create_main_game_embed(game_data, win_prob, analytics)
            embeds.append(main_embed)
            
            # Team analysis embeds
            team_embeds = await self._create_team_embeds(game_data, win_prob, analytics)
            embeds.extend(team_embeds)
            
            return embeds
            
        except Exception as e:
            logger.error(f"Error creating live game embeds: {e}")
            # Return basic embed on error
            return [await self._create_basic_live_embed(game_data)]
    
    async def _create_main_game_embed(self, game_data: Dict, win_prob: Dict, analytics) -> discord.Embed:
        """Create main game overview embed"""
        try:
            game_mode = game_data.get('gameMode', 'Unknown')
            game_length = game_data.get('gameLength', 0)
            game_type = game_data.get('gameType', 'Unknown')
            
            # Determine embed color based on game mode
            if 'ARAM' in game_mode:
                color = 0xffd700  # Gold for ARAM
            elif 'RANKED' in game_type:
                color = 0x00ff88  # Green for ranked
            else:
                color = self.theme.primary_color
            
            embed = discord.Embed(
                title=f"🔴 Live Game Analysis - {game_mode}",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            # Game duration and phase
            if analytics:
                try:
                    phase = analytics.get_game_phase(game_length)
                    phase_emoji = self.phase_emojis.get(phase, "⏱️")
                    phase_desc = analytics.get_phase_description(phase)
                except:
                    phase = "Unknown"
                    phase_emoji = "⏱️"
                    phase_desc = ""
            else:
                phase = "Unknown"
                phase_emoji = "⏱️"
                phase_desc = ""
            
            embed.description = (
                f"**{phase_emoji} Duration:** {game_length // 60}m {game_length % 60}s\n"
                f"**🎮 Game Phase:** {phase}\n"
                f"**🎯 Game Type:** {game_type}"
            )
            
            if phase_desc:
                embed.description += f"\n*{phase_desc}*"
            
            # Win probability with basic bars
            blue_prob = win_prob.get("100", 50.0)
            red_prob = win_prob.get("200", 50.0)
            
            # Create simple probability bars
            blue_bar = self._create_progress_bar(blue_prob, 15)
            red_bar = self._create_progress_bar(red_prob, 15)
            
            embed.add_field(
                name="📊 Win Probability",
                value=f"🔵 **Blue Team: {blue_prob:.1f}%**\n{blue_bar}\n\n"
                      f"🔴 **Red Team: {red_prob:.1f}%**\n{red_bar}",
                inline=False
            )
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating main game embed: {e}")
            return await self._create_basic_live_embed(game_data)
    
    async def _create_team_embeds(self, game_data: Dict, win_prob: Dict, analytics) -> List[discord.Embed]:
        """Create team analysis embeds"""
        try:
            embeds = []
            
            # Organize teams
            teams = {"100": [], "200": []}
            for participant in game_data.get('participants', []):
                team_id = str(participant.get('teamId', 100))
                teams[team_id].append(participant)
            
            team_names = {"100": "🔵 Blue Team", "200": "🔴 Red Team"}
            
            for team_id, players in teams.items():
                if not players:
                    continue
                
                embed = await self._create_single_team_embed(
                    team_id, players, win_prob.get(team_id, 50.0), analytics, team_names[team_id]
                )
                embeds.append(embed)
            
            return embeds
            
        except Exception as e:
            logger.error(f"Error creating team embeds: {e}")
            return []
    
    async def _create_single_team_embed(self, team_id: str, players: List[Dict], 
                                       win_prob: float, analytics, team_name: str) -> discord.Embed:
        """Create embed for a single team"""
        try:
            color = EmbedStyles.TEAM_COLORS.get(team_id, self.theme.primary_color)
            
            embed = discord.Embed(
                title=f"{team_name} - {win_prob:.1f}% Win Rate",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            # Team composition analysis if analytics available
            if analytics:
                try:
                    team_analysis = await analytics.analyze_team_composition(players)
                    
                    # Team stats summary
                    scaling_emoji = "🌱" if team_analysis.scaling_phase == "Early" else "🌿" if team_analysis.scaling_phase == "Mid" else "🌳"
                    engage_stars = "⭐" * min(5, max(1, team_analysis.engage_score // 2))
                    peel_shields = "🛡️" * min(3, max(1, team_analysis.peel_score // 3))
                    
                    embed.description = (
                        f"**{scaling_emoji} Scaling:** {team_analysis.scaling_phase} Game\n"
                        f"**⚔️ Engage:** {engage_stars}\n"
                        f"**🛡️ Peel:** {peel_shields}\n"
                        f"**🎯 Objective Control:** {team_analysis.objective_control}/10"
                    )
                    
                    # Damage distribution
                    if team_analysis.damage_distribution:
                        damage_text = self._create_damage_distribution_text(team_analysis.damage_distribution)
                        embed.add_field(
                            name="⚔️ Damage Types",
                            value=damage_text,
                            inline=True
                        )
                    
                    # Weaknesses
                    if team_analysis.weaknesses:
                        weakness_text = "\n".join([f"⚠️ {w}" for w in team_analysis.weaknesses[:2]])
                        embed.add_field(
                            name="🎯 Weaknesses",
                            value=weakness_text,
                            inline=True
                        )
                        
                except Exception as e:
                    logger.error(f"Error analyzing team composition: {e}")
            
            # Player details
            player_text = ""
            for i, player in enumerate(players, 1):
                player_info = await self._format_player_info(player, i)
                player_text += player_info + "\n"
            
            embed.add_field(
                name="👥 Players",
                value=player_text.strip(),
                inline=False
            )
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating team embed: {e}")
            # Return basic team embed
            return await self._create_basic_team_embed(team_id, players, team_name)
    
    async def _format_player_info(self, player: Dict, position: int) -> str:
        """Format individual player information"""
        try:
            champion_id = player.get('championId', 0)
            champion_data = self.champion_data.get(champion_id, {})
            champion_name = champion_data.get('name', f'Champion {champion_id}')
            summoner_name = player.get('summonerName', 'Unknown')
            
            # Get role emoji
            role = champion_data.get('role', 'Unknown')
            role_emoji = self.role_emojis.get(role, "❓")
            
            # Simple format
            return f"⚔️ **{champion_name}** {role_emoji} - {summoner_name}"
            
        except Exception as e:
            logger.error(f"Error formatting player info: {e}")
            return f"❓ Unknown Player"
    
    def _create_progress_bar(self, percentage: float, length: int = 15) -> str:
        """Create a simple progress bar"""
        try:
            filled_length = int(length * percentage / 100)
            filled_char = "█"
            empty_char = "░"
            bar = filled_char * filled_length + empty_char * (length - filled_length)
            return f"`{bar}` {percentage:.1f}%"
        except:
            return f"`{'█' * (length // 2)}{'░' * (length // 2)}` {percentage:.1f}%"
    
    def _create_damage_distribution_text(self, damage_dist: Dict[str, float]) -> str:
        """Create text representation of damage distribution"""
        try:
            text = ""
            for damage_type, percentage in damage_dist.items():
                if percentage > 5:  # Only show significant percentages
                    emoji = "⚔️" if damage_type == "AD" else "🔮" if damage_type == "AP" else "🛡️"
                    text += f"{emoji} {damage_type}: {percentage:.0f}%\n"
            return text.strip() or "Mixed damage"
        except:
            return "Mixed damage"
    
    async def _create_basic_live_embed(self, game_data: Dict) -> discord.Embed:
        """Create basic live game embed as fallback"""
        try:
            game_mode = game_data.get('gameMode', 'Unknown')
            game_length = game_data.get('gameLength', 0)
            
            embed = discord.Embed(
                title=f"🔴 Live Game - {game_mode}",
                description=f"**Duration:** {game_length // 60}m {game_length % 60}s",
                color=0xff6b6b,
                timestamp=datetime.utcnow()
            )
            
            # Basic team info
            blue_team = []
            red_team = []
            
            for participant in game_data.get('participants', []):
                if participant.get('teamId') == 100:
                    blue_team.append(participant)
                else:
                    red_team.append(participant)
            
            if blue_team:
                blue_text = ""
                for player in blue_team:
                    champion_id = player.get('championId', 0)
                    champion_name = self.champion_data.get(champion_id, {}).get('name', f'Champion {champion_id}')
                    summoner_name = player.get('summonerName', 'Unknown')
                    blue_text += f"**{champion_name}** - {summoner_name}\n"
                
                embed.add_field(
                    name="🔵 Blue Team",
                    value=blue_text.strip(),
                    inline=True
                )
            
            if red_team:
                red_text = ""
                for player in red_team:
                    champion_id = player.get('championId', 0)
                    champion_name = self.champion_data.get(champion_id, {}).get('name', f'Champion {champion_id}')
                    summoner_name = player.get('summonerName', 'Unknown')
                    red_text += f"**{champion_name}** - {summoner_name}\n"
                
                embed.add_field(
                    name="🔴 Red Team",
                    value=red_text.strip(),
                    inline=True
                )
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating basic live embed: {e}")
            return discord.Embed(
                title="🔴 Live Game",
                description="Error loading game data",
                color=0xff6b6b
            )
    
    async def _create_basic_team_embed(self, team_id: str, players: List[Dict], team_name: str) -> discord.Embed:
        """Create basic team embed as fallback"""
        try:
            color = EmbedStyles.TEAM_COLORS.get(team_id, 0x95a5a6)
            
            embed = discord.Embed(
                title=team_name,
                color=color
            )
            
            player_text = ""
            for player in players:
                champion_id = player.get('championId', 0)
                champion_name = self.champion_data.get(champion_id, {}).get('name', f'Champion {champion_id}')
                summoner_name = player.get('summonerName', 'Unknown')
                player_text += f"**{champion_name}** - {summoner_name}\n"
            
            embed.add_field(
                name="Players",
                value=player_text.strip() or "No players found",
                inline=False
            )
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating basic team embed: {e}")
            return discord.Embed(title=team_name, color=0x95a5a6)
    
    async def create_profile_embed_v2(self, summoner_data: Dict, ranked_data: List[Dict], 
                                     mastery_data: List[Dict], achievements: List = None) -> discord.Embed:
        """Create enhanced summoner profile embed"""
        try:
            summoner_name = summoner_data.get('name', 'Unknown')
            summoner_level = summoner_data.get('summonerLevel', 0)
            
            # Determine embed color based on highest rank
            color = self._get_profile_color(ranked_data)
            
            embed = discord.Embed(
                title=f"🎮 {summoner_name}",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            # Basic info
            embed.add_field(
                name="📊 Profile Info",
                value=f"**Level:** {summoner_level}\n"
                      f"**Account:** {summoner_data.get('accountId', 'Unknown')[:8]}...",
                inline=True
            )
            
            # Enhanced ranked information
            if ranked_data:
                ranked_text = await self._format_ranked_info(ranked_data)
                embed.add_field(
                    name="🏆 Ranked Status",
                    value=ranked_text,
                    inline=True
                )
            
            # Champion mastery
            if mastery_data:
                mastery_text = await self._format_mastery_info(mastery_data)
                embed.add_field(
                    name="⭐ Champion Mastery",
                    value=mastery_text,
                    inline=False
                )
            
            # Add achievements if available
            if achievements:
                achievement_text = await self._format_achievements_summary(achievements)
                embed.add_field(
                    name="🏅 Recent Achievements",
                    value=achievement_text,
                    inline=False
                )
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating profile embed: {e}")
            return discord.Embed(
                title=f"🎮 {summoner_data.get('name', 'Unknown')}",
                description="Error loading profile data",
                color=0xff6b6b
            )
    
    def _get_profile_color(self, ranked_data: List[Dict]) -> int:
        """Get embed color based on highest rank"""
        if not ranked_data:
            return self.theme.primary_color
        
        highest_tier = "IRON"
        for queue in ranked_data:
            tier = queue.get('tier', 'IRON')
            if tier in EmbedStyles.RANK_COLORS:
                tier_order = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", 
                             "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
                try:
                    if tier_order.index(tier) > tier_order.index(highest_tier):
                        highest_tier = tier
                except ValueError:
                    pass
        
        return EmbedStyles.RANK_COLORS.get(highest_tier, self.theme.primary_color)
    
    async def _format_ranked_info(self, ranked_data: List[Dict]) -> str:
        """Format ranked information"""
        try:
            ranked_text = ""
            
            for queue in ranked_data:
                queue_type = queue.get('queueType', 'RANKED_SOLO_5x5').replace('_', ' ')
                tier = queue.get('tier', 'Unranked')
                rank = queue.get('rank', '')
                lp = queue.get('leaguePoints', 0)
                wins = queue.get('wins', 0)
                losses = queue.get('losses', 0)
                
                # Calculate win rate
                total_games = wins + losses
                win_rate = (wins / total_games * 100) if total_games > 0 else 0
                
                # Get rank emoji
                rank_emoji = self._get_rank_emoji(tier)
                
                # Format queue name
                queue_display = queue_type.replace('RANKED', '').replace('SOLO', 'Solo/Duo').strip()
                
                ranked_text += f"{rank_emoji} **{queue_display}**\n"
                if tier != "Unranked":
                    ranked_text += f"{tier.title()} {rank} ({lp} LP)\n"
                    ranked_text += f"{wins}W / {losses}L ({win_rate:.1f}%)\n\n"
                else:
                    ranked_text += "Unranked\n\n"
            
            return ranked_text.strip()
            
        except Exception as e:
            logger.error(f"Error formatting ranked info: {e}")
            return "Error loading ranked data"
    
    def _get_rank_emoji(self, tier: str) -> str:
        """Get emoji for rank tier"""
        rank_emojis = {
            "IRON": "🤎",
            "BRONZE": "🥉",
            "SILVER": "🥈", 
            "GOLD": "🥇",
            "PLATINUM": "💠",
            "EMERALD": "💚",
            "DIAMOND": "💎",
            "MASTER": "🎖️",
            "GRANDMASTER": "🏆",
            "CHALLENGER": "👑"
        }
        return rank_emojis.get(tier, "❓")
    
    async def _format_mastery_info(self, mastery_data: List[Dict]) -> str:
        """Format champion mastery"""
        try:
            mastery_text = ""
            
            for i, mastery in enumerate(mastery_data[:3], 1):
                champion_id = mastery.get('championId', 0)
                champion_data = self.champion_data.get(champion_id, {})
                champion_name = champion_data.get('name', f'Champion {champion_id}')
                
                level = mastery.get('championLevel', 0)
                points = mastery.get('championPoints', 0)
                
                # Mastery level emoji
                mastery_emoji = self._get_mastery_emoji(level)
                
                mastery_text += f"{mastery_emoji} **{i}. {champion_name}**\n"
                mastery_text += f"Level {level} ({points:,} pts)\n\n"
            
            return mastery_text.strip()
            
        except Exception as e:
            logger.error(f"Error formatting mastery info: {e}")
            return "Error loading mastery data"
    
    def _get_mastery_emoji(self, level: int) -> str:
        """Get emoji for mastery level"""
        if level >= 7:
            return "💜"  # Mastery 7
        elif level >= 6:
            return "💙"  # Mastery 6
        elif level >= 5:
            return "💚"  # Mastery 5
        elif level >= 4:
            return "💛"  # Mastery 4
        else:
            return "🤍"  # Lower mastery
    
    async def _format_achievements_summary(self, achievements: List) -> str:
        """Format achievements summary"""
        try:
            if not achievements:
                return "No recent achievements"
            
            achievement_text = ""
            for achievement in achievements[:3]:  # Show latest 3
                achievement_text += f"{achievement.emoji} {achievement.name}\n"
            
            if len(achievements) > 3:
                achievement_text += f"\n*... and {len(achievements) - 3} more*"
            
            return achievement_text
            
        except Exception as e:
            logger.error(f"Error formatting achievements: {e}")
            return "Error loading achievements"
    
    async def create_achievement_embed(self, achievement, user_mention: str) -> discord.Embed:
        """Create achievement unlock embed"""
        try:
            color = EmbedStyles.RARITY_COLORS.get(achievement.rarity, 0x95a5a6)
            
            embed = discord.Embed(
                title="🎉 Achievement Unlocked!",
                description=f"{user_mention} earned **{achievement.name}**!\n\n"
                           f"{achievement.emoji} *{achievement.description}*\n\n"
                           f"**+{achievement.points} points**",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="📊 Details",
                value=f"**Category:** {achievement.category.title()}\n"
                      f"**Rarity:** {achievement.rarity.title()}",
                inline=True
            )
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating achievement embed: {e}")
            return discord.Embed(
                title="🎉 Achievement Unlocked!",
                description="Achievement details unavailable",
                color=0x95a5a6
            )
    
    async def create_leaderboard_embed(self, guild: discord.Guild, leaderboard_data: List[Tuple], 
                                     stat_type: str) -> discord.Embed:
        """Create server leaderboard embed"""
        try:
            embed = discord.Embed(
                title=f"🏆 {guild.name} Leaderboard",
                description=f"**{stat_type.replace('_', ' ').title()}**",
                color=0xffd700,
                timestamp=datetime.utcnow()
            )
            
            if not leaderboard_data:
                embed.description += "\n\nNo data available yet. Start using the bot to appear on the leaderboard!"
                embed.color = self.theme.secondary_color
                return embed
            
            # Create leaderboard entries
            leaderboard_text = ""
            medal_emojis = ["🥇", "🥈", "🥉"]
            
            for i, entry in enumerate(leaderboard_data, 1):
                discord_id, summoner_name, stat_value = entry[:3]
                
                # Get user from guild
                user = guild.get_member(int(discord_id))
                display_name = user.display_name if user else (summoner_name or "Unknown User")
                
                # Medal or position
                position_indicator = medal_emojis[i-1] if i <= 3 else f"**{i}.**"
                
                # Format stat value
                if isinstance(stat_value, float):
                    if stat_value.is_integer():
                        stat_display = f"{int(stat_value):,}"
                    else:
                        stat_display = f"{stat_value:,.1f}"
                else:
                    stat_display = f"{stat_value:,}"
                
                leaderboard_text += f"{position_indicator} **{display_name}** - {stat_display}\n"
            
            embed.description += f"\n\n{leaderboard_text.strip()}"
            
            # Add footer
            embed.set_footer(
                text="Use the bot more to climb the leaderboard!",
                icon_url=guild.icon.url if guild.icon else None
            )
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating leaderboard embed: {e}")
            return discord.Embed(
                title=f"🏆 {guild.name} Leaderboard",
                description="Error loading leaderboard data",
                color=0xff6b6b
            )
