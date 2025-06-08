"""
crewbattles/crew.py
Main crew management cog with all enhanced functionality
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Union, Any
import asyncio
import datetime
import hashlib

import aiohttp
import discord
from discord.ext import commands, tasks
from redbot.core import Config
from redbot.core.data_manager import cog_data_path

# Import our enhanced components
from constants import CrewRole, CrewSettings, EMBED_COLORS, CREW_COLORS
from exceptions import *
from models import CrewData, CrewStats, CrewMember, InviteData
from logger import EnhancedCrewLogger
from utils import NicknameManager, EmbedBuilder, ValidationUtils, PermissionUtils
from data_manager import DataManager
from ui import CrewManagementView, CrewInviteView, CrewButton, CrewView

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
    async def fetch_custom_emoji(self, emoji_url: str, guild: discord.Guild) -> str:
        """Fetch and upload a custom emoji to the guild"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(emoji_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        try:
                            emoji = await guild.create_custom_emoji(name="crew_emoji", image=image_data)
                            return str(emoji)
                        except discord.Forbidden:
                            return CrewSettings.DEFAULT_EMOJI
                        except Exception as e:
                            self.enhanced_logger.error(f"Error creating custom emoji: {e}")
                            return CrewSettings.DEFAULT_EMOJI
                    return CrewSettings.DEFAULT_EMOJI
        except Exception as e:
            self.enhanced_logger.error(f"Error fetching custom emoji: {e}")
            return CrewSettings.DEFAULT_EMOJI

    def get_crews_for_guild(self, guild_id: str) -> Dict[str, Dict[str, Any]]:
        """Get crews for a specific guild"""
        return self.crews.get(str(guild_id), {})

    async def create_enhanced_crew_embed(self, guild: discord.Guild, crew_name: str, crew_data: Dict[str, Any]) -> discord.Embed:
        """Create an enhanced crew information embed"""
        try:
            # Create color based on crew name
            color_hash = int(hashlib.md5(crew_name.encode()).hexdigest()[:6], 16)
            
            # Create stats object
            stats = CrewStats.from_dict(crew_data.get("stats", {}))
            
            embed = discord.Embed(
                title=f"{crew_data.get('emoji', '🏴‍☠️')} {crew_name} [{crew_data.get('tag', 'N/A')}]",
                color=color_hash,
                timestamp=datetime.datetime.now()
            )
            
            # Get role objects and member counts
            captain_role = guild.get_role(crew_data.get("captain_role"))
            vice_captain_role = guild.get_role(crew_data.get("vice_captain_role"))
            crew_role = guild.get_role(crew_data.get("crew_role"))
            
            total_members = len(crew_data.get("members", []))
            captains = len(captain_role.members) if captain_role else 0
            vice_captains = len(vice_captain_role.members) if vice_captain_role else 0
            regular_members = total_members - captains - vice_captains
            
            embed.add_field(
                name="👥 Membership",
                value=(
                    f"**Total:** {total_members}\n"
                    f"**Captains:** {captains}\n"
                    f"**Vice Captains:** {vice_captains}\n"
                    f"**Members:** {regular_members}"
                ),
                inline=True
            )
            
            # Enhanced statistics
            embed.add_field(
                name="📊 Battle Stats",
                value=(
                    f"**Win Rate:** {stats.win_rate:.1f}%\n"
                    f"**Total Battles:** {stats.total_battles}\n"
                    f"**Wins:** {stats.wins} | **Losses:** {stats.losses}"
                ),
                inline=True
            )
            
            embed.add_field(
                name="🏆 Tournament Stats",
                value=(
                    f"**Tournaments Won:** {stats.tournaments_won}\n"
                    f"**Tournaments Entered:** {stats.tournaments_participated}\n"
                    f"**Tournament Win Rate:** {stats.tournament_win_rate:.1f}%"
                ),
                inline=True
            )
            
            # Creation info
            try:
                created_date = datetime.datetime.fromisoformat(
                    crew_data.get("created_at", datetime.datetime.now().isoformat())
                )
                days_active = (datetime.datetime.now() - created_date).days
                
                embed.add_field(
                    name="📅 Crew Info",
                    value=(
                        f"**Created:** {created_date.strftime('%Y-%m-%d')}\n"
                        f"**Days Active:** {days_active}\n"
                        f"**Activity Level:** {stats.get_activity_level()}"
                    ),
                    inline=False
                )
            except:
                embed.add_field(
                    name="📅 Crew Info",
                    value=f"**Tag:** `{crew_data.get('tag', 'N/A')}`",
                    inline=False
                )
            
            # Show leadership
            leadership = []
            if captain_role:
                captains_list = [m.display_name for m in captain_role.members[:3]]
                if captains_list:
                    leadership.append(f"👑 **Captains:** {', '.join(captains_list)}")
            
            if vice_captain_role:
                vice_captains_list = [m.display_name for m in vice_captain_role.members[:3]]
                if vice_captains_list:
                    leadership.append(f"⭐ **Vice Captains:** {', '.join(vice_captains_list)}")
            
            if leadership:
                embed.add_field(
                    name="👑 Leadership",
                    value="\n".join(leadership),
                    inline=False
                )
            
            embed.set_footer(text="Enhanced Crew System v2.0")
            return embed
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "create_enhanced_crew_embed", guild.id,
                crew_name=crew_name
            )
            
            # Fallback to basic embed
            return EmbedBuilder.create_error_embed(
                f"Crew: {crew_name}",
                "Error loading detailed information"
            )

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
            
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Handle members leaving the server"""
        try:
            guild = member.guild
            guild_id = str(guild.id)
            
            if guild_id not in self.crews:
                return
            
            async with self.get_guild_lock(guild_id):
                removed_from_crews = []
                
                for crew_name, crew in self.crews[guild_id].items():
                    if member.id in crew.get("members", []):
                        crew["members"].remove(member.id)
                        removed_from_crews.append(crew_name)
                        
                        self.enhanced_logger.log_user_action(
                            "member_left_server", member.id, guild.id,
                            crew_name=crew_name
                        )
                
                if removed_from_crews:
                    await self.save_crews(guild)
                    
        except Exception as e:
            self.enhanced_logger.log_error_with_context(e, "on_member_remove", guild.id, member.id)

    # --- Cog Lifecycle ---
    async def cog_unload(self):
        """Cleanup when cog is unloaded"""
        try:
            self.cleanup_expired_invitations.cancel()
            self.enhanced_logger.log_system_event("cog_unloaded")
        except Exception as e:
            self.enhanced_logger.error(f"Error during cog unload: {e}")

    def cog_unload_sync(self):
        """Synchronous cleanup when cog is unloaded"""
        try:
            self.cleanup_expired_invitations.cancel()
            print("CrewManagement cog unloaded")
        except Exception as e:
            print(f"Error during cog unload: {e}")

from setup import setup_commands
setup_commands(CrewManagement)