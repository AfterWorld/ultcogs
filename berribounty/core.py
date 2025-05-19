# berribounty/core.py
"""Core functionality and main cog class for One Piece bot."""

import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n

from .constants.settings import setup_config  # Fix this import
from .managers.player_manager import PlayerManager
from .managers.battle_manager import BattleManager
from .managers.fruit_manager import FruitManager
from .managers.achievement_manager import AchievementManager
from .commands.battle_commands import BattleCommands
from .commands.berri_commands import BerriCommands
from .commands.fruit_commands import FruitCommands
from .commands.admin_commands import AdminCommands

_ = Translator("OnePiece", __file__)

@cog_i18n(_)
class OnePiece(commands.Cog):
    """One Piece themed discord bot with battles, devil fruits, and berries!"""
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = setup_config(self)
        
        # Initialize managers
        self.player_manager = PlayerManager(self.config)
        self.fruit_manager = FruitManager(self.config, self.player_manager)
        self.battle_manager = BattleManager(self.config, self.player_manager)
        self.achievement_manager = AchievementManager(self.config, self.player_manager)
        
        # Initialize command groups
        self.battle_commands = BattleCommands(self.bot, self.battle_manager, self.player_manager)
        self.berri_commands = BerriCommands(self.bot, self.player_manager)
        self.fruit_commands = FruitCommands(self.bot, self.fruit_manager, self.player_manager)
        self.admin_commands = AdminCommands(self.bot, self.config, self.player_manager)
    
    async def cog_load(self):
        """Called when the cog is loaded."""
        await self._startup_tasks()
    
    async def cog_unload(self):
        """Called when the cog is unloaded."""
        await self._cleanup_tasks()
    
    async def _startup_tasks(self):
        """Perform startup tasks."""
        # Initialize player data for existing members
        for guild in self.bot.guilds:
            for member in guild.members:
                if not member.bot:
                    await self.player_manager.get_or_create_player(member)
    
    async def _cleanup_tasks(self):
        """Perform cleanup tasks."""
        # Cancel any ongoing battles
        await self.battle_manager.cleanup_all_battles()
    
    # Battle Commands
    @commands.group(name="battle", aliases=["fight"])
    @commands.guild_only()
    async def battle(self, ctx):
        """Battle system commands."""
        pass
    
    @battle.command(name="challenge")
    async def battle_challenge(self, ctx, opponent: discord.Member):
        """Challenge another player to battle."""
        await self.battle_commands.challenge(ctx, opponent)
    
    @battle.command(name="status")
    async def battle_status(self, ctx):
        """Check your current battle status."""
        await self.battle_commands.status(ctx)
    
    @battle.command(name="stats")
    async def battle_stats(self, ctx, member: discord.Member = None):
        """View battle statistics."""
        await self.battle_commands.stats(ctx, member)
    
    # Berri Commands
    @commands.group(name="berri", aliases=["berries", "money"])
    @commands.guild_only()
    async def berri(self, ctx):
        """Berri (currency) management commands."""
        pass
    
    @berri.command(name="balance", aliases=["bal"])
    async def berri_balance(self, ctx, member: discord.Member = None):
        """Check berri balance."""
        await self.berri_commands.balance(ctx, member)
    
    @berri.command(name="give")
    async def berri_give(self, ctx, amount: int, recipient: discord.Member):
        """Give berries to another player."""
        await self.berri_commands.give(ctx, amount, recipient)
    
    @berri.command(name="daily")
    async def berri_daily(self, ctx):
        """Claim your daily berries."""
        await self.berri_commands.daily(ctx)
    
    @berri.command(name="gamble")
    async def berri_gamble(self, ctx, amount: int):
        """Gamble your berries."""
        await self.berri_commands.gamble(ctx, amount)
    
    @berri.command(name="work")
    async def berri_work(self, ctx):
        """Work to earn berries."""
        await self.berri_commands.work(ctx)
    
    # Devil Fruit Commands
    @commands.group(name="fruit", aliases=["devil", "devilfruit"])
    @commands.guild_only()
    async def fruit(self, ctx):
        """Devil fruit commands."""
        pass
    
    @fruit.command(name="search")
    async def fruit_search(self, ctx):
        """Search for devil fruits."""
        await self.fruit_commands.search(ctx)
    
    @fruit.command(name="list")
    async def fruit_list(self, ctx):
        """List available devil fruits."""
        await self.fruit_commands.list_fruits(ctx)
    
    @fruit.command(name="info")
    async def fruit_info(self, ctx, *, fruit_name: str = None):
        """Get information about a devil fruit."""
        await self.fruit_commands.info(ctx, fruit_name)
    
    # Admin Commands
    @commands.group(name="opset", aliases=["onepieceset"])
    @commands.admin_or_permissions(administrator=True)
    @commands.guild_only()
    async def opset(self, ctx):
        """One Piece bot admin settings."""
        pass
    
    @opset.command(name="channel")
    async def opset_channel(self, ctx, channel_type: str, channel: discord.TextChannel = None):
        """Set channels for battle announcements."""
        await self.admin_commands.set_channel(ctx, channel_type, channel)
    
    @opset.command(name="maintenance")
    async def opset_maintenance(self, ctx, enabled: bool = None):
        """Toggle maintenance mode."""
        await self.admin_commands.maintenance(ctx, enabled)
    
    @opset.command(name="give")
    async def opset_give(self, ctx, member: discord.Member, item_type: str, amount: int):
        """Give items to a player (admin only)."""
        await self.admin_commands.give_item(ctx, member, item_type, amount)
    
    # Profile Command
    @commands.command(name="profile", aliases=["op"])
    @commands.guild_only()
    async def profile(self, ctx, member: discord.Member = None):
        """View your One Piece profile."""
        if member is None:
            member = ctx.author
        
        player = await self.player_manager.get_or_create_player(member)
        
        embed = discord.Embed(
            title=f"🏴‍☠️ {member.display_name}'s Profile",
            color=discord.Color.gold()
        )
        
        # Basic info
        embed.add_field(
            name="💰 Berries",
            value=f"{player.berries:,}",
            inline=True
        )
        
        # Devil fruit info
        fruit_text = player.devil_fruit if player.devil_fruit else "None"
        embed.add_field(
            name="🍎 Devil Fruit",
            value=fruit_text,
            inline=True
        )
        
        # Battle stats
        total_battles = player.wins + player.losses
        win_rate = (player.wins / total_battles * 100) if total_battles > 0 else 0
        embed.add_field(
            name="⚔️ Battle Record",
            value=f"{player.wins}W / {player.losses}L ({win_rate:.1f}%)",
            inline=True
        )
        
        # Additional stats
        embed.add_field(
            name="📊 Statistics",
            value=(
                f"Damage Dealt: {player.total_damage_dealt:,}\n"
                f"Damage Taken: {player.total_damage_taken:,}\n"
                f"Battles Fought: {player.stats.get('battles_fought', 0)}"
            ),
            inline=False
        )
        
        # Achievements
        achievement_count = len(player.achievements)
        embed.add_field(
            name="🏆 Achievements",
            value=f"{achievement_count} unlocked",
            inline=True
        )
        
        # Current title
        current_title = player.current_title or "Rookie Pirate"
        embed.add_field(
            name="🎭 Title",
            value=current_title,
            inline=True
        )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await ctx.send(embed=embed)
    
    # Event listeners
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Initialize player data when member joins."""
        if not member.bot:
            await self.player_manager.get_or_create_player(member)
    
    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        """Update player activity when commands are used."""
        if ctx.guild and not ctx.author.bot:
            player = await self.player_manager.get_or_create_player(ctx.author)
            await self.player_manager.update_last_active(player)
    
    async def red_delete_data_for_user(self, *, requester: str, user_id: int):
        """Handle user data deletion requests."""
        all_guilds = await self.config.all_guilds()
        
        for guild_id, guild_data in all_guilds.items():
            if str(user_id) in guild_data.get("players", {}):
                async with self.config.guild_from_id(guild_id).players() as players:
                    if str(user_id) in players:
                        del players[str(user_id)]
