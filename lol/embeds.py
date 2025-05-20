# lol/embeds.py - Embed creation methods
import discord
from datetime import datetime
from typing import Dict, List, Any, Optional

from .constants import (
    RANK_EMOJIS, 
    CHAMPION_ROLE_EMOJIS, 
    GAME_MODE_EMOJIS, 
    RANK_COLORS,
    DDRAGON_VERSION,
    QUEUE_TYPES  
)

class EmbedFactory:
    """Factory class for creating Discord embeds"""
    
    def __init__(self):
        self.riot_logo = "https://raw.githubusercontent.com/RiotGamesMinions/DataDragon-Layouts/main/logos/riot-logo.png"
    
    def get_rank_emoji(self, tier: str, with_text: bool = False) -> str:
        """Get emoji for rank tier"""
        emoji = RANK_EMOJIS.get(tier.upper(), "❓")
        if with_text:
            return f"{emoji} {tier.title()}"
        return emoji
    
    def get_champion_role_emoji(self, tags: List[str]) -> str:
        """Get emoji for champion role based on tags"""
        for tag in tags:
            if tag in CHAMPION_ROLE_EMOJIS:
                return CHAMPION_ROLE_EMOJIS[tag]
        return "⚪"
    
    def get_game_mode_emoji(self, mode: str) -> str:
        """Get emoji for game mode"""
        return GAME_MODE_EMOJIS.get(mode, "🎮")
    
    def get_rank_color(self, rank_data: List[Dict]) -> int:
        """Get embed color based on highest rank"""
        # Define tier hierarchy (highest to lowest)
        tier_hierarchy = [
            "CHALLENGER", "GRANDMASTER", "MASTER", "DIAMOND",
            "EMERALD", "PLATINUM", "GOLD", "SILVER", "BRONZE", "IRON"
        ]
        
        # Find highest rank from all queues
        highest_tier = "UNRANKED"
        for rank in rank_data:
            tier = rank.get("tier", "UNRANKED")
            if tier in tier_hierarchy:
                if highest_tier == "UNRANKED" or tier_hierarchy.index(tier) < tier_hierarchy.index(highest_tier):
                    highest_tier = tier
        
        return RANK_COLORS.get(highest_tier, 0x1E90FF)  # Default blue color
    
    def create_summoner_embed(self, summoner_data: Dict, rank_data: List[Dict], region: str) -> discord.Embed:
        """Create an enhanced summoner embed"""
        embed_color = self.get_rank_color(rank_data)
        
        embed = discord.Embed(
            title=f"🎮 {summoner_data['gameName']}#{summoner_data['tagLine']}",
            color=embed_color,
            timestamp=datetime.now()
        )
        
        # Profile icon
        if "profileIconId" in summoner_data:
            icon_url = f"http://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/profileicon/{summoner_data['profileIconId']}.png"
            embed.set_thumbnail(url=icon_url)
        
        # Basic info with emojis
        level = summoner_data.get("summonerLevel", "N/A")
        embed.add_field(
            name="📊 Summoner Level", 
            value=f"**{level}**", 
            inline=True
        )
        
        # Enhanced ranked information
        if rank_data:
            for rank in rank_data[:2]:  # Show top 2 ranked queues
                queue_type = rank["queueType"].replace("_", " ").title()
                tier = rank.get("tier", "Unranked").upper()
                division = rank.get("rank", "")
                lp = rank.get("leaguePoints", 0)
                wins = rank.get("wins", 0)
                losses = rank.get("losses", 0)
                
                if tier != "UNRANKED":
                    rank_emoji = self.get_rank_emoji(tier)
                    winrate = round((wins / (wins + losses)) * 100, 1) if (wins + losses) > 0 else 0
                    
                    # Color-coded win rate
                    if winrate >= 60:
                        wr_emoji = "🟢"
                    elif winrate >= 50:
                        wr_emoji = "🟡"
                    else:
                        wr_emoji = "🔴"
                    
                    rank_str = (
                        f"{rank_emoji} **{tier.title()} {division}** ({lp} LP)\n"
                        f"📈 {wins}W / {losses}L\n"
                        f"{wr_emoji} {winrate}% Win Rate"
                    )
                    
                    # Add streaks and special status
                    if rank.get("hotStreak"):
                        rank_str += "\n🔥 Hot Streak!"
                    if rank.get("veteran"):
                        rank_str += "\n⭐ Veteran"
                    if rank.get("inactive"):
                        rank_str += "\n💤 Inactive"
                        
                else:
                    rank_str = "❓ Unranked"
                
                embed.add_field(
                    name=f"🏆 {queue_type}", 
                    value=rank_str, 
                    inline=True
                )
        else:
            embed.add_field(
                name="🏆 Ranked Status", 
                value="❓ Unranked", 
                inline=True
            )
        
        # Footer with region and last update
        embed.set_footer(
            text=f"🌍 Region: {region.upper()} • Updated",
            icon_url=self.riot_logo
        )
        
        return embed
    
    def create_analysis_embed(self, summoner_data: Dict, analysis: Dict, region: str) -> discord.Embed:
        """Create a performance analysis embed"""
        winrate = analysis['winrate']
        embed_color = 0x00FF7F if winrate >= 50 else 0xFF6B6B
        
        embed = discord.Embed(
            title=f"📊 Performance Analysis - {summoner_data['gameName']}#{summoner_data['tagLine']}",
            color=embed_color,
            timestamp=datetime.now()
        )
        
        # Overall performance stats
        embed.add_field(
            name="📈 Overall Performance",
            value=f"**Games Analyzed:** {analysis['total_games']}\n"
                  f"**Win Rate:** {winrate:.1f}% ({analysis['wins']}W / {analysis['losses']}L)\n"
                  f"**Average KDA:** {analysis['avg_kda']:.2f}\n"
                  f"**K/D/A:** {analysis['avg_kills']:.1f} / {analysis['avg_deaths']:.1f} / {analysis['avg_assists']:.1f}",
            inline=False
        )
        
        # Most played champions
        if analysis['most_played']:
            champ_text = ""
            for champ, stats in analysis['most_played']:
                champ_winrate = (stats["wins"] / stats["games"]) * 100
                champ_kda = (stats["kills"] + stats["assists"]) / max(stats["deaths"], 1)
                champ_text += f"**{champ}** ({stats['games']} games)\n"
                champ_text += f"  {champ_winrate:.1f}% WR • {champ_kda:.2f} KDA\n"
            
            embed.add_field(
                name="🏆 Most Played Champions",
                value=champ_text,
                inline=False
            )
        
        # Recent trend
        recent_wins = analysis['recent_wins']
        recent_games = analysis['recent_games']
        
        if recent_wins >= 4:
            trend = "📈 Winning streak!"
        elif recent_wins <= 1:
            trend = "📉 Losing streak"
        else:
            trend = "📊 Mixed results"
        
        embed.add_field(
            name=f"🔄 Recent Trend (Last {recent_games} Games)",
            value=f"{trend}\n{recent_wins}W / {recent_games - recent_wins}L",
            inline=True
        )
        
        embed.add_field(
            name="🌍 Region", 
            value=region.upper(), 
            inline=True
        )
        
        embed.set_footer(
            text=f"Analysis based on {analysis['total_games']} recent games",
            icon_url=self.riot_logo
        )
        
        return embed
    
    def create_match_embed(self, summoner_data: Dict, match_details: Dict, participant: Dict) -> discord.Embed:
        """Create an enhanced match embed"""
        win = participant["win"]
        embed_color = 0x00FF7F if win else 0xFF6B6B
        
        # Game info
        game_mode = match_details["info"]["gameMode"]
        game_duration = match_details["info"]["gameDuration"]
        champion = participant["championName"]
        
        # KDA info
        kills = participant["kills"]
        deaths = participant["deaths"]
        assists = participant["assists"]
        kda_ratio = (kills + assists) / max(deaths, 1)
        
        # Result emoji and text
        result_emoji = "🏆" if win else "❌"
        result_text = "Victory" if win else "Defeat"
        
        embed = discord.Embed(
            title=f"{result_emoji} {result_text}",
            description=f"**{champion}** • {self._format_duration(game_duration)}",
            color=embed_color,
            timestamp=datetime.fromtimestamp(match_details["info"]["gameCreation"] / 1000)
        )
        
        # Game mode with emoji
        mode_emoji = self.get_game_mode_emoji(game_mode)
        embed.add_field(
            name=f"{mode_emoji} Game Mode",
            value=game_mode,
            inline=True
        )
        
        # Enhanced KDA display
        embed.add_field(
            name="⚔️ KDA",
            value=f"**{kills}** / {deaths} / **{assists}**\n({kda_ratio:.2f} ratio)",
            inline=True
        )
        
        # Damage and vision score if available
        if "totalDamageDealtToChampions" in participant:
            damage = participant["totalDamageDealtToChampions"]
            embed.add_field(
                name="💥 Damage to Champions",
                value=f"{damage:,}",
                inline=True
            )
        
        if "visionScore" in participant:
            vision = participant["visionScore"]
            embed.add_field(
                name="👁️ Vision Score",
                value=f"{vision}",
                inline=True
            )
        
        # Champion image
        champion_icon = f"http://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{champion}.png"
        embed.set_thumbnail(url=champion_icon)
        
        return embed
    
    def create_champion_embed(self, champion: Dict) -> discord.Embed:
        """Create an enhanced champion information embed"""
        embed = discord.Embed(
            title=f"🏛️ {champion['name']}",
            description=f"*{champion['title']}*",
            color=0x0596AA
        )
        
        # Champion splash art
        splash_url = f"http://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champion['id']}_0.jpg"
        embed.set_image(url=splash_url)
        
        # Champion icon
        icon_url = f"http://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{champion['id']}.png"
        embed.set_thumbnail(url=icon_url)
        
        # Enhanced role display with emojis
        role_emoji = self.get_champion_role_emoji(champion["tags"])
        embed.add_field(
            name=f"{role_emoji} Role",
            value=" • ".join(champion["tags"]),
            inline=True
        )
        
        # Difficulty with visual representation
        difficulty = champion['info']['difficulty']
        difficulty_bars = "▓" * difficulty + "░" * (10 - difficulty)
        embed.add_field(
            name="📊 Difficulty",
            value=f"{difficulty_bars} ({difficulty}/10)",
            inline=True
        )
        
        # Enhanced stats display
        stats = champion["stats"]
        embed.add_field(
            name="❤️ Health",
            value=f"{stats['hp']} (+{stats['hpperlevel']}/lvl)",
            inline=True
        )
        
        embed.add_field(
            name="🔮 Mana",
            value=f"{stats['mp']} (+{stats['mpperlevel']}/lvl)",
            inline=True
        )
        
        # Attack damage and speed
        embed.add_field(
            name="⚔️ Attack Damage",
            value=f"{stats['attackdamage']} (+{stats['attackdamageperlevel']}/lvl)",
            inline=True
        )
        
        embed.add_field(
            name="🗲 Attack Speed",
            value=f"{stats['attackspeed']:.3f} (+{stats['attackspeedperlevel']:.3f}%/lvl)",
            inline=True
        )
        
        # Defensive stats
        embed.add_field(
            name="🛡️ Armor",
            value=f"{stats['armor']} (+{stats['armorperlevel']}/lvl)",
            inline=True
        )
        
        embed.add_field(
            name="✨ Magic Resist",
            value=f"{stats['spellblock']} (+{stats['spellblockperlevel']}/lvl)",
            inline=True
        )
        
        # Movement and range
        embed.add_field(
            name="💨 Movement Speed",
            value=f"{stats['movespeed']}",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Attack Range",
            value=f"{stats['attackrange']}",
            inline=True
        )
        
        # Lore preview with proper length handling
        lore = champion.get("lore", "No lore available.")
        if len(lore) > 300:
            lore = lore[:297] + "..."
        
        embed.add_field(
            name="📜 Lore",
            value=lore,
            inline=False
        )
        
        # Footer with additional info
        embed.set_footer(
            text=f"Patch {DDRAGON_VERSION} • Data from Riot Games",
            icon_url=self.riot_logo
        )
        
        return embed
    
    def create_live_game_embed(self, summoner_data: Dict, game_data: Optional[Dict], region: str) -> discord.Embed:
        """Create a live game status embed"""
        if game_data:
            # In game
            embed = discord.Embed(
                title=f"🔴 Live Game - {summoner_data['gameName']}#{summoner_data['tagLine']}",
                color=0xFF0000,
                timestamp=datetime.now()
            )
            
            # Game info
            game_mode = game_data["gameMode"]
            game_length = game_data["gameLength"]
            game_minutes = game_length // 60
            game_seconds = game_length % 60
            
            embed.add_field(name="🎮 Game Mode", value=game_mode, inline=True)
            embed.add_field(name="⏱️ Game Length", value=f"{game_minutes}m {game_seconds}s", inline=True)
            embed.add_field(name="🌍 Region", value=region.upper(), inline=True)
            
            # Find the player's champion
            for participant in game_data["participants"]:
                if participant["puuid"] == summoner_data["puuid"]:
                    champion_id = participant.get("championId", 0)
                    embed.add_field(name="🏆 Champion", value=f"Champion ID: {champion_id}", inline=True)
                    break
            
            embed.set_footer(text="🔴 Currently in game")
        else:
            # Not in game
            embed = discord.Embed(
                title=f"{summoner_data['gameName']}#{summoner_data['tagLine']}",
                description="Not currently in a game",
                color=0x808080
            )
            embed.add_field(name="🌍 Region", value=region.upper(), inline=True)
            embed.set_footer(text="⚫ Offline")
        
        return embed
    
    def create_notification_embed(self, summoner_data: Dict, game_data: Optional[Dict], game_started: bool) -> discord.Embed:
        """Create an embed for live game notifications"""
        if game_started and game_data:
            # Game started notification
            embed = discord.Embed(
                title="🎮 Game Started!",
                description=f"**{summoner_data['gameName']}#{summoner_data['tagLine']}** started a game",
                color=0x00FF00,
                timestamp=datetime.now()
            )
            
            game_mode = game_data.get("gameMode", "Unknown")
            queue_id = game_data.get("gameQueueConfigId", 0)
            queue_type = QUEUE_TYPES.get(queue_id, f"Queue {queue_id}")
            
            embed.add_field(name="🎮 Game Mode", value=game_mode, inline=True)
            embed.add_field(name="🏆 Queue", value=queue_type, inline=True)
            embed.add_field(name="🌍 Region", value=summoner_data['region'].upper(), inline=True)
            
            # Find the player's champion
            for participant in game_data.get("participants", []):
                if participant["puuid"] == summoner_data["puuid"]:
                    champion_id = participant.get("championId", 0)
                    embed.add_field(name="🏅 Champion", value=f"Champion ID: {champion_id}", inline=True)
                    break
        else:
            # Game ended notification
            embed = discord.Embed(
                title="🏁 Game Ended",
                description=f"**{summoner_data['gameName']}#{summoner_data['tagLine']}** finished their game",
                color=0xFF6B35,
                timestamp=datetime.now()
            )
            
            embed.add_field(name="🌍 Region", value=summoner_data['region'].upper(), inline=True)
        
        return embed
    
    def _format_duration(self, seconds: int) -> str:
        """Format game duration into readable format"""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}m {seconds}s"