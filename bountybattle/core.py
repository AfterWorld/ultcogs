import discord
import logging
import asyncio
from typing import Optional, Dict, List, Any, Union
from datetime import datetime, timedelta

from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box, humanize_list

from .managers.battle_manager import BattleStateManager
from .managers.status_manager import StatusEffectManager
from .managers.environment_manager import EnvironmentManager
from .managers.devil_fruit_manager import DevilFruitManager
from .managers.data_manager import DataManager

from .commands.bounty_commands import BountyCommands
from .commands.battle_commands import BattleCommands
from .commands.economy_commands import EconomyCommands
from .commands.fruit_commands import FruitCommands
from .commands.admin_commands import AdminCommands

from .utils.image_utils import ImageUtils
from .utils.message_utils import MessageUtils
from .utils.data_utils import DataUtils

class BountyBattle(commands.Cog):
    """
    One Piece themed RPG system with bounties, devil fruits, and deathmatches.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.logger = logging.getLogger("red.BountyBattle")
        
        # Initialize Config
        self.config = Config.get_conf(self, identifier=1357924680, force_registration=True)
        
        # Register default guild settings
        default_guild = {
            "bounties": {},
            "event": None,
            "global_bank": 0,
            "last_bank_robbery": None,
            "tournaments": {},
            "beta_active": True,
            "leaderboard_channel": None,
            "announcement_channel": None,
            "active_events": {},
            "disabled_commands": [],
            "is_paused": False,
            "restricted_channel": None,
            "maintenance_mode": False
        }
        
        # Register default member settings
        default_member = {
            "bounty": 0,
            "bank_balance": 0,
            "berries": 0,
            "last_daily_claim": None,
            "wins": 0,
            "losses": 0,
            "damage_dealt": 0,
            "achievements": [],
            "titles": [],
            "current_title": None,
            "devil_fruit": None,
            "last_active": None,
            "bounty_hunted": 0,
            "last_deposit_time": None,
            "win_streak": 0,
            "damage_taken": 0,
            "critical_hits": 0,
            "healing_done": 0,
            "turns_survived": 0,
            "burns_applied": 0,
            "stuns_applied": 0,
            "blocks_performed": 0,
            "damage_prevented": 0,
            "elements_used": [],
            "total_battles": 0,
            "perfect_victories": 0,
            "comebacks": 0,
            "fastest_victory": None,
            "longest_battle": None,
            "devil_fruit_mastery": 0,
            "successful_hunts": 0,
            "failed_hunts": 0
        }
        
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        
        # Initialize managers
        self.data_manager = DataManager(self.config, self.logger)
        self.battle_manager = BattleStateManager()
        self.status_manager = StatusEffectManager()
        self.environment_manager = EnvironmentManager()
        self.devil_fruit_manager = DevilFruitManager(self.status_manager, self.environment_manager)
        
        # Initialize utilities
        self.image_utils = ImageUtils(self.logger)
        self.message_utils = MessageUtils()
        self.data_utils = DataUtils(self.config, self.logger)
        
        # Initialize command handlers
        self.bounty_commands = BountyCommands(self)
        self.battle_commands = BattleCommands(self)
        self.economy_commands = EconomyCommands(self)
        self.fruit_commands = FruitCommands(self)
        self.admin_commands = AdminCommands(self)
        
        # Initialize tracking variables
        self.active_channels = set()
        self.battle_stopped = False
        self.current_environment = None
        
        # Initialize boss rotation
        self._initialize_bosses()
        
    def _initialize_bosses(self):
        """Initialize the boss rotation system."""
        now = datetime.utcnow()
        self.current_bosses = {
            "Marine Fortress": {
                "boss": "Vice Admiral Momonga",  # Will be randomized later
                "level": "Easy",
                "next_rotation": now + timedelta(hours=4)
            },
            "Impel Down": {
                "boss": "Magellan",  # Will be randomized later
                "level": "Medium",
                "next_rotation": now + timedelta(hours=6)
            },
            "Enies Lobby": {
                "boss": "Rob Lucci",  # Will be randomized later
                "level": "Hard",
                "next_rotation": now + timedelta(hours=8)
            },
            "Yonko Territory": {
                "boss": "Kaido",  # Will be randomized later
                "level": "Very Hard",
                "next_rotation": now + timedelta(hours=12)
            },
            "Mary Geoise": {
                "boss": "The Five Elders",  # Will be randomized later
                "level": "Extreme",
                "next_rotation": now + timedelta(hours=24)
            }
        }
        
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle messages for automated features."""
        if message.author.bot:
            return
            
        # Implement any automated message processing here
        
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.CommandOnCooldown):
            # Format the cooldown message nicely
            minutes, seconds = divmod(int(error.retry_after), 60)
            if minutes > 0:
                time_fmt = f"{minutes}m {seconds}s"
            else:
                time_fmt = f"{seconds}s"
            
            # Mark as handled to prevent default error handler
            error.handled = True
            await ctx.send(f"⏳ Command on cooldown. Try again in {time_fmt}.")
            
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Handle Devil Fruit cleanup when a member leaves the server."""
        try:
            # Get the member's devil fruit
            fruit = await self.config.member(member).devil_fruit()
            if not fruit:
                return
                
            # Check if it's a rare fruit
            is_rare = await self.fruit_commands.is_fruit_rare(fruit)
            
            # Remove the fruit from the user
            await self.config.member(member).devil_fruit.set(None)
            
            # Announce if it was a rare fruit
            if is_rare:
                for guild in self.bot.guilds:
                    channel = discord.utils.get(guild.text_channels, name="bot-commands")
                    if channel:
                        embed = discord.Embed(
                            title="🌟 Rare Devil Fruit Available!",
                            description=(
                                f"The `{fruit}` has returned to circulation!\n"
                                f"Previous owner left the server."
                            ),
                            color=discord.Color.gold()
                        )
                        await channel.send(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Error handling member remove: {e}")
            
    async def cog_before_invoke(self, ctx: commands.Context):
        """Check if the cog is available before running any command."""
        if not ctx.guild:
            return True  # Allow DMs
            
        if await self.bot.is_owner(ctx.author):
            return True  # Always allow for owner
            
        if ctx.author.guild_permissions.administrator:
            return True  # Always allow for admins
            
        # Check for maintenance mode
        if await self.config.guild(ctx.guild).maintenance_mode():
            await ctx.send("🛠️ BountyBattle is currently in maintenance mode!")
            return False
            
        # Check if system is paused
        if await self.config.guild(ctx.guild).is_paused():
            await ctx.send("⏸️ BountyBattle is currently paused!")
            return False
            
        # Check if command is disabled
        disabled_commands = await self.config.guild(ctx.guild).disabled_commands()
        if ctx.command.name in disabled_commands:
            await ctx.send(f"❌ The command `{ctx.command.name}` is currently disabled!")
            return False
            
        # Check channel restriction
        restricted_channel = await self.config.guild(ctx.guild).restricted_channel()
        if restricted_channel and ctx.channel.id != restricted_channel:
            channel = ctx.guild.get_channel(restricted_channel)
            if channel:
                await ctx.send(f"📍 BountyBattle commands can only be used in {channel.mention}!")
                return False
                
        return True