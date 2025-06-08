"""
crewbattles/crew.py - WITH BASIC COMMANDS FOR TESTING
Main crew management cog with all enhanced functionality
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Union, Any
import asyncio
import datetime
import hashlib

import aiohttp
import discord
from discord.ext import tasks
from redbot.core import commands, Config
from redbot.core.data_manager import cog_data_path

# Import our enhanced components
from .constants import CrewRole, CrewSettings, EMBED_COLORS, CREW_COLORS
from .exceptions import *
from .models import CrewData, CrewStats, CrewMember, InviteData
from .logger import EnhancedCrewLogger
from .utils import NicknameManager, EmbedBuilder, ValidationUtils, PermissionUtils
from .data_manager import DataManager
from .ui import CrewManagementView, CrewInviteView, CrewButton, CrewView

# Import tournament system
try:
    from .tournament import TournamentSystem
except ImportError:
    TournamentSystem = None


class CrewManagement(commands.Cog):
    """Enhanced crew management system with comprehensive features and improved architecture"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        
        # Initialize enhanced components
        self.data_path = cog_data_path(self)
        self.enhanced_logger = EnhancedCrewLogger("CrewManagement", self.data_path)
        self.data_manager = DataManager(self.data_path, self.enhanced_logger)
        self.nickname_manager = NicknameManager(self.enhanced_logger)
        
        # State management
        self.active_crew_messages: Dict[int, Dict] = {}
        self.active_invites: Dict[int, InviteData] = {}
        self.guild_locks: Dict[str, asyncio.Lock] = {}
        self.crews: Dict[str, Dict[str, Any]] = {}  # Preserved for compatibility
        
        # Configuration
        default_guild = {
            "finished_setup": False,
            "separator_roles": None,
            "enhanced_features_enabled": True
        }
        self.config.register_guild(**default_guild)
        
        # Log initialization
        self.enhanced_logger.log_system_event("cog_initialized", version="2.0.0")
        
        # Start background tasks
        self.bot.loop.create_task(self.initialize())
        self.cleanup_expired_invitations.start()

    # --- Test Commands ---
    @commands.command(name="crewtest")
    async def test_command(self, ctx):
        """Test command to verify the cog is working"""
        await ctx.send("✅ CrewBattles cog is loaded and working!")

    @commands.group(name="crew")
    @commands.guild_only()
    async def crew_commands(self, ctx):
        """Commands for managing crews"""
        if ctx.invoked_subcommand is None:
            embed = EmbedBuilder.create_info_embed(
                "Crew Commands",
                "Available crew management commands"
            )
            embed.add_field(
                name="Basic Commands",
                value=(
                    "`crew test` - Test crew functionality\n"
                    "`crew list` - List all crews\n"
                    "`crew create <name>` - Create a new crew (Admin)\n"
                    "`crew join <name>` - Join a crew"
                ),
                inline=False
            )
            await ctx.send(embed=embed)

    @crew_commands.command(name="test")
    async def crew_test(self, ctx):
        """Test crew functionality"""
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        embed = EmbedBuilder.create_success_embed(
            "Crew System Test",
            f"Guild ID: {guild_id}\nCrews loaded: {len(crews)}"
        )
        await ctx.send(embed=embed)

    @crew_commands.command(name="list")
    async def crew_list(self, ctx):
        """List all available crews"""
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if not crews:
            embed = EmbedBuilder.create_warning_embed(
                "No Crews Found",
                "No crews have been created yet. Use `crew create` to create one!"
            )
            await ctx.send(embed=embed)
            return
        
        embed = EmbedBuilder.create_info_embed(
            "Available Crews",
            f"Found {len(crews)} crews in this server"
        )
        
        for crew_name, crew_data in crews.items():
            emoji = crew_data.get('emoji', '🏴‍☠️')
            members = len(crew_data.get('members', []))
            embed.add_field(
                name=f"{emoji} {crew_name}",
                value=f"Members: {members}",
                inline=True
            )
        
        await ctx.send(embed=embed)

    # --- Core Utility Methods ---
    def get_guild_lock(self, guild_id: str) -> asyncio.Lock:
        """Get or create a thread-safe lock for a specific guild"""
        if guild_id not in self.guild_locks:
            self.guild_locks[guild_id] = asyncio.Lock()
        return self.guild_locks[guild_id]

    async def initialize(self):
        """Enhanced initialization with comprehensive error handling"""
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            try:
                await self.load_data(guild)
                self.enhanced_logger.info(f"Initialized crew data for guild: {guild.name}")
            except Exception as e:
                self.enhanced_logger.log_error_with_context(
                    e, f"Failed to initialize guild {guild.name}", guild.id
                )

    async def save_data(self, guild: discord.Guild) -> bool:
        """Enhanced save_data with comprehensive error handling"""
        finished_setup = await self.config.guild(guild).finished_setup()
        if not finished_setup:
            return True
        
        try:
            guild_id = str(guild.id)
            crews_data = self.crews.get(guild_id, {})
            
            success = await self.data_manager.save_crew_data(guild, crews_data)
            if not success:
                self.enhanced_logger.error(f"Failed to save data for guild {guild.name}")
            
            return success
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "save_data", guild.id
            )
            return False

    async def load_data(self, guild: discord.Guild) -> bool:
        """Enhanced load_data with migration support"""
        if not guild:
            return False
    
        finished_setup = await self.config.guild(guild).finished_setup()
        if not finished_setup:
            return True
    
        try:
            guild_id = str(guild.id)
            crews_data = await self.data_manager.load_crew_data(guild)
            
            # Initialize guild namespace
            if guild_id not in self.crews:
                self.crews[guild_id] = {}
            
            # Load data into memory
            self.crews[guild_id] = crews_data
            
            self.enhanced_logger.info(f"Loaded {len(crews_data)} crews for guild {guild.name}")
            return True
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "load_data", guild.id
            )
            return False

    async def save_crews(self, guild: discord.Guild):
        """Wrapper for save_data to maintain compatibility"""
        await self.save_data(guild)

    # --- Preserved Original Methods (Enhanced) ---
    def truncate_nickname(self, original_name: str, emoji_prefix: str) -> str:
        """Enhanced version of original method"""
        return NicknameManager.truncate_nickname(original_name, emoji_prefix)
    
    async def set_nickname_safely(self, member: discord.Member, emoji: str, name_base: str, is_captain: bool = False) -> bool:
        """Enhanced version of original method"""
        role = CrewRole.CAPTAIN if is_captain else CrewRole.MEMBER
        success, _ = await self.nickname_manager.set_crew_nickname(member, emoji, None, role)
        return success

    def log_message(self, level: str, message: str):
        """Enhanced logging method"""
        level = level.upper()
        if level == "INFO":
            self.enhanced_logger.info(message)
        elif level == "WARNING":
            self.enhanced_logger.warning(message)
        elif level == "ERROR":
            self.enhanced_logger.error(message)
        else:
            self.enhanced_logger.info(f"[{level}] {message}")

    # --- Background Tasks ---
    @tasks.loop(hours=1)
    async def cleanup_expired_invitations(self):
        """Enhanced cleanup with better error handling"""
        try:
            current_time = datetime.datetime.now()
            expired_invites = []
            
            for msg_id, invite_data in self.active_invites.items():
                if invite_data.is_expired:
                    expired_invites.append(msg_id)
            
            for msg_id in expired_invites:
                del self.active_invites[msg_id]
                
            if expired_invites:
                self.enhanced_logger.log_system_event(
                    "cleanup_expired_invitations",
                    expired_count=len(expired_invites)
                )
                
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "cleanup_expired_invitations"
            )

    @cleanup_expired_invitations.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

    # --- Utility Methods ---
    def get_crews_for_guild(self, guild_id: str) -> Dict[str, Dict[str, Any]]:
        """Get crews for a specific guild"""
        return self.crews.get(str(guild_id), {})

    # --- Event Listeners ---
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initialize data storage when bot joins a guild"""
        try:
            guild_id = str(guild.id)
            if guild_id not in self.crews:
                self.crews[guild_id] = {}
            
            self.enhanced_logger.log_system_event("bot_joined_guild", guild_id=guild.id)
        except Exception as e:
            self.enhanced_logger.log_error_with_context(e, "on_guild_join", guild.id)

    # --- Cog Lifecycle ---
    async def cog_unload(self):
        """Cleanup when cog is unloaded"""
        try:
            self.cleanup_expired_invitations.cancel()
            self.enhanced_logger.log_system_event("cog_unloaded")
        except Exception as e:
            self.enhanced_logger.error(f"Error during cog unload: {e}")
