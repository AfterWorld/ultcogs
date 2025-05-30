# gif_manager.py - NEW FILE
"""
Complete GIF Management System for Hunger Games
Handles GIF selection, loading, and integration with Discord embeds
"""

import os
import random
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import discord
from redbot.core import commands, Config

logger = logging.getLogger(__name__)

class GifManager:
    """Handles all GIF-related functionality for the Hunger Games bot"""
    
    def __init__(self, bot, config, base_path: str = "gifs"):
        self.bot = bot
        self.config = config
        self.base_path = Path(base_path)
        self.gif_cache = {}
        self.last_cache_update = 0
        self.cache_timeout = 300  # 5 minutes
        
        # Create directory structure if it doesn't exist
        self._create_directory_structure()
        
        # GIF categories and their subdirectories
        self.gif_structure = {
            "victory": {
                "general": "General victory celebrations",
                "high_kill": "Domination/massacre victories (5+ kills)",
                "medium_kill": "Skilled warrior victories (3-4 kills)", 
                "low_kill": "Strategic victories (1-2 kills)",
                "no_kill": "Peaceful/survival victories (0 kills)",
                "underdog": "Against-all-odds victories",
                "final_duel": "1v1 final showdown victories",
                "bloodbath": "Overwhelming massacre victories"
            },
            "death": {
                "general": "General elimination/death scenes",
                "brutal": "Violent/brutal deaths",
                "accident": "Accidental/environmental deaths",
                "betrayal": "Betrayal/backstab deaths",
                "heroic": "Noble/heroic deaths"
            },
            "sponsor": {
                "gift": "Gift/package deliveries",
                "revival": "Resurrection/revival scenes",
                "equipment": "Weapon/gear deliveries",
                "food": "Food/healing deliveries"
            },
            "alliance": {
                "formation": "Alliance/team formation",
                "betrayal": "Alliance betrayals",
                "cooperation": "Teamwork/cooperation"
            },
            "special": {
                "bloodbath": "Opening Cornucopia bloodbath",
                "finale": "Final showdown scenes",
                "feast": "Arena feast events",
                "environmental": "Arena hazard events"
            }
        }
    
    def _create_directory_structure(self):
        """Create the GIF directory structure"""
        try:
            for category in ["victory", "death", "sponsor", "alliance", "special"]:
                category_path = self.base_path / category
                category_path.mkdir(parents=True, exist_ok=True)
                
                # Create subdirectories based on structure
                if category in self.gif_structure:
                    for subcategory in self.gif_structure[category]:
                        subcategory_path = category_path / subcategory
                        subcategory_path.mkdir(exist_ok=True)
            
            logger.info(f"GIF directory structure created at {self.base_path}")
        except Exception as e:
            logger.error(f"Error creating GIF directory structure: {e}")
    
    def _scan_gifs(self) -> Dict[str, Dict[str, List[str]]]:
        """Scan the GIF directories and return available GIFs"""
        try:
            gif_files = {}
            supported_formats = ['.gif', '.webp', '.mp4', '.mov']
            
            for category_dir in self.base_path.iterdir():
                if category_dir.is_dir():
                    category = category_dir.name
                    gif_files[category] = {}
                    
                    for subcategory_dir in category_dir.iterdir():
                        if subcategory_dir.is_dir():
                            subcategory = subcategory_dir.name
                            files = []
                            
                            for file_path in subcategory_dir.iterdir():
                                if file_path.suffix.lower() in supported_formats:
                                    files.append(str(file_path))
                            
                            if files:
                                gif_files[category][subcategory] = files
            
            return gif_files
        except Exception as e:
            logger.error(f"Error scanning GIFs: {e}")
            return {}
    
    def _get_cached_gifs(self) -> Dict[str, Dict[str, List[str]]]:
        """Get GIFs from cache or rescan if cache is stale"""
        current_time = asyncio.get_event_loop().time()
        
        if (not self.gif_cache or 
            current_time - self.last_cache_update > self.cache_timeout):
            self.gif_cache = self._scan_gifs()
            self.last_cache_update = current_time
        
        return self.gif_cache
    
    def get_victory_gif(self, game_data: Dict, winner_data: Dict) -> Optional[str]:
        """Select appropriate victory GIF based on game context"""
        try:
            gifs = self._get_cached_gifs()
            victory_gifs = gifs.get("victory", {})
            
            if not victory_gifs:
                return None
            
            # Determine victory type
            total_players = len(game_data.get("players", {}))
            kills = winner_data.get("kills", 0)
            
            # Priority order for GIF selection
            preferred_categories = []
            
            if total_players == 2:
                preferred_categories.append("final_duel")
            
            if kills >= 7:
                preferred_categories.append("bloodbath")
            elif kills >= 5:
                preferred_categories.append("high_kill")
            elif kills >= 3:
                preferred_categories.append("medium_kill")
            elif kills >= 1:
                preferred_categories.append("low_kill")
            elif kills == 0:
                preferred_categories.append("no_kill")
            
            if total_players <= 5:
                preferred_categories.append("underdog")
            
            # Always add general as fallback
            preferred_categories.append("general")
            
            # Try to find a GIF from preferred categories
            for category in preferred_categories:
                if category in victory_gifs and victory_gifs[category]:
                    return random.choice(victory_gifs[category])
            
            # Final fallback - any victory GIF
            all_victory_gifs = []
            for category_gifs in victory_gifs.values():
                all_victory_gifs.extend(category_gifs)
            
            if all_victory_gifs:
                return random.choice(all_victory_gifs)
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting victory GIF: {e}")
            return None
    
    def get_death_gif(self, death_type: str = "general") -> Optional[str]:
        """Get a death/elimination GIF"""
        try:
            gifs = self._get_cached_gifs()
            death_gifs = gifs.get("death", {})
            
            if not death_gifs:
                return None
            
            # Try specific death type first
            if death_type in death_gifs and death_gifs[death_type]:
                return random.choice(death_gifs[death_type])
            
            # Fallback to general death GIFs
            if "general" in death_gifs and death_gifs["general"]:
                return random.choice(death_gifs["general"])
            
            # Final fallback - any death GIF
            all_death_gifs = []
            for category_gifs in death_gifs.values():
                all_death_gifs.extend(category_gifs)
            
            if all_death_gifs:
                return random.choice(all_death_gifs)
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting death GIF: {e}")
            return None
    
    def get_sponsor_gif(self, sponsor_type: str = "gift") -> Optional[str]:
        """Get a sponsor/gift GIF"""
        try:
            gifs = self._get_cached_gifs()
            sponsor_gifs = gifs.get("sponsor", {})
            
            if not sponsor_gifs:
                return None
            
            # Try specific sponsor type
            if sponsor_type in sponsor_gifs and sponsor_gifs[sponsor_type]:
                return random.choice(sponsor_gifs[sponsor_type])
            
            # Fallback to general gift GIFs
            if "gift" in sponsor_gifs and sponsor_gifs["gift"]:
                return random.choice(sponsor_gifs["gift"])
            
            # Final fallback - any sponsor GIF
            all_sponsor_gifs = []
            for category_gifs in sponsor_gifs.values():
                all_sponsor_gifs.extend(category_gifs)
            
            if all_sponsor_gifs:
                return random.choice(all_sponsor_gifs)
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting sponsor GIF: {e}")
            return None
    
    def get_special_gif(self, event_type: str) -> Optional[str]:
        """Get a special event GIF (bloodbath, finale, etc.)"""
        try:
            gifs = self._get_cached_gifs()
            special_gifs = gifs.get("special", {})
            
            if not special_gifs:
                return None
            
            if event_type in special_gifs and special_gifs[event_type]:
                return random.choice(special_gifs[event_type])
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting special GIF: {e}")
            return None
    
    def get_gif_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics about available GIFs"""
        try:
            gifs = self._get_cached_gifs()
            stats = {}
            
            for category, subcategories in gifs.items():
                stats[category] = {}
                for subcategory, gif_list in subcategories.items():
                    stats[category][subcategory] = len(gif_list)
            
            return stats
        except Exception as e:
            logger.error(f"Error getting GIF stats: {e}")
            return {}
    
    def clear_cache(self):
        """Clear the GIF cache to force rescan"""
        self.gif_cache = {}
        self.last_cache_update = 0
    
    async def upload_gif_url(self, url: str, category: str, subcategory: str, filename: str) -> bool:
        """Helper method to download and save a GIF from URL (for admin commands)"""
        try:
            import aiohttp
            
            category_path = self.base_path / category / subcategory
            category_path.mkdir(parents=True, exist_ok=True)
            
            file_path = category_path / filename
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        with open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        # Clear cache to include new GIF
                        self.clear_cache()
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Error uploading GIF: {e}")
            return False


# Add these methods to the existing HungerGames class in __init__.py

class HungerGamesGifCommands:
    """GIF management commands for HungerGames"""
    
    def __init__(self, parent_cog):
        self.parent = parent_cog
        self.gif_manager = GifManager(parent_cog.bot, parent_cog.config)
    
    @commands.group(name="gif", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def gif_commands(self, ctx):
        """GIF management commands for Hunger Games"""
        await ctx.send_help()
    
    @gif_commands.command(name="enable")
    async def gif_enable(self, ctx):
        """Enable GIF integration for Hunger Games"""
        try:
            await self.parent.config.guild(ctx.guild).enable_gifs.set(True)
            
            embed = discord.Embed(
                title="🎬 **GIF Integration Enabled!**",
                description="GIFs will now be displayed during games when available.",
                color=0x00FF00
            )
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error enabling GIFs: {str(e)}")
    
    @gif_commands.command(name="disable")
    async def gif_disable(self, ctx):
        """Disable GIF integration for Hunger Games"""
        try:
            await self.parent.config.guild(ctx.guild).enable_gifs.set(False)
            
            embed = discord.Embed(
                title="🚫 **GIF Integration Disabled**",
                description="GIFs will no longer be displayed during games.",
                color=0xFF0000
            )
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error disabling GIFs: {str(e)}")
    
    @gif_commands.command(name="stats")
    async def gif_stats(self, ctx):
        """Show GIF collection statistics"""
        try:
            stats = self.gif_manager.get_gif_stats()
            
            embed = discord.Embed(
                title="📊 **GIF Collection Statistics**",
                color=0x00CED1
            )
            
            total_gifs = 0
            
            for category, subcategories in stats.items():
                category_total = sum(subcategories.values())
                total_gifs += category_total
                
                if category_total > 0:
                    subcategory_text = "\n".join([
                        f"• {subcat}: {count}" 
                        for subcat, count in subcategories.items() 
                        if count > 0
                    ])
                    
                    embed.add_field(
                        name=f"🎬 **{category.title()}** ({category_total})",
                        value=subcategory_text if subcategory_text else "None",
                        inline=True
                    )
            
            embed.description = f"**Total GIFs:** {total_gifs}"
            
            if total_gifs == 0:
                embed.add_field(
                    name="📁 **No GIFs Found**",
                    value="Add GIF files to the `gifs/` directory to get started!",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting GIF stats: {str(e)}")
    
    @gif_commands.command(name="structure")
    async def gif_structure(self, ctx):
        """Show the GIF directory structure and descriptions"""
        try:
            embed = discord.Embed(
                title="📁 **GIF Directory Structure**",
                description="Organize your GIFs in these folders for automatic selection:",
                color=0x4169E1
            )
            
            for category, subcategories in self.gif_manager.gif_structure.items():
                structure_text = "\n".join([
                    f"• `{subcat}/` - {desc}"
                    for subcat, desc in subcategories.items()
                ])
                
                embed.add_field(
                    name=f"📂 **{category}//**",
                    value=structure_text,
                    inline=False
                )
            
            embed.add_field(
                name="📋 **Instructions**",
                value="1. Place GIF files in the appropriate folders\n"
                      "2. Supported formats: `.gif`, `.webp`, `.mp4`, `.mov`\n"
                      "3. Use `.hungergames gif stats` to verify files are detected\n"
                      "4. GIFs are automatically selected based on game context",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error showing structure: {str(e)}")
    
    @gif_commands.command(name="test")
    async def gif_test(self, ctx, category: str = "victory", subcategory: str = "general"):
        """Test GIF selection from a specific category"""
        try:
            # Test different GIF types
            if category == "victory":
                test_game = {"players": {"123": {"kills": 2}}}
                test_winner = {"kills": 2, "name": "TestPlayer"}
                gif_url = self.gif_manager.get_victory_gif(test_game, test_winner)
            elif category == "death":
                gif_url = self.gif_manager.get_death_gif(subcategory)
            elif category == "sponsor":
                gif_url = self.gif_manager.get_sponsor_gif(subcategory)
            elif category == "special":
                gif_url = self.gif_manager.get_special_gif(subcategory)
            else:
                return await ctx.send("❌ Invalid category! Use: victory, death, sponsor, special")
            
            if gif_url:
                embed = discord.Embed(
                    title=f"🎬 **GIF Test: {category}/{subcategory}**",
                    color=0x00FF00
                )
                embed.set_image(url=f"attachment://{os.path.basename(gif_url)}")
                
                with open(gif_url, 'rb') as f:
                    file = discord.File(f, filename=os.path.basename(gif_url))
                    await ctx.send(embed=embed, file=file)
            else:
                await ctx.send(f"❌ No GIFs found for {category}/{subcategory}")
                
        except Exception as e:
            await ctx.send(f"❌ Error testing GIF: {str(e)}")
    
    @gif_commands.command(name="reload")
    async def gif_reload(self, ctx):
        """Reload the GIF cache"""
        try:
            self.gif_manager.clear_cache()
            stats = self.gif_manager.get_gif_stats()
            total_gifs = sum(sum(subcats.values()) for subcats in stats.values())
            
            embed = discord.Embed(
                title="🔄 **GIF Cache Reloaded**",
                description=f"Found {total_gifs} GIFs across all categories.",
                color=0x00FF00
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error reloading GIFs: {str(e)}")


# Integration with game.py - Update the victory display method

async def _send_victory_display_with_gif(self, game: GameState, channel: discord.TextChannel, 
                                       winner_id: str, winner: PlayerData, prize: int):
    """Enhanced victory display with GIF integration"""
    try:
        # Check if GIFs are enabled for this guild
        gifs_enabled = await self.config.guild(channel.guild).enable_gifs()
        
        total_players = len(game["players"])
        victory_phrase = self._get_victory_phrase(game, winner)
        winner_emoji = self._get_player_emoji(winner)
        
        # Main victory embed
        embed = discord.Embed(color=0xFFD700)
        embed.title = victory_phrase
        
        # Try to add GIF if enabled
        gif_file = None
        if gifs_enabled and hasattr(self, 'gif_manager'):
            gif_path = self.gif_manager.get_victory_gif(game, winner)
            if gif_path and os.path.exists(gif_path):
                gif_file = discord.File(gif_path, filename=os.path.basename(gif_path))
                embed.set_image(url=f"attachment://{os.path.basename(gif_path)}")
        
        # Winner display
        winner_display = f"**{winner['name']}** {winner['title']} {winner_emoji}"
        embed.add_field(name="", value=winner_display, inline=False)
        
        # Reward
        reward_text = f"**Reward:** {prize:,} 💰"
        embed.add_field(name="", value=reward_text, inline=False)
        
        # Winner section header
        embed.add_field(name="**Winner**", value="", inline=False)
        
        # Total players
        embed.add_field(name="", value=f"**Total Players: {total_players}**", inline=False)
        
        # Send with or without GIF
        if gif_file:
            await channel.send(embed=embed, file=gif_file)
        else:
            await channel.send(embed=embed)
        
        # Rankings embed
        await self._send_rankings_embed_updated(game, channel)
        
    except Exception as e:
        logger.error(f"Error sending victory display with GIF: {e}")
        # Fallback to original method
        await self._send_victory_display(game, channel, winner_id, winner, prize)
