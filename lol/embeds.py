"""
Enhanced Discord Embed Builder for Advanced LoL Cog

Creates sophisticated, visually appealing Discord embeds with 
interactive elements, rich formatting, and professional styling.
"""

import discord
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
import math
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


@dataclass
class InteractiveElement:
    """Interactive embed element configuration"""
    emoji: str
    action: str
    description: str
    enabled: bool = True


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
    """Main embed builder with advanced features"""
    
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
        """Create enhanced live game embeds with advanced analytics"""
        embeds = []
        
        # Calculate win probability if not provided
        if not win_prob:
            win_prob_obj = await analytics.calculate_win_probability(game_data)
            win_prob = {
                "100": win_prob_obj.blue_team_prob,
                "200": win_prob_obj.red_team_prob
            }
        
        # Main game overview embed
        main_embed = await self._create_main_game_embed(game_data, win_prob, analytics)
        embeds.append(main_embed)
        
        # Team analysis embeds
        team_embeds = await self._create_team_embeds(game_data, win_prob, analytics)
        embeds.extend(team_embeds)
        
        # Add interactive footer to main embed
        main_embed.set_footer(
            text="📊 Detailed Stats • 🔄 Refresh • 📈 Win Probability • ⏱️ Match History",
            icon_url="https://cdn.discordapp.com/emojis/123456789012345678.png"
        )
        
        return embeds
    
    async def _create_main_game_embed(self, game_data: Dict, win_prob: Dict, analytics) -> discord.Embed:
        """Create main game overview embed"""
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
        phase = analytics.get_game_phase(game_length)
        phase_emoji = self.phase_emojis.get(phase, "⏱️")
        
        embed.description = (
            f"**{phase_emoji} Duration:** {game_length // 60}m {game_length % 60}s\n"
            f"**🎮 Game Phase:** {phase}\n"
            f"**🎯 Game Type:** {game_type}"
        )
        
        # Win probability with visual bars
        blue_prob = win_prob.get("100", 50.0)
        red_prob = win_prob.get("200", 50.0)
        
        # Create probability bars
        blue_bar = self._create_progress_bar(blue_prob, 20, "🔵", "⬜")
        red_bar = self._create_progress_bar(red_prob, 20, "🔴", "⬜")
        
        embed.add_field(
            name="📊 Win Probability",
            value=f"🔵 **Blue Team: {blue_prob:.1f}%**\n{blue_bar}\n\n"
                  f"🔴 **Red Team: {red_prob:.1f}%**\n{red_bar}",
            inline=False
        )
        
        # Game insights
        insights = await self._generate_game_insights(game_data, analytics, phase)
        if insights:
            embed.add_field(
                name="💡 Game Insights",
                value=insights,
                inline=False
            )
        
        # Add thumbnail based on game mode
        if 'ARAM' in game_mode:
            embed.set_thumbnail(url="https://cdn.communitydragon.org/latest/game/assets/ux/summonerrift/img/map-bg.jpg")
        
        return embed
    
    async def _create_team_embeds(self, game_data: Dict, win_prob: Dict, analytics) -> List[discord.Embed]:
        """Create detailed team analysis embeds"""
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
    
    async def _create_single_team_embed(self, team_id: str, players: List[Dict], 
                                       win_prob: float, analytics, team_name: str) -> discord.Embed:
        """Create embed for a single team"""
        color = EmbedStyles.TEAM_COLORS.get(team_id, self.theme.primary_color)
        
        embed = discord.Embed(
            title=f"{team_name} - {win_prob:.1f}% Win Rate",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        # Team composition analysis
        team_analysis = await analytics.analyze_team_composition(players)
        
        # Team stats summary
        scaling_emoji = "🌱" if team_analysis.scaling_phase == "Early" else "🌿" if team_analysis.scaling_phase == "Mid" else "🌳"
        engage_stars = "⭐" * min(5, team_analysis.engage_score)
        peel_shields = "🛡️" * min(5, team_analysis.peel_score)
        
        embed.description = (
            f"**{scaling_emoji} Scaling:** {team_analysis.scaling_phase} Game\n"
            f"**⚔️ Engage:** {engage_stars} ({team_analysis.engage_score}/10)\n"
            f"**🛡️ Peel:** {peel_shields} ({team_analysis.peel_score}/10)\n"
            f"**🎯 Objective Control:** {team_analysis.objective_control}/10"
        )
        
        # Damage distribution pie chart (text representation)
        if team_analysis.damage_distribution:
            damage_text = self._create_damage_distribution_text(team_analysis.damage_distribution)
            embed.add_field(
                name="⚔️ Damage Distribution",
                value=damage_text,
                inline=True
            )
        
        # Team synergies and weaknesses
        if team_analysis.synergies:
            synergy_text = "\n".join([f"✨ {synergy}" for synergy in team_analysis.synergies[:3]])
            embed.add_field(
                name="🤝 Synergies",
                value=synergy_text,
                inline=True
            )
        
        if team_analysis.weaknesses:
            weakness_text = "\n".join([f"⚠️ {weakness}" for weakness in team_analysis.weaknesses[:3]])
            embed.add_field(
                name="🎯 Weaknesses",
                value=weakness_text,
                inline=True
            )
        
        # Player details
        player_text = ""
        for i, player in enumerate(players, 1):
            player_info = await self._format_player_info(player, i)
            player_text += player_info + "\n"
        
        embed.add_field(
            name="👥 Players",
            value=player_text,
            inline=False
        )
        
        return embed
    
    async def _format_player_info(self, player: Dict, position: int) -> str:
        """Format individual player information"""
        champion_id = player.get('championId', 0)
        champion_data = self.champion_data.get(champion_id, {})
        champion_name = champion_data.get('name', f'Champion {champion_id}')
        summoner_name = player.get('summonerName', 'Unknown')
        
        # Get role emoji
        role = champion_data.get('role', 'Unknown')
        role_emoji = self.role_emojis.get(role, "❓")
        
        # Performance indicator (would be based on analysis)
        performance = self._get_performance_indicator(player, champion_id)
        perf_emoji = self.performance_emojis.get(performance, "❓")
        
        # Rank display (if available)
        rank_display = await self._format_rank_display(player)
        
        return f"{perf_emoji} **{champion_name}** {role_emoji}\n├ {summoner_name}\n└ {rank_display}"
    
    def _get_performance_indicator(self, player: Dict, champion_id: int) -> str:
        """Analyze player performance indicator"""
        # This would integrate with historical data analysis
        # For now, return a placeholder
        return "average"
    
    async def _format_rank_display(self, player: Dict) -> str:
        """Format player rank display"""
        # This would integrate with cached rank data
        # For now, return placeholder
        return "Rank: Unknown"
    
    def _create_progress_bar(self, percentage: float, length: int = 20, 
                           filled_char: str = "█", empty_char: str = "░") -> str:
        """Create a visual progress bar"""
        filled_length = int(length * percentage / 100)
        bar = filled_char * filled_length + empty_char * (length - filled_length)
        return f"`{bar}` {percentage:.1f}%"
    
    def _create_damage_distribution_text(self, damage_dist: Dict[str, float]) -> str:
        """Create text representation of damage distribution"""
        text = ""
        for damage_type, percentage in damage_dist.items():
            if percentage > 0:
                emoji = "⚔️" if damage_type == "AD" else "🔮" if damage_type == "AP" else "🛡️"
                text += f"{emoji} {damage_type}: {percentage:.0f}%\n"
        return text.strip()
    
    async def _generate_game_insights(self, game_data: Dict, analytics, phase: str) -> str:
        """Generate intelligent game insights"""
        insights = []
        
        game_length = game_data.get('gameLength', 0)
        
        # Phase-specific insights
        if phase == "Early Game":
            insights.append("🌱 Focus on CS and early objectives")
        elif phase == "Mid Game":
            insights.append("⚔️ Team fights around objectives are crucial")
        elif phase == "Late Game":
            insights.append("🎯 One team fight can decide the game")
        
        # Game length insights
        if game_length > 2100:  # 35+ minutes
            insights.append("⏰ Extended game - scaling champions have advantage")
        elif game_length < 900:  # Less than 15 minutes
            insights.append("⚡ Fast-paced early game")
        
        return " • ".join(insights) if insights else ""
    
    async def create_profile_embed_v2(self, summoner_data: Dict, ranked_data: List[Dict], 
                                     mastery_data: List[Dict], achievements: List = None) -> discord.Embed:
        """Create enhanced summoner profile embed"""
        summoner_name = summoner_data.get('name', 'Unknown')
        summoner_level = summoner_data.get('summonerLevel', 0)
        
        # Determine embed color based on highest rank
        color = self._get_profile_color(ranked_data)
        
        embed = discord.Embed(
            title=f"🎮 {summoner_name}",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        # Basic info with enhanced formatting
        embed.add_field(
            name="📊 Profile Info",
            value=f"**Level:** {summoner_level}\n"
                  f"**Region:** {summoner_data.get('region', 'Unknown').upper()}\n"
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
        
        # Champion mastery with visual enhancements
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
        
        # Set profile icon as thumbnail if available
        profile_icon_id = summoner_data.get('profileIconId', 0)
        if profile_icon_id:
            icon_url = f"https://ddragon.leagueoflegends.com/cdn/14.1.1/img/profileicon/{profile_icon_id}.png"
            embed.set_thumbnail(url=icon_url)
        
        return embed
    
    def _get_profile_color(self, ranked_data: List[Dict]) -> int:
        """Get embed color based on highest rank"""
        if not ranked_data:
            return self.theme.primary_color
        
        highest_tier = "IRON"
        for queue in ranked_data:
            tier = queue.get('tier', 'IRON')
            if tier in EmbedStyles.RANK_COLORS:
                # Simple tier comparison (could be more sophisticated)
                tier_order = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", 
                             "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
                if tier_order.index(tier) > tier_order.index(highest_tier):
                    highest_tier = tier
        
        return EmbedStyles.RANK_COLORS.get(highest_tier, self.theme.primary_color)
    
    async def _format_ranked_info(self, ranked_data: List[Dict]) -> str:
        """Format ranked information with visual enhancements"""
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
                ranked_text += f"├ {tier.title()} {rank} ({lp} LP)\n"
                ranked_text += f"└ {wins}W / {losses}L ({win_rate:.1f}%)\n\n"
            else:
                ranked_text += "└ Unranked\n\n"
        
        return ranked_text.strip()
    
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
        """Format champion mastery with visual enhancements"""
        mastery_text = ""
        
        for i, mastery in enumerate(mastery_data[:3], 1):
            champion_id = mastery.get('championId', 0)
            champion_data = self.champion_data.get(champion_id, {})
            champion_name = champion_data.get('name', f'Champion {champion_id}')
            
            level = mastery.get('championLevel', 0)
            points = mastery.get('championPoints', 0)
            
            # Mastery level emoji
            mastery_emoji = self._get_mastery_emoji(level)
            
            # Role emoji if available
            role = champion_data.get('role', '')
            role_emoji = self.role_emojis.get(role, '')
            
            mastery_text += f"{mastery_emoji} **{i}. {champion_name}** {role_emoji}\n"
            mastery_text += f"├ Level {level}\n"
            mastery_text += f"└ {points:,} mastery points\n\n"
        
        return mastery_text.strip()
    
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
        if not achievements:
            return "No recent achievements"
        
        achievement_text = ""
        for achievement in achievements[:3]:  # Show latest 3
            rarity_emoji = self._get_rarity_emoji(achievement.rarity)
            achievement_text += f"{rarity_emoji} {achievement.emoji} {achievement.name}\n"
        
        if len(achievements) > 3:
            achievement_text += f"\n*... and {len(achievements) - 3} more*"
        
        return achievement_text
    
    def _get_rarity_emoji(self, rarity: str) -> str:
        """Get emoji for achievement rarity"""
        rarity_emojis = {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵", 
            "epic": "🟣",
            "legendary": "🟠",
            "mythic": "🔴"
        }
        return rarity_emojis.get(rarity, "⚪")
    
    async def create_achievement_embed(self, achievement, user_mention: str) -> discord.Embed:
        """Create achievement unlock embed with enhanced styling"""
        color = EmbedStyles.RARITY_COLORS.get(achievement.rarity, 0x95a5a6)
        
        embed = discord.Embed(
            title="🎉 Achievement Unlocked!",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        # Achievement info with enhanced formatting
        rarity_emoji = self._get_rarity_emoji(achievement.rarity)
        
        embed.description = (
            f"{user_mention} earned **{achievement.name}**!\n\n"
            f"{achievement.emoji} *{achievement.description}*\n\n"
            f"{rarity_emoji} **{achievement.rarity.title()} Achievement**\n"
            f"**+{achievement.points} points**"
        )
        
        embed.add_field(
            name="📊 Details",
            value=f"**Category:** {achievement.category.title()}\n"
                  f"**Points:** {achievement.points}\n"
                  f"**Rarity:** {achievement.rarity.title()}",
            inline=True
        )
        
        # Add achievement icon or thumbnail if available
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/achievement_icon.png")
        
        embed.set_footer(
            text=f"Achievement unlocked • {achievement.rarity.title()} rarity",
            icon_url="https://cdn.discordapp.com/emojis/star.png"
        )
        
        return embed
    
    async def create_leaderboard_embed(self, guild: discord.Guild, leaderboard_data: List[Tuple], 
                                     stat_type: str) -> discord.Embed:
        """Create enhanced server leaderboard embed"""
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
        
        # Create leaderboard entries with enhanced formatting
        leaderboard_text = ""
        medal_emojis = ["🥇", "🥈", "🥉"]
        
        for i, entry in enumerate(leaderboard_data, 1):
            discord_id, summoner_name, stat_value, *extra = entry
            
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
            
            # Add level/points info if available
            extra_info = ""
            if len(extra) >= 2:  # total_points, level
                total_points, level = extra[0], extra[1]
                if stat_type != "total_points":
                    extra_info = f" • Level {level}"
            
            leaderboard_text += f"{position_indicator} **{display_name}**\n"
            leaderboard_text += f"├ {stat_display} {stat_type.replace('_', ' ')}{extra_info}\n"
            
            # Add progress bar for top 3
            if i <= 3 and leaderboard_data:
                max_value = leaderboard_data[0][2]  # First place value
                if max_value > 0:
                    percentage = (stat_value / max_value) * 100
                    progress_bar = self._create_progress_bar(percentage, 10, "█", "░")
                    leaderboard_text += f"└ {progress_bar}\n\n"
                else:
                    leaderboard_text += "└ ─────────────\n\n"
            else:
                leaderboard_text += "└ ─────────────\n\n"
        
        embed.description += f"\n\n{leaderboard_text.strip()}"
        
        # Add footer with update info
        embed.set_footer(
            text="Leaderboard updates every 5 minutes • Use the bot more to climb!",
            icon_url=guild.icon.url if guild.icon else None
        )
        
        return embed
    
    async def create_match_embed_v2(self, match_data: Dict, puuid: str) -> discord.Embed:
        """Create enhanced match history embed"""
        info = match_data.get('info', {})
        
        # Find player's data
        player_data = None
        for participant in info.get('participants', []):
            if participant.get('puuid') == puuid:
                player_data = participant
                break
        
        if not player_data:
            return None
        
        # Basic match information
        game_mode = info.get('gameMode', 'Unknown')
        game_duration = info.get('gameDuration', 0)
        game_creation = datetime.fromtimestamp(info.get('gameCreation', 0) / 1000)
        
        # Player performance
        champion_name = player_data.get('championName', 'Unknown')
        kills = player_data.get('kills', 0)
        deaths = player_data.get('deaths', 0)
        assists = player_data.get('assists', 0)
        cs = player_data.get('totalMinionsKilled', 0) + player_data.get('neutralMinionsKilled', 0)
        vision_score = player_data.get('visionScore', 0)
        damage_dealt = player_data.get('totalDamageDealtToChampions', 0)
        gold_earned = player_data.get('goldEarned', 0)
        
        # Win/Loss styling
        win = player_data.get('win', False)
        color = 0x4ecdc4 if win else 0xff6b6b
        result_emoji = "🏆" if win else "💀"
        result_text = "Victory" if win else "Defeat"
        
        embed = discord.Embed(
            title=f"{result_emoji} {champion_name} - {game_mode}",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        # Match summary
        duration_text = f"{game_duration // 60}m {game_duration % 60}s"
        time_ago = datetime.utcnow() - game_creation
        if time_ago.days > 0:
            time_text = f"{time_ago.days}d ago"
        elif time_ago.seconds > 3600:
            time_text = f"{time_ago.seconds // 3600}h ago"
        else:
            time_text = f"{time_ago.seconds // 60}m ago"
        
        embed.description = (
            f"**Result:** {result_text}\n"
            f"**Duration:** {duration_text}\n"
            f"**Played:** {time_text}"
        )
        
        # KDA with visual styling
        kda_ratio = (kills + assists) / max(deaths, 1)
        kda_rating = self._get_kda_rating(kda_ratio)
        kda_emoji = "🔥" if kda_ratio >= 3 else "⚡" if kda_ratio >= 2 else "⚔️"
        
        embed.add_field(
            name=f"{kda_emoji} KDA",
            value=f"**{kills}/{deaths}/{assists}**\n"
                  f"Ratio: {kda_ratio:.2f}\n"
                  f"Rating: {kda_rating}",
            inline=True
        )
        
        # Performance metrics
        embed.add_field(
            name="📊 Performance", 
            value=f"**CS:** {cs}\n"
                  f"**Vision:** {vision_score}\n"
                  f"**Damage:** {damage_dealt:,}",
            inline=True
        )
        
        # Economy
        embed.add_field(
            name="💰 Economy",
            value=f"**Gold:** {gold_earned:,}\n"
                  f"**GPM:** {(gold_earned / (game_duration / 60)):.0f}\n"
                  f"**CSPM:** {(cs / (game_duration / 60)):.1f}",
            inline=True
        )
        
        # Items (if available)
        items = []
        for i in range(7):  # 6 items + trinket
            item = player_data.get(f'item{i}', 0)
            if item > 0:
                items.append(str(item))
        
        if items:
            embed.add_field(
                name="🎒 Final Build",
                value=" • ".join(items[:6]) if items else "No items",
                inline=False
            )
        
        # Set champion icon as thumbnail
        champion_id = self._get_champion_id_by_name(champion_name)
        if champion_id:
            embed.set_thumbnail(url=f"{self.champion_icon_base}/{champion_id}.png")
        
        return embed
    
    def _get_kda_rating(self, kda_ratio: float) -> str:
        """Get KDA performance rating"""
        if kda_ratio >= 3.0:
            return "Exceptional"
        elif kda_ratio >= 2.0:
            return "Great"
        elif kda_ratio >= 1.5:
            return "Good"
        elif kda_ratio >= 1.0:
            return "Average"
        else:
            return "Poor"
    
    def _get_champion_id_by_name(self, champion_name: str) -> Optional[int]:
        """Get champion ID by name from champion data"""
        for champ_id, champ_data in self.champion_data.items():
            if champ_data.get('name', '').lower() == champion_name.lower():
                return champ_id
        return None
    
    # Interactive Elements
    
    def get_interactive_elements(self, embed_type: str) -> List[InteractiveElement]:
        """Get interactive elements for different embed types"""
        elements = {
            "live_game": [
                InteractiveElement("📊", "detailed_stats", "Show detailed player statistics"),
                InteractiveElement("🔄", "refresh", "Refresh live game data"),
                InteractiveElement("📈", "probability", "Show win probability breakdown"),
                InteractiveElement("⏱️", "history", "View recent match history")
            ],
            "profile": [
                InteractiveElement("🎮", "live_check", "Check for live game"),
                InteractiveElement("📊", "detailed_stats", "Show detailed statistics"),
                InteractiveElement("🏆", "achievements", "View achievements"),
                InteractiveElement("📈", "match_history", "Recent matches")
            ],
            "leaderboard": [
                InteractiveElement("🔄", "refresh", "Refresh leaderboard"),
                InteractiveElement("📊", "stats", "Show different stats"),
                InteractiveElement("🏆", "achievements", "Achievement leaderboard"),
                InteractiveElement("⏰", "weekly", "Weekly leaderboard")
            ]
        }
        
        return elements.get(embed_type, [])
