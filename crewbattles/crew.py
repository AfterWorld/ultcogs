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

    @crew_commands.command(name="view")
    async def crew_view(self, ctx, *, crew_name: str):
        """View detailed information about a specific crew"""
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if crew_name not in crews:
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Crew Not Found",
                f"No crew named `{crew_name}` exists."
            ))
            return
        
        embed = await self.create_enhanced_crew_embed(ctx.guild, crew_name, crews[crew_name])
        await ctx.send(embed=embed)

    @crew_commands.command(name="join")
    async def crew_join(self, ctx, *, crew_name: str):
        """Join a specific crew"""
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        member = ctx.author
        
        if crew_name not in crews:
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Crew Not Found",
                f"No crew named `{crew_name}` exists."
            ))
            return
        
        crew = crews[crew_name]
        
        # Check if already in this crew
        if member.id in crew.get("members", []):
            await ctx.send(embed=EmbedBuilder.create_warning_embed(
                "Already in Crew",
                f"You are already a member of `{crew_name}`."
            ))
            return
        
        # Check if in another crew
        for other_name, other_crew in crews.items():
            if member.id in other_crew.get("members", []):
                await ctx.send(embed=EmbedBuilder.create_warning_embed(
                    "Already in a Crew",
                    f"You are already in the crew `{other_name}`. You cannot switch crews once you join one."
                ))
                return
        
        # Add to crew
        async with self.get_guild_lock(guild_id):
            crew["members"].append(member.id)
            
            # Assign crew role
            crew_role = ctx.guild.get_role(crew.get("crew_role"))
            role_assigned = False
            
            if crew_role:
                try:
                    await member.add_roles(crew_role)
                    role_assigned = True
                except discord.Forbidden:
                    pass
            
            # Update nickname
            nickname_success = False
            if hasattr(self, 'nickname_manager'):
                nickname_success, _ = await self.nickname_manager.set_crew_nickname(
                    member, crew.get("emoji", "🏴‍☠️"), crew.get("tag"), CrewRole.MEMBER
                )
            
            await self.save_crews(ctx.guild)
        
        # Log the action
        self.enhanced_logger.log_user_action(
            "joined_crew", member.id, ctx.guild.id,
            crew_name=crew_name
        )
        
        # Create response
        embed = EmbedBuilder.create_success_embed(
            "Successfully Joined Crew",
            f"Welcome to **{crew_name}**! {crew.get('emoji', '🏴‍☠️')}"
        )
        
        warnings = []
        if not role_assigned:
            warnings.append("⚠️ Couldn't assign crew role due to permission issues")
        if not nickname_success:
            warnings.append("⚠️ Couldn't update nickname due to permission issues")
        
        if warnings:
            embed.add_field(
                name="Warnings",
                value="\n".join(warnings),
                inline=False
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

    # --- Setup Commands Group ---
    @commands.group(name="crewsetup")
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def crew_setup(self, ctx):
        """Commands for setting up the crew system."""
        if ctx.invoked_subcommand is None:
            embed = EmbedBuilder.create_info_embed(
                "Crew Setup Commands",
                "Available setup commands for the crew system"
            )
            embed.add_field(
                name="📝 Basic Setup",
                value=(
                    "`crewsetup init` - Initialize the crew system\n"
                    "`crewsetup status` - Check setup status\n"
                    "`crewsetup finish` - Post crew selection interface"
                ),
                inline=False
            )
            await ctx.send(embed=embed)

    @crew_setup.command(name="init")
    async def setup_init(self, ctx):
        """Initialize the crew system for this server."""
        try:
            guild_id = str(ctx.guild.id)
            
            # Initialize guild namespaces if they don't exist
            if guild_id not in self.crews:
                self.crews[guild_id] = {}
            
            # Create data directories
            self.data_manager.crews_dir.mkdir(exist_ok=True)
            self.data_manager.backup_dir.mkdir(exist_ok=True)
            
            await self.config.guild(ctx.guild).finished_setup.set(True)
            await self.save_data(ctx.guild)
            
            self.enhanced_logger.log_crew_action("system_initialized", ctx.guild.id, ctx.author.id)
            
            embed = EmbedBuilder.create_success_embed(
                "Crew System Initialized",
                "✅ The crew system has been successfully initialized for this server."
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "setup_init", ctx.guild.id, ctx.author.id
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Initialization Failed",
                "An error occurred while initializing the crew system."
            ))

    @crew_setup.command(name="status")
    async def setup_status(self, ctx):
        """Show the current status of the crew system setup."""
        try:
            guild_id = str(ctx.guild.id)
            
            # Check setup status
            finished_setup = await self.config.guild(ctx.guild).finished_setup()
            crews = self.crews.get(guild_id, {})
            
            # Create status embed
            embed = EmbedBuilder.create_info_embed(
                "Crew System Status",
                f"Current setup status for **{ctx.guild.name}**"
            )
            
            # Basic setup status
            setup_status = "✅ Initialized" if finished_setup else "❌ Not Initialized"
            embed.add_field(
                name="🔧 System Status",
                value=f"**Setup:** {setup_status}",
                inline=True
            )
            
            # Crew count
            embed.add_field(
                name="🏴‍☠️ Crews",
                value=f"**Count:** {len(crews)}",
                inline=True
            )
            
            # Next steps
            next_steps = []
            if not finished_setup:
                next_steps.append("• Run `crewsetup init` to initialize the system")
            if not crews:
                next_steps.append("• Create crews (you may have legacy crews)")
            else:
                next_steps.append("• Use `crewsetup finish` to post crew selection interface")
            
            if next_steps:
                embed.add_field(
                    name="📝 Next Steps",
                    value="\n".join(next_steps),
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ Setup Complete",
                    value="Your crew system is fully configured!",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "setup_status", ctx.guild.id, ctx.author.id
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Status Check Failed",
                "An error occurred while checking system status."
            ))

    @crew_setup.command(name="finish")
    async def setup_finish(self, ctx):
        """Post interactive crew selection interfaces for users to join crews."""
        try:
            # Validate setup
            finished_setup = await self.config.guild(ctx.guild).finished_setup()
            if not finished_setup:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Setup Not Complete",
                    "Crew system is not set up yet. Run `crewsetup init` first."
                ))
                return
                
            guild_id = str(ctx.guild.id)
            crews = self.crews.get(guild_id, {})
            
            if not crews:
                await ctx.send(embed=EmbedBuilder.create_warning_embed(
                    "No Crews Available",
                    "No crews have been created yet. You need existing crews to post selection interfaces."
                ))
                return
            
            # Create header embed
            header_embed = EmbedBuilder.create_info_embed(
                "🏴‍☠️ Join a Crew Today! 🏴‍☠️",
                "Choose your crew wisely - you can't switch once you join!"
            )
            header_embed.color = discord.Color.gold()
            
            # Add crew overview
            crew_list = []
            for crew_name, crew_data in crews.items():
                emoji = crew_data.get('emoji', '🏴‍☠️')
                tag = crew_data.get('tag', '')
                member_count = len(crew_data.get('members', []))
                crew_list.append(f"{emoji} **{crew_name}** [{tag}] - {member_count} members")
            
            header_embed.add_field(
                name="Available Crews",
                value="\n".join(crew_list),
                inline=False
            )
            
            header_embed.add_field(
                name="How to Join",
                value="Use `.crew join <crew name>` to join any of these crews!",
                inline=False
            )
            
            await ctx.send(embed=header_embed)
            
            # Post each crew with detailed info
            posted_crews = 0
            for crew_name, crew_data in crews.items():
                try:
                    # Create detailed crew embed
                    embed = await self.create_enhanced_crew_embed(ctx.guild, crew_name, crew_data)
                    
                    # Add join instructions
                    embed.add_field(
                        name="💫 How to Join",
                        value=f"Use `.crew join {crew_name}` to join this crew!",
                        inline=False
                    )
                    
                    await ctx.send(embed=embed)
                    posted_crews += 1
                    
                except Exception as e:
                    self.enhanced_logger.log_error_with_context(
                        e, "setup_finish_crew_post", ctx.guild.id, ctx.author.id,
                        crew_name=crew_name
                    )
                    continue
            
            # Send completion message
            completion_embed = EmbedBuilder.create_success_embed(
                "Setup Complete!",
                f"✅ Crew selection interfaces have been posted!\n\n"
                f"**{posted_crews}** crews are now available for users to join.\n"
                f"Users can join using the `.crew join <name>` command."
            )
            completion_embed.add_field(
                name="Available Commands",
                value=(
                    "`.crew join <name>` - Join a specific crew\n"
                    "`.crew list` - View all available crews\n"
                    "`.crew view <name>` - View detailed crew information"
                ),
                inline=False
            )
            
            await ctx.send(embed=completion_embed)
            
            self.enhanced_logger.log_crew_action(
                "setup_finished", ctx.guild.id, ctx.author.id, 
                crews_posted=posted_crews, total_crews=len(crews)
            )
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "setup_finish", ctx.guild.id, ctx.author.id
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Setup Finish Failed",
                "An error occurred while posting crew selection interfaces."
            ))

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

