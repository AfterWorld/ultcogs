import discord
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class V2ComponentsHelper:
    """Helper class for using Discord V2 Components with direct HTTP API access"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def send_message_with_champion_icons(self, ctx, title, description, champion_ids, champion_names=None):
        """
        Send a message with champion icons using V2 components
        
        Parameters:
        ctx - Command context
        title - Message title
        description - Message description
        champion_ids - List of champion IDs (numerical) to display
        champion_names - Optional list of champion names (must match length of champion_ids)
        """
        if champion_names is None:
            champion_names = [f"Champion {cid}" for cid in champion_ids]
        
        try:
            # Instead of using components directly, let's use standard embeds as a workaround
            # This avoids the custom_id error issue
            
            # Create a message with the header
            await ctx.send(f"## {title}\n{description}")
            
            # Send individual embeds for each champion
            for champion_id, champion_name in zip(champion_ids, champion_names):
                embed = discord.Embed(
                    title=champion_name,
                    color=discord.Color.blue()
                )
                
                # Set the champion icon as the image
                icon_url = f"https://raw.githubusercontent.com/AfterWorld/ultcogs/main/lol/championicons/{champion_id}.png"
                embed.set_image(url=icon_url)
                
                # Send the embed
                await ctx.send(embed=embed)
            
            return True
        except Exception as e:
            import logging
            logging.error(f"Error sending message with champion icons: {e}")
            return False
    
    async def send_summoner_profile_with_champions(self, ctx, summoner_data, rank_data, mastery_data, region):
        """
        Send a summoner profile message with champion icons using standard embeds
        
        This sends a single summoner info embed followed by champion mastery embeds
        """
        try:
            # First send a standard embed with summoner info - ONLY ONCE
            embed_factory = ctx.cog.embed_factory  # Get embed factory from the cog
            embed = embed_factory.create_summoner_embed(summoner_data, rank_data, region)
            await ctx.send(embed=embed)
            
            # Then send champion mastery info with icons using standard embeds
            if mastery_data:
                # Send a header for the champion section
                await ctx.send(f"## Champion Mastery - {summoner_data['gameName']}#{summoner_data['tagLine']}")
                
                # Create individual embeds for top champions
                for i, mastery in enumerate(mastery_data[:5]):  # Show top 5 champions
                    champion_id = mastery["championId"]
                    champion_name = mastery.get("championName", f"Champion {champion_id}")
                    level = mastery["championLevel"]
                    points = mastery["championPoints"]
                    
                    # Create champion embed
                    embed = discord.Embed(
                        title=f"Champion #{i+1}: {champion_name}",
                        description=f"Level {level} - {points:,} points",
                        color=self._get_mastery_color(level)  # Add this method to get colors based on level
                    )
                    
                    # Set champion icon as the image
                    icon_url = ctx.cog.embed_factory.get_custom_champion_icon_url(champion_id)
                    embed.set_thumbnail(url=icon_url)  # Or use set_image() for larger icons
                    
                    await ctx.send(embed=embed)
                
                return True
            
        except Exception as e:
            import logging
            logging.error(f"Error sending summoner profile with champions: {e}")
            # Fallback to traditional method
            await self.fallback_send_summoner_profile(ctx, summoner_data, rank_data, mastery_data, region)
            return False
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
    
    async def send_live_game_with_champion_icon(self, ctx, summoner_data, game_data, region):
        """Send live game info with champion icon using V2 components"""
        try:
            # First send standard embed with game info
            embed_factory = ctx.cog.embed_factory
            embed = embed_factory.create_live_game_embed(summoner_data, game_data, region)
            await ctx.send(embed=embed)
            
            # If in game, send champion icon using V2 components
            if game_data:
                for participant in game_data["participants"]:
                    if participant["puuid"] == summoner_data["puuid"]:
                        champion_id = participant.get("championId", 0)
                        champion_name = participant.get("championName", f"Champion {champion_id}")
                        
                        title = "Currently Playing"
                        description = f"{summoner_data['gameName']} is playing:"
                        
                        success = await self.send_message_with_champion_icons(
                            ctx, title, description, [champion_id], [champion_name]
                        )
                        
                        if not success:
                            # Fallback to traditional method
                            await self.fallback_send_live_game(ctx, summoner_data, game_data, region)
                        break
            
            return True
        except Exception as e:
            logger.error(f"Error sending live game with champion icon: {e}")
            # Fallback to traditional method
            await self.fallback_send_live_game(ctx, summoner_data, game_data, region)
            return False
    
    async def send_match_history_with_champions(self, ctx, summoner_data, matches, region):
        """Send match history with champion icons using V2 components"""
        try:
            if not matches:
                await ctx.send("❌ No recent matches found.")
                return True
            
            # First send a summary embed
            embed_factory = ctx.cog.embed_factory
            embed = discord.Embed(
                title=f"📜 Recent Matches - {summoner_data['gameName']}#{summoner_data['tagLine']}",
                color=0xFF6B35,
                timestamp=datetime.now()
            )
            
            embed.set_footer(text=f"Recent matches in {region.upper()}")
            await ctx.send(embed=embed)
            
            # Extract champion info from matches
            champion_ids = []
            champion_names = []
            match_results = []
            
            for match in matches[:5]:  # Show up to 5 recent matches
                participant = match['participant']
                champion_id = participant.get("championId", 0)
                champion_name = participant["championName"]
                
                result = "Victory" if participant["win"] else "Defeat"
                kda = f"{participant['kills']}/{participant['deaths']}/{participant['assists']}"
                
                champion_ids.append(champion_id)
                champion_names.append(champion_name)
                match_results.append(f"**{result}** - {kda}")
            
            # Send champions using V2 components
            title = "Recent Champions Played"
            description = f"{summoner_data['gameName']}'s recent games:"
            
            success = await self.send_message_with_champion_icons(
                ctx, title, description, champion_ids, champion_names
            )
            
            if success:
                # Send match results in a regular message
                results_text = "\n".join([f"**{name}**: {result}" for name, result in zip(champion_names, match_results)])
                await ctx.send(f"**Match Results:**\n{results_text}")
            else:
                # Fallback to traditional method
                await self.fallback_send_match_history(ctx, summoner_data, matches, region)
            
            return True
        except Exception as e:
            logger.error(f"Error sending match history with champions: {e}")
            # Fallback to traditional method
            await self.fallback_send_match_history(ctx, summoner_data, matches, region)
            return False
    
    # Fallback methods for when v2 components fail
    
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
