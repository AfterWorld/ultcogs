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
    
    def create_build_embed(self, champion: Dict, build_data: Dict) -> discord.Embed:
        """Create a champion build recommendation embed"""
        embed = discord.Embed(
            title=f"🏗️ {champion['name']} Build Guide",
            description=f"*{champion['title']}*",
            color=0x0596AA,
            timestamp=datetime.now()
        )
        
        # Champion icon
        icon_url = f"http://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{champion['id']}.png"
        embed.set_thumbnail(url=icon_url)
        
        # Role information
        role_emoji = self.get_champion_role_emoji(champion["tags"])
        embed.add_field(
            name=f"{role_emoji} Primary Role",
            value=" • ".join(champion["tags"]),
            inline=True
        )
        
        # Starting items
        starting_items = build_data.get("starting_items", [])
        if starting_items:
            starting_text = []
            for item in starting_items[:4]:  # Show top 4 starting items
                starting_text.append(f"• {item['name']}")
            
            embed.add_field(
                name="🚀 Starting Items",
                value="\n".join(starting_text),
                inline=True
            )
        
        # Boots options
        boots = build_data.get("boots", [])
        if boots:
            boots_text = []
            for boot in boots[:3]:  # Show top 3 boots
                boots_text.append(f"• {boot['name']}")
            
            embed.add_field(
                name="👟 Boots Options", 
                value="\n".join(boots_text),
                inline=True
            )
        
        # Core items by role
        core_items = build_data.get("core_items", [])
        if core_items:
            core_text = []
            for item in core_items[:4]:  # Show top 4 core items
                core_text.append(f"• {item['name']}")
            
            embed.add_field(
                name="⚔️ Core Items",
                value="\n".join(core_text),
                inline=False
            )
        
        # Popular builds
        popular_builds = build_data.get("popular_builds", [])
        if popular_builds:
            for i, build in enumerate(popular_builds[:2]):  # Show top 2 builds
                build_items = []
                items_data = build_data.get("items", {})
                
                # Get item names from the build's item IDs
                for item_id in build.get("items", [])[:6]:  # Show up to 6 items
                    if item_id in items_data:
                        item_name = items_data[item_id]["name"]
                        build_items.append(f"• {item_name}")
                    else:
                        # Fallback for items that might not be in the items data
                        build_items.append(f"• Item {item_id}")
                
                if build_items:
                    embed.add_field(
                        name=f"📋 {build['name']}",
                        value=f"*{build['description']}*\n" + "\n".join(build_items[:4]),  # Limit to 4 items per build
                        inline=True
                    )
        
        # Situational items
        situational = build_data.get("situational", [])
        if situational:
            situational_text = []
            for item in situational[:4]:  # Show top 4 situational items
                situational_text.append(f"• {item['name']}")
            
            embed.add_field(
                name="🔄 Situational Items",
                value="\n".join(situational_text),
                inline=False
            )
        
        # Add tips
        tips = self._get_build_tips(champion["tags"])
        if tips:
            embed.add_field(
                name="💡 Build Tips",
                value=tips,
                inline=False
            )
        
        embed.set_footer(
            text=f"Build recommendations • Patch {DDRAGON_VERSION}",
            icon_url=self.riot_logo
        )
        
        return embed

    def _get_build_tips(self, tags: List[str]) -> str:
        """Get build tips based on champion role"""
        if not tags:
            return "• Adapt your build to the game situation\n• Consider enemy team composition\n• Don't forget to upgrade your trinket"
            
        primary_role = tags[0]
        
        tips_by_role = {
            "Marksman": "• Prioritize attack damage and attack speed early\n• Consider armor penetration against tanks\n• Build defensively if behind or against assassins",
            "Mage": "• Focus on ability power and magic penetration\n• Get Zhonya's Hourglass against AD threats\n• Consider magic resist reduction for team fights",
            "Tank": "• Build resistances matching enemy damage types\n• Prioritize health and resistances over damage\n• Get utility items to help your team",
            "Fighter": "• Balance damage and survivability\n• Consider anti-healing items against sustain\n• Adapt build based on enemy composition",
            "Assassin": "• Prioritize lethality against squishy targets\n• Get items with active effects for outplays\n• Consider defensive items if falling behind",
            "Support": "• Focus on utility and team support\n• Build based on your ADC's needs\n• Prioritize vision control and map control"
        }
        
        return tips_by_role.get(primary_role, "• Adapt your build to the game situation\n• Consider enemy team composition\n• Build for your team's needs")
    
    # Add this method to your EmbedFactory class in embeds.py

    def create_me_profile_embed(self, summoner_data: Dict, rank_data: List[Dict], 
                           mastery_data: List[Dict], match_analysis: Dict, region: str) -> discord.Embed:
        """Create an enhanced profile embed that mimics the React card but in native Discord format"""
        embed_color = self.get_rank_color(rank_data)
        
        # Create description with header info
        description = (
            f"## {summoner_data['gameName']}#{summoner_data['tagLine']}\n"
            f"**Level {summoner_data.get('summonerLevel', 'N/A')}** • {region.upper()} Region\n\n"
        )
        
        embed = discord.Embed(
            title="League of Legends Profile",
            description=description,
            color=embed_color,
            timestamp=datetime.now()
        )
        
        # Profile icon
        if "profileIconId" in summoner_data:
            icon_url = f"http://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/profileicon/{summoner_data['profileIconId']}.png"
            embed.set_thumbnail(url=icon_url)
        
        # Ranked information with enhanced formatting
        if rank_data:
            rank_str = "## Ranked Status\n"
            
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
                    
                    # Color-coded win rate indicator
                    if winrate >= 60:
                        wr_indicator = "🟢"
                    elif winrate >= 50:
                        wr_indicator = "🟡"
                    else:
                        wr_indicator = "🔴"
                    
                    rank_str += (
                        f"### {rank_emoji} {queue_type}\n"
                        f"**{tier.title()} {division}** • {lp} LP\n"
                        f"**W/L:** {wins}W / {losses}L • **WR:** {wr_indicator} {winrate}%\n"
                    )
                    
                    # Add special status indicators
                    status = []
                    if rank.get("hotStreak"):
                        status.append("🔥 **Hot Streak!**")
                    if rank.get("veteran"):
                        status.append("⭐ Veteran")
                    if rank.get("inactive"):
                        status.append("💤 Inactive")
                        
                    if status:
                        rank_str += " • ".join(status) + "\n"
                        
                    rank_str += "\n"
                else:
                    rank_str += f"### {queue_type}\n❓ **Unranked**\n\n"
        else:
            rank_str = "## Ranked Status\n❓ **Unranked in all queues**\n\n"
        
        embed.description = description + rank_str
        
        # Top Champions section with mastery info
        if mastery_data:
            champions_field = ""
            for i, mastery in enumerate(mastery_data[:3], 1):
                # Level-based emojis
                level_emojis = {7: "💎", 6: "💜", 5: "🔥", 4: "⭐", 3: "⚡", 2: "✨", 1: "🔹"}
                level = mastery["championLevel"]
                level_emoji = level_emojis.get(level, "⭐")
                
                # Format points with commas
                points = mastery["championPoints"]
                formatted_points = f"{points:,}"
                
                champ_name = mastery.get("championName", f"Champion {mastery['championId']}")
                champions_field += f"**{i}.** {level_emoji} **{champ_name}** (Lvl {level}): {formatted_points} pts\n"
            
            embed.add_field(
                name="🏅 Top Champions",
                value=champions_field or "No mastery data available",
                inline=False
            )
        
        # Recent performance metrics with enhanced formatting
        if match_analysis:
            winrate = match_analysis.get('winrate', 0)
            kda = match_analysis.get('avg_kda', 0)
            
            # Winrate indicator
            if winrate >= 60:
                wr_indicator = "🔥 Excellent"
            elif winrate >= 50:
                wr_indicator = "✅ Good"
            else:
                wr_indicator = "🔄 Needs Improvement"
            
            # KDA indicator
            if kda >= 4.0:
                kda_indicator = "💯 Outstanding"
            elif kda >= 3.0:
                kda_indicator = "👍 Great"
            elif kda >= 2.0:
                kda_indicator = "👌 Average"
            else:
                kda_indicator = "👊 Fighting"
            
            # Performance section
            performance_field = (
                f"**Win Rate:** {winrate:.1f}% ({match_analysis.get('wins', 0)}W / {match_analysis.get('losses', 0)}L) {wr_indicator}\n"
                f"**KDA:** {match_analysis.get('avg_kda', 0):.2f} {kda_indicator}\n"
                f"**K/D/A:** {match_analysis.get('avg_kills', 0):.1f}/{match_analysis.get('avg_deaths', 0):.1f}/{match_analysis.get('avg_assists', 0):.1f}\n\n"
            )
            
            # Most played champions
            if match_analysis.get('most_played'):
                performance_field += "**Most Played Champions:**\n"
                for i, (champ_name, stats, *_) in enumerate(match_analysis['most_played'][:3], 1):
                    winrate = (stats["wins"] / stats["games"]) * 100
                    win_indicator = "🟢" if winrate >= 55 else "🟡" if winrate >= 45 else "🔴"
                    performance_field += f"{i}. **{champ_name}**: {win_indicator} {winrate:.1f}% WR ({stats['games']} games)\n"
            
            embed.add_field(
                name=f"📈 Recent Performance (Last {match_analysis.get('total_games', 0)} Games)",
                value=performance_field,
                inline=False
            )
        
        # Footer
        embed.set_footer(
            text=f"Your linked League of Legends account • Updated", 
            icon_url=self.riot_logo
        )
        
        return embed

    def get_custom_champion_icon_url(self, champion_key: int) -> str:
        """Get custom champion icon URL from champion key (numerical ID)"""
        return f"https://raw.githubusercontent.com/AfterWorld/ultcogs/main/lol/championicons/{champion_key}.png"

    def create_me_profile_embed(self, summoner_data: Dict, rank_data: List[Dict], 
                        mastery_data: List[Dict], match_analysis: Dict, region: str) -> discord.Embed:
        """Create an enhanced profile embed that mimics the React card but in native Discord format"""
        embed_color = self.get_rank_color(rank_data)
        
        # Create description with header info
        description = (
            f"## {summoner_data['gameName']}#{summoner_data['tagLine']}\n"
            f"**Level {summoner_data.get('summonerLevel', 'N/A')}** • {region.upper()} Region\n\n"
        )
        
        embed = discord.Embed(
            title="League of Legends Profile",
            description=description,
            color=embed_color,
            timestamp=datetime.now()
        )
        
        # Profile icon
        if "profileIconId" in summoner_data:
            icon_url = f"http://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/profileicon/{summoner_data['profileIconId']}.png"
            embed.set_thumbnail(url=icon_url)
        
        # Ranked information with enhanced formatting
        if rank_data:
            rank_str = "## Ranked Status\n"
            
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
                    
                    # Color-coded win rate indicator
                    if winrate >= 60:
                        wr_indicator = "🟢"
                    elif winrate >= 50:
                        wr_indicator = "🟡"
                    else:
                        wr_indicator = "🔴"
                    
                    rank_str += (
                        f"### {rank_emoji} {queue_type}\n"
                        f"**{tier.title()} {division}** • {lp} LP\n"
                        f"**W/L:** {wins}W / {losses}L • **WR:** {wr_indicator} {winrate}%\n"
                    )
                    
                    # Add special status indicators
                    status = []
                    if rank.get("hotStreak"):
                        status.append("🔥 **Hot Streak!**")
                    if rank.get("veteran"):
                        status.append("⭐ Veteran")
                    if rank.get("inactive"):
                        status.append("💤 Inactive")
                        
                    if status:
                        rank_str += " • ".join(status) + "\n"
                        
                    rank_str += "\n"
                else:
                    rank_str += f"### {queue_type}\n❓ **Unranked**\n\n"
        else:
            rank_str = "## Ranked Status\n❓ **Unranked in all queues**\n\n"
        
        embed.description = description + rank_str
        
        # Top Champions section with mastery info - USE CHAMPION ICONS NOW
        if mastery_data:
            champions_field = ""
            for i, mastery in enumerate(mastery_data[:3], 1):
                # Level-based emojis
                level_emojis = {7: "💎", 6: "💜", 5: "🔥", 4: "⭐", 3: "⚡", 2: "✨", 1: "🔹"}
                level = mastery["championLevel"]
                level_emoji = level_emojis.get(level, "⭐")
                
                # Format points with commas
                points = mastery["championPoints"]
                formatted_points = f"{points:,}"
                
                champ_name = mastery.get("championName", f"Champion {mastery['championId']}")
                
                # Add champion icon URL
                champion_icon = self.get_custom_champion_icon_url(mastery['championId'])
                champions_field += f"**{i}.** {level_emoji} **[{champ_name}]({champion_icon})** (Lvl {level}): {formatted_points} pts\n"
            
            embed.add_field(
                name="🏅 Top Champions",
                value=champions_field or "No mastery data available",
                inline=False
            )
        
        # Recent performance metrics with enhanced formatting
        if match_analysis:
            winrate = match_analysis.get('winrate', 0)
            kda = match_analysis.get('avg_kda', 0)
            
            # Winrate indicator
            if winrate >= 60:
                wr_indicator = "🔥 Excellent"
            elif winrate >= 50:
                wr_indicator = "✅ Good"
            else:
                wr_indicator = "🔄 Needs Improvement"
            
            # KDA indicator
            if kda >= 4.0:
                kda_indicator = "💯 Outstanding"
            elif kda >= 3.0:
                kda_indicator = "👍 Great"
            elif kda >= 2.0:
                kda_indicator = "👌 Average"
            else:
                kda_indicator = "👊 Fighting"
            
            # Performance section
            performance_field = (
                f"**Win Rate:** {winrate:.1f}% ({match_analysis.get('wins', 0)}W / {match_analysis.get('losses', 0)}L) {wr_indicator}\n"
                f"**KDA:** {match_analysis.get('avg_kda', 0):.2f} {kda_indicator}\n"
                f"**K/D/A:** {match_analysis.get('avg_kills', 0):.1f}/{match_analysis.get('avg_deaths', 0):.1f}/{match_analysis.get('avg_assists', 0):.1f}\n\n"
            )
            
            # Most played champions with CHAMPION ICONS
            if match_analysis.get('most_played'):
                performance_field += "**Most Played Champions:**\n"
                for i, (champ_name, stats, champion_id) in enumerate(match_analysis['most_played'][:3], 1):
                    winrate = (stats["wins"] / stats["games"]) * 100
                    win_indicator = "🟢" if winrate >= 55 else "🟡" if winrate >= 45 else "🔴"
                    
                    # Use champion icon URL if we have the champion ID
                    if champion_id:
                        champion_icon = self.get_custom_champion_icon_url(champion_id)
                        performance_field += f"{i}. **[{champ_name}]({champion_icon})**: {win_indicator} {winrate:.1f}% WR ({stats['games']} games)\n"
                    else:
                        performance_field += f"{i}. **{champ_name}**: {win_indicator} {winrate:.1f}% WR ({stats['games']} games)\n"
            
            embed.add_field(
                name=f"📈 Recent Performance (Last {match_analysis.get('total_games', 0)} Games)",
                value=performance_field,
                inline=False
            )
        
        # Footer
        embed.set_footer(
            text=f"Your linked League of Legends account • Updated", 
            icon_url=self.riot_logo
        )
        
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
                    
                    # Use custom champion icon URL
                    champion_icon = self.get_custom_champion_icon_url(champion_id)
                    
                    # Add champion as an image using the icon URL in the description
                    embed.add_field(
                        name="🏅 Champion",
                        value=f"[Champion Icon]({champion_icon})",
                        inline=True
                    )
                    
                    # Set the champion icon as the thumbnail
                    embed.set_thumbnail(url=champion_icon)
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
                    
                    # Use custom champion icon URL
                    champion_icon = self.get_custom_champion_icon_url(champion_id)
                    
                    # Add champion info
                    embed.add_field(
                        name="🏆 Champion",
                        value=f"[Champion Icon]({champion_icon})",
                        inline=True
                    )
                    
                    # Set the thumbnail to the champion icon
                    embed.set_thumbnail(url=champion_icon)
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

    def create_match_embed(self, summoner_data: Dict, match_details: Dict, participant: Dict) -> discord.Embed:
        """Create an enhanced match embed"""
        win = participant["win"]
        embed_color = 0x00FF7F if win else 0xFF6B6B
        
        # Game info
        game_mode = match_details["info"]["gameMode"]
        game_duration = match_details["info"]["gameDuration"]
        champion = participant["championName"]
        champion_id = participant.get("championId", 0)
        
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
        
        # Champion image - use custom champion icon
        if champion_id:
            champion_icon = self.get_custom_champion_icon_url(champion_id)
        else:
            # Fallback to Data Dragon if needed
            champion_icon = f"http://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{champion}.png"
        
        embed.set_thumbnail(url=champion_icon)
        
        return embed
