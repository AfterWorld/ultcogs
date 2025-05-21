# Updated v2_components.py file using Discord Components V2

import discord
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class V2ComponentsHelper:
    """Helper class for using Discord V2 Components with direct HTTP API access"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def send_summoner_profile_with_components_v2(self, ctx, summoner_data, rank_data, mastery_data, region):
        """
        Send a summoner profile message with champion icons using Components V2
        """
        try:
            # Create the primary container for the profile
            profile_container = {
                "type": 17,  # Container type
                "components": [
                    # Header section with summoner info
                    {
                        "type": 9,  # Section type
                        "components": [
                            {
                                "type": 10,  # TextDisplay type
                                "content": f"# {summoner_data['gameName']}#{summoner_data['tagLine']}\n**Level {summoner_data.get('summonerLevel', 'N/A')}** • {region.upper()} Region"
                            }
                        ]
                    }
                ]
            }
            
            # Add profile icon if available
            if "profileIconId" in summoner_data:
                profile_container["components"].append({
                    "type": 12,  # Media gallery type
                    "items": [
                        {
                            "media": {
                                "url": f"http://ddragon.leagueoflegends.com/cdn/13.24.1/img/profileicon/{summoner_data['profileIconId']}.png"
                            }
                        }
                    ]
                })
            
            # Add ranked information
            rank_section = {
                "type": 9,  # Section type
                "components": [
                    {
                        "type": 10,  # TextDisplay type
                        "content": "## Ranked Status"
                    }
                ]
            }
            
            if rank_data:
                for rank in rank_data[:2]:  # Show top 2 ranked queues
                    queue_type = rank["queueType"].replace("_", " ").title()
                    tier = rank.get("tier", "Unranked").upper()
                    division = rank.get("rank", "")
                    lp = rank.get("leaguePoints", 0)
                    wins = rank.get("wins", 0)
                    losses = rank.get("losses", 0)
                    
                    if tier != "UNRANKED":
                        winrate = round((wins / (wins + losses)) * 100, 1) if (wins + losses) > 0 else 0
                        
                        rank_section["components"].append({
                            "type": 10,  # TextDisplay type
                            "content": f"### {queue_type}\n**{tier} {division}** • {lp} LP\n**W/L:** {wins}W / {losses}L • **WR:** {winrate}%"
                        })
                    else:
                        rank_section["components"].append({
                            "type": 10,  # TextDisplay type
                            "content": f"### {queue_type}\n❓ **Unranked**"
                        })
            else:
                rank_section["components"].append({
                    "type": 10,  # TextDisplay type
                    "content": "❓ **Unranked in all queues**"
                })
            
            # Add rank section to the container
            profile_container["components"].append(rank_section)
            
            # Add a divider
            profile_container["components"].append({
                "type": 14  # Divider type
            })
            
            # Add champion mastery section
            if mastery_data:
                # Add header for champion mastery
                profile_container["components"].append({
                    "type": 10,  # TextDisplay type
                    "content": "## Champion Mastery"
                })
                
                # Add each champion in its own section
                for i, mastery in enumerate(mastery_data[:5]):  # Show top 5 champions
                    champion_id = mastery["championId"]
                    champion_name = mastery.get("championName", f"Champion {champion_id}")
                    level = mastery["championLevel"]
                    points = mastery["championPoints"]
                    
                    # Create a section for this champion
                    champ_section = {
                        "type": 9,  # Section type
                        "components": [
                            {
                                "type": 10,  # TextDisplay type
                                "content": f"**#{i+1}: {champion_name}**\nLevel {level} - {points:,} points"
                            }
                        ]
                    }
                    
                    # Add champion icon as an accessory
                    icon_url = f"https://raw.githubusercontent.com/AfterWorld/ultcogs/main/lol/championicons/{champion_id}.png"
                    champ_section["accessory"] = {
                        "type": 4,  # Thumbnail type
                        "image": {
                            "url": icon_url
                        }
                    }
                    
                    # Add this champion section to the container
                    profile_container["components"].append(champ_section)
            
            # Create the message payload with Components V2 flag
            payload = {
                "flags": 32768,  # IS_COMPONENTS_V2 flag
                "components": [profile_container]
            }
            
            # Use Discord.py's HTTP interface to send the message
            try:
                await ctx.bot.http.request(
                    discord.http.Route('POST', '/channels/{channel_id}/messages', 
                                      channel_id=ctx.channel.id),
                    json=payload
                )
                return True
            except Exception as e:
                logger.error(f"Error sending message with Components V2: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error preparing Components V2 message: {e}")
            # Fallback to traditional method
            await self.fallback_send_summoner_profile(ctx, summoner_data, rank_data, mastery_data, region)
            return False
    
    async def send_live_game_with_components_v2(self, ctx, summoner_data, game_data, region):
        """Send live game info with champion icon using Components V2"""
        try:
            if game_data:
                # Game info
                game_mode = game_data["gameMode"]
                game_length = game_data["gameLength"]
                game_minutes = game_length // 60
                game_seconds = game_length % 60
                
                # Create the container for live game info
                live_game_container = {
                    "type": 17,  # Container type
                    "components": [
                        # Header section
                        {
                            "type": 10,  # TextDisplay type
                            "content": f"# 🔴 Live Game - {summoner_data['gameName']}#{summoner_data['tagLine']}"
                        },
                        
                        # Game info section
                        {
                            "type": 9,  # Section type
                            "components": [
                                {
                                    "type": 10,  # TextDisplay type
                                    "content": f"**🎮 Game Mode:** {game_mode}\n**⏱️ Game Length:** {game_minutes}m {game_seconds}s\n**🌍 Region:** {region.upper()}"
                                }
                            ]
                        }
                    ]
                }
                
                # Find the player's champion
                for participant in game_data["participants"]:
                    if participant["puuid"] == summoner_data["puuid"]:
                        champion_id = participant.get("championId", 0)
                        champion_name = participant.get("championName", f"Champion {champion_id}")
                        
                        # Add champion section
                        champ_section = {
                            "type": 9,  # Section type
                            "components": [
                                {
                                    "type": 10,  # TextDisplay type
                                    "content": f"# Currently Playing: {champion_name}"
                                }
                            ]
                        }
                        
                        # Add champion icon media gallery
                        icon_url = f"https://raw.githubusercontent.com/AfterWorld/ultcogs/main/lol/championicons/{champion_id}.png"
                        live_game_container["components"].append({
                            "type": 12,  # Media gallery type
                            "items": [
                                {
                                    "media": {
                                        "url": icon_url
                                    }
                                }
                            ]
                        })
                        
                        # Add the champion section
                        live_game_container["components"].append(champ_section)
                        break
                
                # Add footer
                live_game_container["components"].append({
                    "type": 10,  # TextDisplay type
                    "content": "🔴 Currently in game"
                })
                
            else:
                # Not in game container
                live_game_container = {
                    "type": 17,  # Container type
                    "components": [
                        {
                            "type": 10,  # TextDisplay type
                            "content": f"# {summoner_data['gameName']}#{summoner_data['tagLine']}\nNot currently in a game"
                        },
                        {
                            "type": 10,  # TextDisplay type
                            "content": f"**🌍 Region:** {region.upper()}\n⚫ Offline"
                        }
                    ]
                }
            
            # Create the message payload with Components V2 flag
            payload = {
                "flags": 32768,  # IS_COMPONENTS_V2 flag
                "components": [live_game_container]
            }
            
            # Use Discord.py's HTTP interface to send the message
            try:
                await ctx.bot.http.request(
                    discord.http.Route('POST', '/channels/{channel_id}/messages', 
                                      channel_id=ctx.channel.id),
                    json=payload
                )
                return True
            except Exception as e:
                logger.error(f"Error sending message with Components V2: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error preparing Components V2 message: {e}")
            # Fallback to traditional method
            await self.fallback_send_live_game(ctx, summoner_data, game_data, region)
            return False
    
    async def send_match_history_with_components_v2(self, ctx, summoner_data, matches, region):
        """Send match history with champion icons using Components V2"""
        try:
            if not matches:
                await ctx.send("❌ No recent matches found.")
                return True
            
            # Create the container for match history
            match_history_container = {
                "type": 17,  # Container type
                "components": [
                    # Header section
                    {
                        "type": 10,  # TextDisplay type
                        "content": f"# 📜 Recent Matches - {summoner_data['gameName']}#{summoner_data['tagLine']}"
                    },
                    
                    # Region info
                    {
                        "type": 10,  # TextDisplay type
                        "content": f"Recent matches in {region.upper()}"
                    },
                    
                    # Add a divider
                    {
                        "type": 14  # Divider type
                    }
                ]
            }
            
            # Add each match in its own section
            for i, match in enumerate(matches[:5]):  # Show up to 5 recent matches
                participant = match['participant']
                details = match['details']
                
                # Match info
                win = participant["win"]
                result_text = "Victory" if win else "Defeat"
                champion_name = participant["championName"]
                champion_id = participant.get("championId", 0)
                kills = participant["kills"]
                deaths = participant["deaths"]
                assists = participant["assists"]
                kda_ratio = (kills + assists) / max(deaths, 1)
                
                # Game info
                game_mode = details["info"]["gameMode"]
                game_duration = details["info"]["gameDuration"]
                duration_mins = game_duration // 60
                duration_secs = game_duration % 60
                
                # Create a section for this match
                match_section = {
                    "type": 9,  # Section type
                    "components": [
                        {
                            "type": 10,  # TextDisplay type
                            "content": f"### Match {i+1}: {result_text}\n**{champion_name}** • {kills}/{deaths}/{assists} ({kda_ratio:.2f})\n{game_mode} • {duration_mins}m {duration_secs}s"
                        }
                    ]
                }
                
                # Add champion icon as an accessory
                icon_url = f"https://raw.githubusercontent.com/AfterWorld/ultcogs/main/lol/championicons/{champion_id}.png"
                match_section["accessory"] = {
                    "type": 4,  # Thumbnail type
                    "image": {
                        "url": icon_url
                    }
                }
                
                # Add this match section to the container
                match_history_container["components"].append(match_section)
                
                # Add a divider after each match (except the last one)
                if i < min(len(matches), 5) - 1:
                    match_history_container["components"].append({
                        "type": 14  # Divider type
                    })
            
            # Create the message payload with Components V2 flag
            payload = {
                "flags": 32768,  # IS_COMPONENTS_V2 flag
                "components": [match_history_container]
            }
            
            # Use Discord.py's HTTP interface to send the message
            try:
                await ctx.bot.http.request(
                    discord.http.Route('POST', '/channels/{channel_id}/messages', 
                                      channel_id=ctx.channel.id),
                    json=payload
                )
                return True
            except Exception as e:
                logger.error(f"Error sending message with Components V2: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error preparing Components V2 message: {e}")
            # Fallback to traditional method
            await self.fallback_send_match_history(ctx, summoner_data, matches, region)
            return False
    
    # Keep the fallback methods in case Components V2 fails
    async def fallback_send_summoner_profile(self, ctx, summoner_data, rank_data, mastery_data, region):
        """Fallback method to display summoner profile using multiple embeds"""
        embed_factory = ctx.cog.embed_factory
        
        # Main profile embed
        main_embed = embed_factory.create_summoner_embed(summoner_data, rank_data, region)
        await ctx.send(embed=main_embed)
        
        # Send separate embeds for each champion mastery
        if mastery_data:
            for i, mastery in enumerate(mastery_data[:3]):  # Limit to top 3 to avoid spam
                champion_id = mastery["championId"]
                champion_name = mastery.get("championName", f"Champion {champion_id}")
                level = mastery["championLevel"]
                points = mastery["championPoints"]
                
                # Create champion embed
                embed = discord.Embed(
                    title=f"Champion #{i+1}: {champion_name}",
                    description=f"Level {level} - {points:,} points",
                    color=discord.Color.purple()
                )
                
                # Set thumbnail to champion icon
                icon_url = embed_factory.get_custom_champion_icon_url(champion_id)
                embed.set_thumbnail(url=icon_url)
                
                await ctx.send(embed=embed)

    async def fallback_send_live_game(self, ctx, summoner_data, game_data, region):
        """Fallback method to display live game info using embeds"""
        embed_factory = ctx.cog.embed_factory
        
        # Main game info
        main_embed = embed_factory.create_live_game_embed(summoner_data, game_data, region)
        await ctx.send(embed=main_embed)
        
        # If in game, add champion info
        if game_data:
            for participant in game_data["participants"]:
                if participant["puuid"] == summoner_data["puuid"]:
                    champion_id = participant.get("championId", 0)
                    champion_name = participant.get("championName", f"Champion {champion_id}")
                    
                    # Create champion embed
                    embed = discord.Embed(
                        title=f"Currently Playing: {champion_name}",
                        color=discord.Color.red()
                    )
                    
                    # Set image to champion icon
                    icon_url = embed_factory.get_custom_champion_icon_url(champion_id)
                    embed.set_image(url=icon_url)
                    
                    await ctx.send(embed=embed)
                    break

    async def fallback_send_match_history(self, ctx, summoner_data, matches, region):
        """Fallback method to display match history using embeds"""
        if not matches:
            await ctx.send("❌ No recent matches found.")
            return
        
        embed_factory = ctx.cog.embed_factory
        
        # Summary embed
        main_embed = discord.Embed(
            title=f"📜 Recent Matches - {summoner_data['gameName']}#{summoner_data['tagLine']}",
            color=0xFF6B35,
            description=f"Last {len(matches)} matches in {region.upper()}",
            timestamp=datetime.now()
        )
        
        await ctx.send(embed=main_embed)
        
        # Individual match embeds with champion images
        for i, match in enumerate(matches[:3]):  # Limit to 3 recent matches to avoid spam
            participant = match['participant']
            details = match['details']
            
            match_embed = embed_factory.create_match_embed(summoner_data, details, participant)
            await ctx.send(embed=match_embed)
    
    def _get_mastery_color(self, level: int) -> discord.Color:
        """Get color based on champion mastery level"""
        colors = {
            7: discord.Color.purple(),   # Level 7
            6: discord.Color.magenta(),  # Level 6
            5: discord.Color.red(),      # Level 5
            4: discord.Color.blue(),     # Level 4
            3: discord.Color.green(),    # Level 3
            2: discord.Color.gold(),     # Level 2
            1: discord.Color.light_grey() # Level 1
        }
        return colors.get(level, discord.Color.default())
