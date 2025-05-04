import discord
import random
import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union

from redbot.core import commands, Config
from redbot.core.bot import Red

class BountyBattle(commands.Cog):
    """One Piece themed RPG system with bounties, devil fruits, and deathmatches."""

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
        
        # File path for external data
        self.bounty_file = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/bounties.json"
        os.makedirs(os.path.dirname(self.bounty_file), exist_ok=True)
        
        # Initialize tracking variables
        self.active_channels = set()
        self.battle_stopped = False
        
        # Import necessary constants
        from .constants.devil_fruits import DEVIL_FRUITS
        from .constants.titles import TITLES, HIDDEN_TITLES
        from .constants.achievements import ACHIEVEMENTS
        from .constants.moves import MOVES
        from .constants.environments import ENVIRONMENTS
        
        self.constants = type('Constants', (), {
            'DEVIL_FRUITS': DEVIL_FRUITS,
            'TITLES': TITLES,
            'HIDDEN_TITLES': HIDDEN_TITLES,
            'ACHIEVEMENTS': ACHIEVEMENTS,
            'MOVES': MOVES,
            'ENVIRONMENTS': ENVIRONMENTS
        })
        
        # Initialize managers
        self._initialize_managers()
        
        # Initialize command handlers
        self._initialize_command_handlers()
        
        # Initialize boss rotation
        self._initialize_bosses()
    
    def _initialize_managers(self):
        """Initialize all the manager classes."""
        from .managers.battle_manager import BattleStateManager
        from .managers.status_manager import StatusEffectManager
        from .managers.environment_manager import EnvironmentManager
        from .managers.devil_fruit_manager import DevilFruitManager
        from .managers.data_manager import DataManager
        
        from .utils.image_utils import ImageUtils
        from .utils.message_utils import MessageUtils
        from .utils.data_utils import DataUtils
        
        # Initialize managers
        self.battle_manager = BattleStateManager()
        self.status_manager = StatusEffectManager()
        self.environment_manager = EnvironmentManager()
        self.data_manager = DataManager(self.config, self.logger)
        self.devil_fruit_manager = DevilFruitManager(self.status_manager, self.environment_manager)
        
        # Initialize utils
        self.image_utils = ImageUtils(self.logger)
        self.message_utils = MessageUtils()
        self.data_utils = DataUtils(self.config, self.logger)
    
    def _initialize_command_handlers(self):
        """Initialize all command handlers and attach them to the cog."""
        from .commands.bounty_commands import BountyCommands
        from .commands.battle_commands import BattleCommands
        from .commands.economy_commands import EconomyCommands
        from .commands.fruit_commands import FruitCommands
        from .commands.admin_commands import AdminCommands
        
        # Create command handler instances
        self.bounty_commands = BountyCommands(self)
        self.battle_commands = BattleCommands(self)
        self.economy_commands = EconomyCommands(self)
        self.fruit_commands = FruitCommands(self)
        self.admin_commands = AdminCommands(self)
        
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
    
    # --- Data Management Functions ---
    
    def load_bounties(self):
        """Load bounty data safely from file."""
        if not os.path.exists(self.bounty_file):
            return {}  # If file doesn't exist, return empty dict
        
        try:
            with open(self.bounty_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}  # If file is corrupted, return empty dict
    
    def save_bounties(self, data):
        """Save bounty data safely to file."""
        os.makedirs(os.path.dirname(self.bounty_file), exist_ok=True)
        with open(self.bounty_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    
    # --- BountyCommands ---
    
    @commands.command()
    async def startbounty(self, ctx):
        """Start your bounty journey."""
        await self.bounty_commands.startbounty(ctx)
    
    @commands.command()
    async def mybounty(self, ctx):
        """Check your bounty amount."""
        await self.bounty_commands.mybounty(ctx)
    
    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def dailybounty(self, ctx):
        """Claim your daily bounty increase."""
        await self.bounty_commands.dailybounty(ctx)
    
    @commands.command()
    async def mostwanted(self, ctx):
        """Display the top users with the highest bounties."""
        await self.bounty_commands.mostwanted(ctx)
    
    @commands.command()
    @commands.cooldown(1, 600, commands.BucketType.user)
    async def bountyhunt(self, ctx, target: discord.Member):
        """Attempt to steal a percentage of another user's bounty with a lock-picking minigame."""
        await self.bounty_commands.bountyhunt(ctx, target)
    
    # --- BattleCommands ---
    
    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def deathbattle(self, ctx, opponent: discord.Member = None):
        """Start a One Piece deathmatch against another user with a bounty."""
        await self.battle_commands.deathbattle(ctx, opponent)
    
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def stopbattle(self, ctx):
        """Stop an ongoing battle (Admin/Owner only)."""
        await self.battle_commands.stopbattle(ctx)
    
    # --- EconomyCommands ---
    
    @commands.command()
    async def bankstats(self, ctx):
        """View statistics about World Government bank fees and taxes."""
        await self.economy_commands.bankstats(ctx)
    
    @commands.group(name="bountybank", aliases=["bbank"], invoke_without_command=True)
    async def bountybank(self, ctx):
        """Check your bank balance and the global bank amount."""
        await self.economy_commands.bountybank(ctx)
    
    @bountybank.command(name="deposit")
    async def bank_deposit(self, ctx, amount):
        """Deposit bounty into your bank account (10% tax goes to World Government)."""
        await self.economy_commands.bank_deposit(ctx, amount)
    
    @bountybank.command(name="withdraw")
    async def bank_withdraw(self, ctx, amount):
        """Withdraw bounty from your bank account (subject to fees and interest collection)."""
        await self.economy_commands.bank_withdraw(ctx, amount)
    
    @commands.command()
    async def globalbank(self, ctx):
        """Check how many berries are stored in the World Government's vault."""
        await self.economy_commands.globalbank(ctx)
    
    @commands.command()
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def berryflip(self, ctx, bet: Optional[int] = None):
        """Flip a coin to potentially increase your bounty. Higher bets have lower win chances!"""
        await self.economy_commands.berryflip(ctx, bet)
    
    # --- FruitCommands ---
    
    @commands.command()
    async def eatfruit(self, ctx):
        """Consume a random Devil Fruit!"""
        # Placeholder until we add the implementation
        await ctx.send("This command is coming soon!")
    
    @commands.command()
    async def myfruit(self, ctx):
        """Check which Devil Fruit you have eaten."""
        # Placeholder until we add the implementation
        await ctx.send("This command is coming soon!")
    
    @commands.command()
    async def removefruit(self, ctx, member: discord.Member = None):
        """Remove a user's Devil Fruit. Owners and Admins remove for free, others pay 1,000,000 berries from their bounty."""
        await self.fruit_commands.removefruit(ctx, member)
    
    @commands.group(name="fruits", invoke_without_command=True)
    async def fruits(self, ctx):
        """Display Devil Fruit statistics and information."""
        await self.fruit_commands.fruits(ctx)
    
    @fruits.command(name="rare")
    async def fruits_rare(self, ctx):
        """Display all rare Devil Fruit users with detailed information."""
        await self.fruit_commands.fruits_rare(ctx)
    
    @fruits.command(name="common")
    async def fruits_common(self, ctx):
        """Display all common Devil Fruit users with detailed information."""
        await self.fruit_commands.fruits_common(ctx)
    
    # --- AdminCommands ---
    
    @commands.group(name="bbadmin")
    @commands.admin_or_permissions(administrator=True)
    async def bb_admin(self, ctx):
        """Admin controls for BountyBattle (Admin only)"""
        if ctx.invoked_subcommand is None:
            await self.admin_commands.bb_admin(ctx)
    
    @bb_admin.command(name="pause")
    async def pause_system(self, ctx, duration: str = None):
        """Temporarily pause all BountyBattle commands."""
        await self.admin_commands.pause_system(ctx, duration)
    
    @bb_admin.command(name="unpause")
    async def unpause_system(self, ctx):
        """Resume all BountyBattle commands."""
        await self.admin_commands.unpause_system(ctx)
    
    @bb_admin.command(name="restrict")
    async def restrict_channel(self, ctx, channel: discord.TextChannel = None):
        """Restrict BountyBattle commands to a specific channel."""
        await self.admin_commands.restrict_channel(ctx, channel)
    
    @bb_admin.command(name="unrestrict")
    async def unrestrict_channel(self, ctx):
        """Remove channel restriction for BountyBattle commands."""
        await self.admin_commands.unrestrict_channel(ctx)
    
    @bb_admin.command(name="disable")
    async def disable_commands(self, ctx, *commands):
        """Disable specific BountyBattle commands."""
        await self.admin_commands.disable_commands(ctx, *commands)
    
    @bb_admin.command(name="enable")
    async def enable_commands(self, ctx, *commands):
        """Re-enable specific BountyBattle commands."""
        await self.admin_commands.enable_commands(ctx, *commands)
    
    @bb_admin.command(name="maintenance")
    async def toggle_maintenance(self, ctx, duration: str = None):
        """Toggle maintenance mode for BountyBattle."""
        await self.admin_commands.toggle_maintenance(ctx, duration)
    
    @bb_admin.command(name="status")
    async def show_status(self, ctx):
        """Show current BountyBattle system status."""
        await self.admin_commands.show_status(ctx)
    
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def givefruit(self, ctx, member: discord.Member, *, fruit_name: str):
        """Give a user a Devil Fruit (Admin/Owner only)."""
        await self.admin_commands.givefruit(ctx, member, fruit_name=fruit_name)
    
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def fruitcleanup(self, ctx, days: int = 30):
        """Clean up Devil Fruits from inactive players and users who left the server (Admin/Owner only)."""
        await self.admin_commands.fruitcleanup(ctx, days)
    
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def resetstats(self, ctx, member: discord.Member = None):
        """Reset all users' stats (Admin/Owner only)."""
        await self.admin_commands.resetstats(ctx, member)
    
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def granttitle(self, ctx, member: discord.Member, *, title: str):
        """Grant a title to a user (Admin/Owner only)."""
        await self.admin_commands.granttitle(ctx, member, title=title)
    
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def betaover(self, ctx):
        """End the beta test (Admin/Owner only)."""
        await self.admin_commands.betaover(ctx)
        
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def setbounty(self, ctx, member: discord.Member, amount: int):
        """Set a user's bounty (Admin/Owner only)."""
        if amount < 0:
            return await ctx.send("❌ Bounty cannot be negative.")
        
        # Add permission check message
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
        
        try:
            # Set the bounty
            new_bounty = await self.data_manager.safe_modify_bounty(member, amount, "set")
            if new_bounty is None:
                return await ctx.send("⚠️ Failed to set bounty. Please try again.")

            # Create embed for response
            embed = discord.Embed(
                title="🏴‍☠️ Bounty Updated",
                description=f"**{member.display_name}**'s bounty has been set to `{amount:,}` Berries!",
                color=discord.Color.green()
            )

            # Add current title if applicable
            new_title = self.data_utils.get_bounty_title(amount)
            if new_title:
                embed.add_field(
                    name="Current Title",
                    value=f"`{new_title}`",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in setbounty command: {str(e)}")
            await ctx.send(f"❌ An error occurred while setting the bounty: {str(e)}")
