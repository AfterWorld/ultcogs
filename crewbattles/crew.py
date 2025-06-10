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
        
        # ENHANCED: Check Discord roles first to detect current crew membership
        current_crew = await self._get_member_current_crew(member, crews)
        
        if current_crew:
            if current_crew == crew_name:
                await ctx.send(embed=EmbedBuilder.create_warning_embed(
                    "Already in Crew",
                    f"You are already a member of **{crew_name}**."
                ))
                return
            else:
                await ctx.send(embed=EmbedBuilder.create_warning_embed(
                    "Already in a Crew",
                    f"You are already a member of **{current_crew}**. You cannot switch crews once you join one."
                ))
                return
        
        # Add to crew
        async with self.get_guild_lock(guild_id):
            # Ensure member is in the list (in case of data sync issues)
            if member.id not in crew.get("members", []):
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

    async def create_enhanced_crew_embed(self, guild: discord.Guild, crew_name: str, crew_data: dict) -> discord.Embed:
        """Create an enhanced embed showing detailed crew information"""
        try:
            # Get crew information
            emoji = crew_data.get('emoji', '🏴‍☠️')
            tag = crew_data.get('tag', 'N/A')
            members = crew_data.get('members', [])
            
            # Get role objects
            captain_role = guild.get_role(crew_data.get("captain_role"))
            vice_captain_role = guild.get_role(crew_data.get("vice_captain_role"))
            crew_role = guild.get_role(crew_data.get("crew_role"))
            
            # Count members by role
            total_members = len(members)
            captains = len(captain_role.members) if captain_role else 0
            vice_captains = len(vice_captain_role.members) if vice_captain_role else 0
            regular_members = total_members - captains - vice_captains
            
            # Find captain
            captain = next((m for m in guild.members if captain_role and captain_role in m.roles), None)
            
            # Get statistics
            stats = crew_data.get('stats', {})
            wins = stats.get('wins', 0)
            losses = stats.get('losses', 0)
            tournaments_won = stats.get('tournaments_won', 0)
            tournaments_participated = stats.get('tournaments_participated', 0)
            
            # Calculate rates
            total_battles = wins + losses
            win_rate = (wins / total_battles * 100) if total_battles > 0 else 0.0
            tournament_win_rate = (tournaments_won / tournaments_participated * 100) if tournaments_participated > 0 else 0.0
            
            # Create embed
            embed = discord.Embed(
                title=f"{emoji} {crew_name} [{tag}]",
                description=crew_data.get('description', 'A mighty crew ready for battle!'),
                color=crew_data.get('color') or discord.Color.blue()
            )
            
            # Add crew information
            embed.add_field(
                name="👥 Membership",
                value=(
                    f"**Total:** {total_members}\n"
                    f"**Captain:** {captain.display_name if captain else 'None'}\n"
                    f"**Vice Captains:** {vice_captains}\n"
                    f"**Members:** {regular_members}"
                ),
                inline=True
            )
            
            embed.add_field(
                name="📊 Battle Statistics",
                value=(
                    f"**Win Rate:** {win_rate:.1f}%\n"
                    f"**Total Battles:** {total_battles}\n"
                    f"**Wins:** {wins}\n"
                    f"**Losses:** {losses}"
                ),
                inline=True
            )
            
            # Add tournament info if there are tournaments
            if tournaments_participated > 0:
                embed.add_field(
                    name="🏆 Tournament Record",
                    value=(
                        f"**Tournament Win Rate:** {tournament_win_rate:.1f}%\n"
                        f"**Tournaments Won:** {tournaments_won}\n"
                        f"**Tournaments Played:** {tournaments_participated}"
                    ),
                    inline=True
                )
            
            # Add role information
            role_info = []
            if captain_role:
                role_info.append(f"**Captain Role:** {captain_role.mention}")
            if vice_captain_role:
                role_info.append(f"**Vice Captain Role:** {vice_captain_role.mention}")
            if crew_role:
                role_info.append(f"**Crew Role:** {crew_role.mention}")
            
            if role_info:
                embed.add_field(
                    name="🎭 Discord Roles",
                    value="\n".join(role_info),
                    inline=False
                )
            
            # Add creation date if available
            if 'created_at' in crew_data:
                try:
                    created_date = datetime.datetime.fromisoformat(crew_data['created_at'])
                    embed.add_field(
                        name="📅 Crew Founded",
                        value=created_date.strftime("%B %d, %Y"),
                        inline=True
                    )
                    
                    # Calculate days active
                    days_active = (datetime.datetime.now() - created_date).days
                    embed.add_field(
                        name="⏰ Days Active",
                        value=f"{days_active} days",
                        inline=True
                    )
                except:
                    pass  # Skip if date parsing fails
            
            # Add performance level based on stats
            if total_battles > 0:
                if win_rate >= 70:
                    performance = "🔥 Excellent"
                elif win_rate >= 50:
                    performance = "✅ Good"
                elif win_rate >= 30:
                    performance = "⚖️ Average"
                else:
                    performance = "📈 Improving"
                
                embed.add_field(
                    name="📈 Performance Level",
                    value=performance,
                    inline=True
                )
            
            # Set footer
            embed.set_footer(text=f"Enhanced Crew System • Use 'crew join {crew_name}' to join!")
            
            return embed
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "create_enhanced_crew_embed", guild.id, crew_name=crew_name
            )
            
            # Return a basic fallback embed
            return EmbedBuilder.create_crew_embed(
                f"{crew_data.get('emoji', '🏴‍☠️')} {crew_name}",
                f"Members: {len(crew_data.get('members', []))}",
                crew_name=crew_name
            )

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
            
            # Create reaction-based crew selection
            reaction_embed = EmbedBuilder.create_info_embed(
                "🎯 Quick Join with Reactions",
                "Click the emoji below to instantly join that crew!"
            )
            
            # Add crew list with emojis for reactions
            crew_reaction_list = []
            crew_emojis = []
            for crew_name, crew_data in crews.items():
                emoji = crew_data.get('emoji', '🏴‍☠️')
                tag = crew_data.get('tag', '')
                member_count = len(crew_data.get('members', []))
                crew_reaction_list.append(f"{emoji} **{crew_name}** [{tag}]")
                crew_emojis.append((emoji, crew_name))
            
            reaction_embed.add_field(
                name="Available Crews",
                value="\n".join(crew_reaction_list),
                inline=False
            )
            
            reaction_embed.add_field(
                name="How It Works",
                value="1️⃣ Click a crew emoji below\n2️⃣ You'll be instantly added to that crew!\n3️⃣ You can only join one crew, so choose wisely!",
                inline=False
            )
            
            # Post the reaction message
            reaction_message = await ctx.send(embed=reaction_embed)
            
            # Add reactions for each crew
            for emoji, crew_name in crew_emojis:
                try:
                    await reaction_message.add_reaction(emoji)
                except discord.HTTPException:
                    # If custom emoji fails, continue with others
                    self.enhanced_logger.warning(f"Failed to add reaction {emoji} for crew {crew_name}")
                    continue
            
            # Store the message for reaction handling
            guild_id = str(ctx.guild.id)
            if guild_id not in self.active_crew_messages:
                self.active_crew_messages[guild_id] = {}
            
            self.active_crew_messages[guild_id][reaction_message.id] = {
                "type": "crew_selection",
                "crews": {emoji: crew_name for emoji, crew_name in crew_emojis},
                "channel_id": ctx.channel.id,
                "created_at": datetime.datetime.now().isoformat()
            }
            
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
    async def on_reaction_add(self, reaction, user):
        """Handle crew joining via reactions"""
        # Ignore bot reactions
        if user.bot:
            return
        
        guild = reaction.message.guild
        if not guild:
            return
            
        guild_id = str(guild.id)
        message_id = reaction.message.id
        
        # Check if this is a crew selection message
        if (guild_id not in self.active_crew_messages or 
            message_id not in self.active_crew_messages[guild_id]):
            return
        
        message_data = self.active_crew_messages[guild_id][message_id]
        if message_data["type"] != "crew_selection":
            return
        
        # Get the crew for this emoji
        emoji_str = str(reaction.emoji)
        crew_name = message_data["crews"].get(emoji_str)
        
        if not crew_name:
            return
        
        try:
            # Process the crew join
            success = await self._process_crew_join_reaction(user, guild, crew_name, reaction)
            
            if success:
                # Remove the user's reaction to keep the message clean
                try:
                    await reaction.remove(user)
                except discord.Forbidden:
                    pass  # Can't remove reactions, but that's okay
                    
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "on_reaction_add", guild.id, user.id,
                crew_name=crew_name
            )
    
    async def _process_crew_join_reaction(self, user, guild, crew_name: str, reaction) -> bool:
        """Process a crew join via reaction"""
        guild_id = str(guild.id)
        crews = self.crews.get(guild_id, {})
        
        if crew_name not in crews:
            return False
        
        crew = crews[crew_name]
        member = guild.get_member(user.id)
        
        if not member:
            return False
        
        # ENHANCED: Check Discord roles first to detect current crew membership
        current_crew = await self._get_member_current_crew(member, crews)
        
        if current_crew:
            if current_crew == crew_name:
                try:
                    await user.send(f"⚠️ You are already a member of **{crew_name}**!")
                except discord.Forbidden:
                    pass
                return False
            else:
                try:
                    await user.send(f"⚠️ You are already a member of **{current_crew}**. You cannot switch crews once you join one.")
                except discord.Forbidden:
                    pass
                return False
        
        # Add to crew
        async with self.get_guild_lock(guild_id):
            # Ensure member is in the list (in case of data sync issues)
            if member.id not in crew.get("members", []):
                crew["members"].append(member.id)
            
            # Assign crew role
            crew_role = guild.get_role(crew.get("crew_role"))
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
            
            await self.save_crews(guild)
        
        # Log the action
        self.enhanced_logger.log_user_action(
            "joined_crew_via_reaction", member.id, guild.id,
            crew_name=crew_name
        )
        
        # Send success message
        try:
            success_message = f"🎉 Welcome to **{crew_name}**! {crew.get('emoji', '🏴‍☠️')}"
            
            warnings = []
            if not role_assigned:
                warnings.append("⚠️ Couldn't assign crew role due to permission issues")
            if not nickname_success:
                warnings.append("⚠️ Couldn't update nickname due to permission issues")
            
            if warnings:
                success_message += "\n\n" + "\n".join(warnings)
            
            await user.send(success_message)
        except discord.Forbidden:
            # Can't DM user, try to send in channel
            try:
                channel = guild.get_channel(reaction.message.channel.id)
                if channel:
                    await channel.send(f"🎉 {member.mention} has joined **{crew_name}**! {crew.get('emoji', '🏴‍☠️')}", delete_after=5)
            except:
                pass
        
        return True

    async def _get_member_current_crew(self, member: discord.Member, crews: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """Get the crew a member is currently in by checking their Discord roles"""
        for crew_name, crew_data in crews.items():
            # Check all crew roles (captain, vice captain, regular crew)
            crew_roles = [
                crew_data.get("captain_role"),
                crew_data.get("vice_captain_role"), 
                crew_data.get("crew_role")
            ]
            
            for role_id in crew_roles:
                if role_id and any(role.id == role_id for role in member.roles):
                    return crew_name
        
        return None

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

# DON'T load setup commands for now - test basic functionality first
# from .setup import setup_commands
# setup_commands(CrewManagement)
