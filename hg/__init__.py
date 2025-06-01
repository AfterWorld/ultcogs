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
from .commands import CommandHandler
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