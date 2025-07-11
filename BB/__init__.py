"""
DeathBattle Cog - A battle system with Berris currency
"""
import discord
from redbot.core import commands, Config
from redbot.core.bot import Red

# Import with absolute path handling
import sys
import os

# Get the directory of this __init__.py file
cog_dir = os.path.dirname(os.path.abspath(__file__))

# Temporarily add to path for imports
if cog_dir not in sys.path:
    sys.path.insert(0, cog_dir)

try:
    from .bank import BankCommands
    from .deathbattle import BattleCommands
    from .utils import setup_logger
    from .constants import (
        REMOVE_FRUIT_COST, BUY_FRUIT_COST, BUY_RARE_FRUIT_COST,
        FRUIT_REMOVE_COOLDOWN, FRUIT_BUY_COOLDOWN
    )
except ImportError:
    # Fallback imports
    from bank import BankCommands
    from deathbattle import BattleCommands
    from utils import setup_logger
    from constants import (
        REMOVE_FRUIT_COST, BUY_FRUIT_COST, BUY_RARE_FRUIT_COST,
        FRUIT_REMOVE_COOLDOWN, FRUIT_BUY_COOLDOWN
    )
finally:
    # Clean up path
    if cog_dir in sys.path:
        sys.path.remove(cog_dir)

class DeathBattle(BankCommands, BattleCommands):
    """
    A cog featuring DeathBattles and a Berris economy system.
    
    Players can battle each other in 1v1 fights to earn Berris,
    store them in a bank, and even rob other players!
    """
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.log = setup_logger("main")
        
        # Set up configuration
        self.config = Config.get_conf(
            self, 
            identifier=1234567890, 
            force_registration=True
        )
        
        # Default settings - UPDATED with fruit management tracking
        default_member = {
            "total_berris": 0,
            "bank_balance": 0,
            "security_level": "basic",
            "wins": 0,
            "losses": 0,
            "last_battle": None,
            "last_robbery": None,
            "devil_fruit": None,
            "has_started": False,
            "fruit_acquired_date": None,
            "last_fruit_remove": None,   # Track when they last removed a fruit
            "last_fruit_buy": None,      # Track when they last bought a fruit
            "fruits_removed_count": 0    # Track total fruits removed
        }
        
        default_guild = {
            "battle_channel": None,
            "allow_robberies": True,
            "announce_battles": True,
            "rare_fruits_given": {},  # Track rare fruits given out {user_id: fruit_name}
            "rare_fruit_limit": 3     # Max number of each rare fruit that can exist
        }
        
        self.config.register_member(**default_member)
        self.config.register_guild(**default_guild)
        
        # Initialize parent classes
        BankCommands.__init__(self, bot, self.config)
        BattleCommands.__init__(self, bot, self.config)
        
        self.log.info("DeathBattle cog initialized successfully")
    
    @commands.group(name="dbconfig", invoke_without_command=True)
    @commands.admin_or_permissions(manage_guild=True)
    async def deathbattle_config(self, ctx):
        """Configure DeathBattle settings for this server."""
        battle_channel_id = await self.config.guild(ctx.guild).battle_channel()
        allow_robberies = await self.config.guild(ctx.guild).allow_robberies()
        announce_battles = await self.config.guild(ctx.guild).announce_battles()
        rare_fruit_limit = await self.config.guild(ctx.guild).rare_fruit_limit()
        
        battle_channel = None
        if battle_channel_id:
            battle_channel = self.bot.get_channel(battle_channel_id)
        
        embed = discord.Embed(
            title="⚔️ DeathBattle Configuration",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🏟️ Battle Channel",
            value=battle_channel.mention if battle_channel else "Not set",
            inline=False
        )
        
        embed.add_field(
            name="💰 Allow Robberies",
            value="✅ Enabled" if allow_robberies else "❌ Disabled",
            inline=True
        )
        
        embed.add_field(
            name="📢 Announce Battles",
            value="✅ Enabled" if announce_battles else "❌ Disabled",
            inline=True
        )
        
        embed.add_field(
            name="🍎 Rare Fruit Limit",
            value=f"{rare_fruit_limit} per fruit type",
            inline=True
        )
        
        # Add fruit management costs
        embed.add_field(
            name="💸 Fruit Management Costs",
            value=f"Remove: {REMOVE_FRUIT_COST:,} Berris\nBuy New: {BUY_FRUIT_COST:,} Berris\nBuy Rare: {BUY_RARE_FRUIT_COST:,} Berris",
            inline=True
        )
        
        # Add cooldown info
        embed.add_field(
            name="⏰ Cooldowns",
            value=f"Remove Fruit: {FRUIT_REMOVE_COOLDOWN // 3600} hours\nBuy Fruit: {FRUIT_BUY_COOLDOWN // 60} minutes",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @deathbattle_config.command(name="channel")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_battle_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the designated battle channel."""
        if channel is None:
            await self.config.guild(ctx.guild).battle_channel.set(None)
            await ctx.send("✅ Battle channel restriction removed.")
        else:
            await self.config.guild(ctx.guild).battle_channel.set(channel.id)
            await ctx.send(f"✅ Battle channel set to {channel.mention}")
    
    @deathbattle_config.command(name="robberies")
    @commands.admin_or_permissions(manage_guild=True)
    async def toggle_robberies(self, ctx, enabled: bool = None):
        """Enable or disable bank robberies."""
        if enabled is None:
            current = await self.config.guild(ctx.guild).allow_robberies()
            enabled = not current
        
        await self.config.guild(ctx.guild).allow_robberies.set(enabled)
        status = "enabled" if enabled else "disabled"
        await ctx.send(f"✅ Bank robberies have been {status}.")
    
    @deathbattle_config.command(name="rarelimit")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_rare_limit(self, ctx, limit: int):
        """Set the limit for rare devil fruits per type."""
        if limit < 1:
            await ctx.send("❌ Limit must be at least 1.")
            return
        
        await self.config.guild(ctx.guild).rare_fruit_limit.set(limit)
        await ctx.send(f"✅ Rare fruit limit set to {limit} per fruit type.")
    
    @commands.command(name="berris")
    async def check_berris(self, ctx, user: discord.Member = None):
        """Check your or someone else's Berris."""
        if user is None:
            user = ctx.author
        
        total_berris = await self.config.member(user).total_berris()
        bank_balance = await self.config.member(user).bank_balance()
        
        embed = discord.Embed(
            title=f"💰 {user.display_name}'s Berris",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💵 Wallet",
            value=f"{total_berris:,} Berris",
            inline=True
        )
        
        embed.add_field(
            name="🏦 Bank",
            value=f"{bank_balance:,} Berris",
            inline=True
        )
        
        embed.add_field(
            name="💎 Total Worth",
            value=f"{total_berris + bank_balance:,} Berris",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def cog_check(self, ctx):
        """Check if battles are restricted to a specific channel."""
        if ctx.command.qualified_name.startswith(('db', 'deathbattle', 'battle')):
            battle_channel_id = await self.config.guild(ctx.guild).battle_channel()
            if battle_channel_id and ctx.channel.id != battle_channel_id:
                battle_channel = self.bot.get_channel(battle_channel_id)
                if battle_channel:
                    await ctx.send(f"❌ Battles can only be started in {battle_channel.mention}!")
                    return False
        
        # Check if robberies are disabled
        if ctx.command.qualified_name == 'rob':
            allow_robberies = await self.config.guild(ctx.guild).allow_robberies()
            if not allow_robberies:
                await ctx.send("❌ Bank robberies are disabled in this server!")
                return False
        
        return True

async def setup(bot: Red):
    """Set up the cog."""
    cog = DeathBattle(bot)
    await bot.add_cog(cog)
