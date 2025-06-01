# __init__.py - CLEAN MAIN COG FILE
"""
Hunger Games Battle Royale Cog for Red-DiscordBot
Main cog file - delegates to other modules for functionality
"""

import discord
from redbot.core import commands, Config, data_manager
import asyncio
import logging
from typing import Dict

from .constants import DEFAULT_GUILD_CONFIG, DEFAULT_MEMBER_CONFIG
from .game_logic import GameEngine
from .commands import CommandHandler  # Import as CommandHandler to avoid conflict
from .poll_system import PollSystem
from .validators import InputValidator
from .event_handlers import EventHandler

# Set up logging
logger = logging.getLogger(__name__)

# Try to import systems
try:
    from .image_handler import ImageRoundHandler
    IMAGE_SYSTEM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Image system not available: {e}")
    IMAGE_SYSTEM_AVAILABLE = False

try:
    from .gif_manager import GifManager
    GIF_SYSTEM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"GIF system not available: {e}")
    GIF_SYSTEM_AVAILABLE = False


class HungerGames(commands.Cog):
    """A Hunger Games style battle royale game for Discord"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        
        self.config.register_guild(**DEFAULT_GUILD_CONFIG)
        self.config.register_member(**DEFAULT_MEMBER_CONFIG)
        
        # Core systems
        self.active_games: Dict[int, Dict] = {}
        self.game_engine = GameEngine(bot, self.config)
        self.validator = InputValidator()
        self.event_handler = EventHandler(self.game_engine)
        self.poll_system = PollSystem(self)
        self.command_handler = CommandHandler(self)
        
        # Optional systems
        self._setup_optional_systems()
    
    def _setup_optional_systems(self):
        """Set up optional image and GIF systems"""
        # Image system
        if IMAGE_SYSTEM_AVAILABLE:
            try:
                image_base_path = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/CogManager/cogs/hg/Images"
                self.image_handler = ImageRoundHandler(self.bot, image_base_path)
                logger.info("Image handler initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize image handler: {e}")
                self.image_handler = None
        else:
            self.image_handler = None
        
        # GIF system  
        if GIF_SYSTEM_AVAILABLE:
            try:
                cog_data_path = data_manager.cog_data_path(self)
                gif_base_path = cog_data_path / "gifs"
                self.gif_manager = GifManager(self.bot, self.config, str(gif_base_path))
                logger.info("GIF system initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GIF system: {e}")
                self.gif_manager = None
        else:
            self.gif_manager = None
    
    def cog_unload(self):
        """Cancel all running games when cog is unloaded"""
        for guild_id in list(self.active_games.keys()):
            if "task" in self.active_games[guild_id]:
                self.active_games[guild_id]["task"].cancel()
        logger.info("Hunger Games cog unloaded, all games cancelled")
    
    # Add the missing game_loop method
    async def game_loop(self, guild_id: int):
        """Main game loop that runs the Hunger Games"""
        try:
            game = self.active_games[guild_id]
            channel = game["channel"]
            
            # Get config
            event_interval = await self.config.guild_from_id(guild_id).event_interval()
            
            while guild_id in self.active_games:
                game = self.active_games[guild_id]
                
                if game["status"] != "active":
                    break
                
                # Get alive players
                alive_players = self.game_engine.get_alive_players(game)
                
                # Check for game end
                if await self.game_engine.check_game_end(game, channel):
                    break
                
                # Increment round
                game["round"] += 1
                
                # Execute events for this round
                try:
                    event_messages = await self.game_engine.execute_combined_events(game, channel)
                    
                    # Send event messages
                    for message in event_messages:
                        if message:
                            embed = discord.Embed(description=message, color=0xFF6B35)
                            await channel.send(embed=embed)
                            await asyncio.sleep(1)
                    
                    # Check for special events
                    special_message = await self.game_engine.check_special_events(game, channel, alive_players)
                    if special_message:
                        embed = discord.Embed(description=special_message, color=0x4169E1)
                        await channel.send(embed=embed)
                    
                    # Send status update occasionally
                    if game["round"] % 6 == 0 and len(alive_players) > 8:
                        status_embed = self.game_engine.create_status_embed(game, channel.guild)
                        await channel.send(embed=status_embed)
                    
                except Exception as e:
                    logger.error(f"Error in game loop round {game['round']}: {e}")
                    await channel.send("⚠️ The arena experienced technical difficulties, but the games continue...")
                
                # Calculate sleep time based on player count
                alive_count = len(self.game_engine.get_alive_players(game))
                if alive_count <= 2:
                    sleep_time = max(8, event_interval // 3)
                elif alive_count <= 5:
                    sleep_time = max(12, event_interval // 2)
                else:
                    sleep_time = max(25, event_interval)
                
                await asyncio.sleep(sleep_time)
            
            # Clean up
            if guild_id in self.active_games:
                del self.active_games[guild_id]
                
        except Exception as e:
            logger.error(f"Fatal error in game loop for guild {guild_id}: {e}")
            if guild_id in self.active_games:
                del self.active_games[guild_id]
            await channel.send("❌ The arena has malfunctioned. Game ended.")
    
    # Add missing _send_game_start_messages method
    async def _send_game_start_messages(self, game, player_count):
        """Send game start and player introduction messages"""
        channel = game["channel"]
        
        # Game start message
        from .utils import create_game_start_embed
        embed = create_game_start_embed(player_count)
        await channel.send(embed=embed)
        
        await asyncio.sleep(3)
        
        # Show initial tributes
        embed = discord.Embed(
            title="👥 **THE TRIBUTES**",
            description="Meet this year's brave competitors:",
            color=0x4169E1
        )
        
        from .utils import format_player_list
        player_list = format_player_list(game["players"], show_status=False)
        embed.add_field(
            name="🏹 **Entered the Arena**",
            value=player_list,
            inline=False
        )
        
        await channel.send(embed=embed)
        
        # Add extra dramatic pause for small games
        if player_count <= 4:
            await asyncio.sleep(2)
            embed = discord.Embed(
                title="⚡ **INTENSE SHOWDOWN INCOMING** ⚡",
                description=f"With only **{player_count} tributes**, this will be a lightning-fast battle!\n"
                           f"Every second counts... every move matters...",
                color=0xFF6B35
            )
            await channel.send(embed=embed)
    
    # =====================================================
    # DELEGATE COMMANDS TO COMMAND HANDLER
    # =====================================================
    
    # Main commands
    @commands.command(name="he")
    async def hunger_games_event(self, ctx, countdown: int = 60):
        """Start a Hunger Games battle royale! React to join!"""
        await self.command_handler.handle_hunger_games_event(ctx, countdown)
    
    @commands.command(name="hg")
    async def hg_command(self, ctx, *, args=None):
        """Hunger Games poll command"""
        await self.command_handler.handle_hg_command(ctx, args)
    
    @commands.command(name="poll")
    async def poll_command(self, ctx, threshold: int = None):
        """Create a poll for starting a Hunger Games"""
        await self.command_handler.handle_poll_command(ctx, threshold)
    
    # Main command group
    @commands.group(invoke_without_command=True)
    async def hungergames(self, ctx):
        """Hunger Games battle royale commands"""
        await self.command_handler.handle_hungergames_help(ctx)
    
    # Subcommands - delegate to handler
    @hungergames.command(name="alive")
    async def hg_alive(self, ctx):
        """Show current alive players in the active game"""
        await self.command_handler.handle_alive(ctx)
    
    @hungergames.command(name="stats")
    async def hg_stats(self, ctx, member: discord.Member = None):
        """View Hunger Games statistics for yourself or another player"""
        await self.command_handler.handle_stats(ctx, member)
    
    @hungergames.command(name="stop")
    @commands.has_permissions(manage_guild=True)
    async def hg_stop(self, ctx):
        """Stop the current Hunger Games"""
        await self.command_handler.handle_stop(ctx)
    
    @hungergames.command(name="status")
    async def hg_status(self, ctx):
        """Check the status of current Hunger Games"""
        await self.command_handler.handle_status(ctx)
    
    @hungergames.command(name="test")
    @commands.has_permissions(manage_guild=True)
    async def hg_test(self, ctx):
        """Test game events (Admin only)"""
        await self.command_handler.handle_test(ctx)
    
    @hungergames.command(name="debug")
    @commands.has_permissions(manage_guild=True)
    async def hg_debug(self, ctx):
        """Debug current game state (Admin only)"""
        await self.command_handler.handle_debug(ctx)
    
    @hungergames.command(name="config")
    @commands.has_permissions(manage_guild=True)
    async def hg_config(self, ctx):
        """View current Hunger Games configuration"""
        await self.command_handler.handle_config(ctx)
    
    @hungergames.command(name="leaderboard", aliases=["lb", "top"])
    async def hg_leaderboard(self, ctx, stat: str = "wins"):
        """View the Hunger Games leaderboard"""
        await self.command_handler.handle_leaderboard(ctx, stat)
    
    # Settings group
    @hungergames.group(name="set", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def hg_set(self, ctx):
        """Configure Hunger Games settings"""
        await ctx.send_help()
    
    @hg_set.command(name="pollthreshold")
    async def hg_set_poll_threshold(self, ctx, threshold: int = None):
        """Set the minimum players needed for a poll to start a game"""
        await self.command_handler.handle_set_poll_threshold(ctx, threshold)
    
    @hg_set.command(name="pollpingrole")
    async def hg_set_poll_ping_role(self, ctx, role: discord.Role = None):
        """Set the role to ping when polls start"""
        await self.command_handler.handle_set_poll_ping_role(ctx, role)
    
    @hg_set.command(name="blacklistrole")
    async def hg_set_blacklist_role(self, ctx, role: discord.Role, action: str = "add"):
        """Add or remove a role from the blacklist"""
        await self.command_handler.handle_set_blacklist_role(ctx, role, action)
    
    @hg_set.command(name="tempban")
    async def hg_set_temp_ban(self, ctx, member: discord.Member, duration: str = None):
        """Temporarily ban a member from Hunger Games"""
        await self.command_handler.handle_set_temp_ban(ctx, member, duration)
    
    @hg_set.command(name="reward")
    async def hg_set_reward(self, ctx, amount: int):
        """Set the base reward amount"""
        await self.command_handler.handle_set_reward(ctx, amount)
    
    @hg_set.command(name="sponsor")
    async def hg_set_sponsor(self, ctx, chance: int):
        """Set the sponsor revival chance (1-50%)"""
        await self.command_handler.handle_set_sponsor(ctx, chance)
    
    @hg_set.command(name="interval")
    async def hg_set_interval(self, ctx, seconds: int):
        """Set the event interval (10-120 seconds)"""
        await self.command_handler.handle_set_interval(ctx, seconds)


async def setup(bot):
    """Required function for loading the cog"""
    await bot.add_cog(HungerGames(bot))
