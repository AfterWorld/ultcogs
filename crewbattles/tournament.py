"""
crewbattles/tournament.py - ENHANCED VERSION
Tournament system that properly integrates with the enhanced crew management system
"""

import asyncio
import datetime
import json
import os
import random
from pathlib import Path
from typing import Dict, List, Optional, Any

import discord
from redbot.core import commands, Config
from redbot.core.data_manager import cog_data_path

# Import enhanced components from the crew system
from .constants import CrewSettings, EMBED_COLORS
from .utils import EmbedBuilder, PermissionUtils
from .logger import EnhancedCrewLogger
from .exceptions import CrewError


class TournamentSystem(commands.Cog):
    """Enhanced tournament system with proper crew integration"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=8765432109, force_registration=True)
        
        # Default configuration
        default_guild = {
            "finished_setup": False,
            "tournament_settings": {
                "max_participants": 16,
                "min_participants": 2,
                "allow_auto_join": True
            }
        }
        
        self.config.register_guild(**default_guild)
        self.tournaments = {}
        self.active_channels = set()
        self.guild_locks = {}
        self._crew_manager = None
        
        # Initialize enhanced components
        self.data_path = cog_data_path(self)
        self.enhanced_logger = EnhancedCrewLogger("TournamentSystem", self.data_path)
        
        # Define enhanced battle moves
        self.MOVES = [
            {"name": "Strike", "type": "regular", "description": "A basic attack", "effect": None},
            {"name": "Slash", "type": "regular", "description": "A quick sword slash", "effect": None},
            {"name": "Punch", "type": "regular", "description": "A direct hit", "effect": None},
            {"name": "Fireball", "type": "strong", "description": "A ball of fire", "effect": "burn", "burn_chance": 0.5},
            {"name": "Thunder Strike", "type": "strong", "description": "A bolt of lightning", "effect": "stun", "stun_chance": 0.3},
            {"name": "Heavy Blow", "type": "strong", "description": "A powerful attack", "effect": None},
            {"name": "Critical Smash", "type": "critical", "description": "A devastating attack", "effect": None},
            {"name": "Ultimate Strike", "type": "critical", "description": "An ultimate power move", "effect": None},
            {"name": "Gum-Gum Pistol", "type": "strong", "description": "Luffy's signature attack", "effect": None},
            {"name": "Three-Sword Style", "type": "critical", "description": "Zoro's powerful technique", "effect": None},
            {"name": "Black Leg", "type": "regular", "description": "Sanji's kick technique", "effect": None}
        ]
        
        # Initialize on startup
        self.bot.loop.create_task(self.initialize())
        
        self.enhanced_logger.log_system_event("tournament_system_initialized")

    def get_guild_lock(self, guild_id: str) -> asyncio.Lock:
        """Get a lock for a specific guild, creating it if it doesn't exist."""
        if guild_id not in self.guild_locks:
            self.guild_locks[guild_id] = asyncio.Lock()
        return self.guild_locks[guild_id]

    def set_crew_manager(self, crew_manager):
        """Set the crew manager reference."""
        self._crew_manager = crew_manager
        self.enhanced_logger.log_system_event("crew_manager_set")
        
    def get_crew_manager(self):
        """Get the crew manager reference."""
        if not self._crew_manager:
            self._crew_manager = self.bot.get_cog("CrewManagement")
            if not self._crew_manager:
                self.enhanced_logger.warning("CrewManagement cog not found when needed")
        return self._crew_manager

    def get_crews_for_guild(self, guild_id: str) -> Dict[str, Any]:
        """Get crews for a guild from the crew manager."""
        crew_manager = self.get_crew_manager()
        if not crew_manager:
            return {}
        
        # Access the crews directly from the crew manager
        return crew_manager.crews.get(guild_id, {})

    async def initialize(self):
        """Initialize the cog by loading data from all guilds."""
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            try:
                await self.load_data(guild)
                self.enhanced_logger.info(f"Initialized tournament data for guild: {guild.name}")
            except Exception as e:
                self.enhanced_logger.log_error_with_context(
                    e, f"Failed to initialize guild {guild.name}", guild.id
                )

    async def save_data(self, guild: discord.Guild) -> bool:
        """Save tournament data for a specific guild."""
        try:
            finished_setup = await self.config.guild(guild).finished_setup()
            if not finished_setup:
                return True
        
            # Create tournaments directory
            tournaments_dir = self.data_path / "Tournaments"
            tournaments_dir.mkdir(exist_ok=True)
            
            file_path = tournaments_dir / f"{guild.id}.json"
            guild_id = str(guild.id)
            
            data = {
                "tournaments": self.tournaments.get(guild_id, {}),
                "metadata": {
                    "version": "enhanced_v1.0",
                    "last_modified": datetime.datetime.now().isoformat(),
                    "guild_id": guild.id,
                    "guild_name": guild.name
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.enhanced_logger.log_data_operation(
                "save_tournament_data", guild.id, True,
                tournament_count=len(self.tournaments.get(guild_id, {}))
            )
            return True
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "save_tournament_data", guild.id
            )
            return False
    
    async def load_data(self, guild: discord.Guild) -> bool:
        """Load tournament data for a specific guild."""
        try:
            if not guild:
                return False
        
            finished_setup = await self.config.guild(guild).finished_setup()
            if not finished_setup:
                return True
        
            tournaments_dir = self.data_path / "Tournaments"
            file_path = tournaments_dir / f"{guild.id}.json"
            guild_id = str(guild.id)
            
            if not file_path.exists():
                self.enhanced_logger.info(f"No tournament data file found for guild {guild.name}")
                return True
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Initialize guild namespace
            if guild_id not in self.tournaments:
                self.tournaments[guild_id] = {}
            
            # Load tournaments
            tournaments_data = data.get("tournaments", {})
            self.tournaments[guild_id] = tournaments_data
            
            self.enhanced_logger.log_data_operation(
                "load_tournament_data", guild.id, True,
                tournament_count=len(tournaments_data)
            )
            return True
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "load_tournament_data", guild.id
            )
            return False

    async def save_tournaments(self, guild: discord.Guild):
        """Save tournament data with enhanced error handling."""
        await self.save_data(guild)
    
    def generate_health_bar(self, hp: int, max_hp: int = 100, bar_length: int = 10) -> str:
        """Generate a visual health bar."""
        if max_hp <= 0:
            return '░' * bar_length
        
        filled_length = max(0, min(bar_length, int(hp / max_hp * bar_length)))
        return '█' * filled_length + '░' * (bar_length - filled_length)

    def get_tournaments_for_guild(self, guild_id: str) -> Dict[str, Any]:
        """Get tournaments for a specific guild."""
        return self.tournaments.get(guild_id, {})

    # --- Setup Command Group ---
    @commands.group(name="tournysetup")
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def tournament_setup(self, ctx):
        """Commands for setting up the tournament system."""
        if ctx.invoked_subcommand is None:
            embed = EmbedBuilder.create_info_embed(
                "Tournament Setup Commands",
                "Available setup commands for the tournament system"
            )
            embed.add_field(
                name="📝 Basic Setup",
                value=(
                    "`tournysetup init` - Initialize the tournament system\n"
                    "`tournysetup reset` - Reset all tournament data\n"
                    "`tournysetup status` - Check setup status"
                ),
                inline=False
            )
            await ctx.send(embed=embed)

    @tournament_setup.command(name="init")
    async def setup_init(self, ctx):
        """Initialize the tournament system for this server."""
        try:
            guild_id = str(ctx.guild.id)
            
            # Initialize guild namespaces
            if guild_id not in self.tournaments:
                self.tournaments[guild_id] = {}
            
            # Create data directory
            tournaments_dir = self.data_path / "Tournaments"
            tournaments_dir.mkdir(exist_ok=True)
            
            await self.config.guild(ctx.guild).finished_setup.set(True)
            await self.save_data(ctx.guild)
            
            self.enhanced_logger.log_crew_action(
                "tournament_system_initialized", ctx.guild.id, ctx.author.id
            )
            
            embed = EmbedBuilder.create_success_embed(
                "Tournament System Initialized",
                "✅ The tournament system has been successfully initialized for this server."
            )
            embed.add_field(
                name="Next Steps",
                value=(
                    "• Create tournaments with `tourny create`\n"
                    "• Add crews with `tourny add`\n"
                    "• Start tournaments with `tourny start`"
                ),
                inline=False
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "tournament_setup_init", ctx.guild.id, ctx.author.id
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Initialization Failed",
                "An error occurred while initializing the tournament system."
            ))

    @tournament_setup.command(name="reset")
    async def setup_reset(self, ctx):
        """Reset all tournament data for this server."""
        try:
            # Confirmation check
            embed = EmbedBuilder.create_warning_embed(
                "Confirm Reset",
                "⚠️ **WARNING:** This will permanently delete ALL tournament data!\n\n"
                "Type `CONFIRM RESET` to proceed:"
            )
            await ctx.send(embed=embed)
            
            def check(m):
                return (m.author == ctx.author and 
                       m.channel == ctx.channel and 
                       m.content == "CONFIRM RESET")
            
            try:
                await self.bot.wait_for("message", check=check, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send(embed=EmbedBuilder.create_info_embed(
                    "Reset Cancelled",
                    "Reset operation timed out."
                ))
                return
            
            guild_id = str(ctx.guild.id)
            tournament_count = len(self.tournaments.get(guild_id, {}))
            
            # Clear data
            if guild_id in self.tournaments:
                self.tournaments[guild_id] = {}
            
            await self.save_data(ctx.guild)
            
            self.enhanced_logger.log_crew_action(
                "tournament_system_reset", ctx.guild.id, ctx.author.id,
                tournaments_deleted=tournament_count
            )
            
            embed = EmbedBuilder.create_success_embed(
                "Reset Complete",
                f"✅ All tournament data has been reset.\n**{tournament_count}** tournaments were deleted."
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "tournament_setup_reset", ctx.guild.id, ctx.author.id
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Reset Failed",
                "An error occurred while resetting tournament data."
            ))

    @tournament_setup.command(name="status")
    async def setup_status(self, ctx):
        """Show the current status of the tournament system setup."""
        try:
            guild_id = str(ctx.guild.id)
            
            # Check setup status
            finished_setup = await self.config.guild(ctx.guild).finished_setup()
            tournaments = self.tournaments.get(guild_id, {})
            
            # Check crew system integration
            crew_manager = self.get_crew_manager()
            crews = self.get_crews_for_guild(guild_id) if crew_manager else {}
            
            embed = EmbedBuilder.create_info_embed(
                "Tournament System Status",
                f"Current setup status for **{ctx.guild.name}**"
            )
            
            # Basic setup status
            setup_status = "✅ Initialized" if finished_setup else "❌ Not Initialized"
            embed.add_field(
                name="🔧 System Status",
                value=f"**Setup:** {setup_status}",
                inline=True
            )
            
            # Integration status
            crew_integration = "✅ Connected" if crew_manager else "❌ Not Connected"
            embed.add_field(
                name="🔗 Crew Integration",
                value=f"**Status:** {crew_integration}",
                inline=True
            )
            
            # Tournament count
            embed.add_field(
                name="🏆 Tournaments",
                value=f"**Count:** {len(tournaments)}",
                inline=True
            )
            
            # Available crews
            embed.add_field(
                name="🏴‍☠️ Available Crews",
                value=f"**Count:** {len(crews)}",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "tournament_setup_status", ctx.guild.id, ctx.author.id
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Status Check Failed",
                "An error occurred while checking system status."
            ))

    # --- Tournament Command Group ---
    @commands.group(name="tourny")
    @commands.guild_only()
    async def tournament_commands(self, ctx):
        """Commands for managing tournaments."""
        if ctx.invoked_subcommand is None:
            embed = EmbedBuilder.create_info_embed(
                "Tournament Commands",
                "Available tournament management commands"
            )
            embed.add_field(
                name="📋 Management",
                value=(
                    "`tourny create <name>` - Create a tournament (Admin)\n"
                    "`tourny list` - List all tournaments\n"
                    "`tourny view <name>` - View tournament details\n"
                    "`tourny delete <name>` - Delete a tournament (Admin)"
                ),
                inline=False
            )
            embed.add_field(
                name="👥 Participation",
                value=(
                    "`tourny add <tournament> <crew>` - Add crew (Admin)\n"
                    "`tourny remove <tournament> <crew>` - Remove crew (Admin)\n"
                    "`tourny invite <tournament>` - Invite all crews (Admin)\n"
                    "`tourny start <tournament>` - Start tournament (Admin)"
                ),
                inline=False
            )
            embed.add_field(
                name="📊 Statistics",
                value="`tourny stats [crew]` - View tournament statistics",
                inline=False
            )
            await ctx.send(embed=embed)

    @tournament_commands.command(name="create")
    @commands.admin_or_permissions(administrator=True)
    async def tournament_create(self, ctx, *, name: str):
        """Create a new tournament. Only admins can use this command."""
        try:
            # Validate setup
            finished_setup = await self.config.guild(ctx.guild).finished_setup()
            if not finished_setup:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Setup Required",
                    "Tournament system is not set up yet. Ask an admin to run `tournysetup init` first."
                ))
                return
            
            # Validate name
            if not name or len(name.strip()) == 0:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Invalid Name",
                    "Tournament name cannot be empty."
                ))
                return
            
            name = name.strip()
            if len(name) > 50:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Name Too Long",
                    "Tournament name must be 50 characters or less."
                ))
                return
                
            guild_id = str(ctx.guild.id)
            tournaments = self.tournaments.get(guild_id, {})
            
            if name in tournaments:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Tournament Exists",
                    f"A tournament with the name `{name}` already exists."
                ))
                return
                
            # Initialize guild namespace if not exists
            if guild_id not in self.tournaments:
                self.tournaments[guild_id] = {}
                
            # Create tournament
            self.tournaments[guild_id][name] = {
                "name": name,
                "creator": ctx.author.id,
                "crews": [],
                "started": False,
                "created_at": datetime.datetime.now().isoformat()
            }
            
            await self.save_tournaments(ctx.guild)
            
            self.enhanced_logger.log_crew_action(
                "tournament_created", ctx.guild.id, ctx.author.id,
                tournament_name=name
            )
            
            # Send tournament info
            embed = EmbedBuilder.create_success_embed(
                f"Tournament Created: {name}",
                "Tournament has been successfully created!"
            )
            embed.add_field(
                name="📋 Tournament Details",
                value=(
                    f"**Creator:** {ctx.author.mention}\n"
                    f"**Status:** Recruiting\n"
                    f"**Participating Crews:** 0"
                ),
                inline=False
            )
            embed.add_field(
                name="🔧 Next Steps",
                value=(
                    f"• Add crews: `tourny add {name} <crew_name>`\n"
                    f"• Invite all crews: `tourny invite {name}`\n"
                    f"• Start tournament: `tourny start {name}`"
                ),
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "tournament_create", ctx.guild.id, ctx.author.id,
                tournament_name=name
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Creation Failed",
                "An error occurred while creating the tournament."
            ))

    @tournament_commands.command(name="list")
    async def tournament_list(self, ctx):
        """List all available tournaments."""
        try:
            # Validate setup
            finished_setup = await self.config.guild(ctx.guild).finished_setup()
            if not finished_setup:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Setup Required",
                    "Tournament system is not set up yet. Ask an admin to run `tournysetup init` first."
                ))
                return
                
            guild_id = str(ctx.guild.id)
            tournaments = self.tournaments.get(guild_id, {})
            
            if not tournaments:
                await ctx.send(embed=EmbedBuilder.create_warning_embed(
                    "No Tournaments",
                    "No tournaments available. Ask an admin to create some with `tourny create`."
                ))
                return
            
            embed = EmbedBuilder.create_info_embed(
                "🏆 Available Tournaments",
                f"Found {len(tournaments)} tournaments in this server"
            )
            
            for name, tournament in tournaments.items():
                creator = ctx.guild.get_member(tournament["creator"])
                status = "🔄 In Progress" if tournament["started"] else "📋 Recruiting"
                crew_count = len(tournament['crews'])
                
                embed.add_field(
                    name=f"{status} {name}",
                    value=(
                        f"**Creator:** {creator.mention if creator else 'Unknown'}\n"
                        f"**Crews:** {crew_count}\n"
                        f"**Created:** {tournament.get('created_at', 'Unknown')[:10]}"
                    ),
                    inline=True
                )
                
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "tournament_list", ctx.guild.id, ctx.author.id
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "List Failed",
                "An error occurred while loading tournaments."
            ))

    @tournament_commands.command(name="view")
    async def tournament_view(self, ctx, *, name: str):
        """View the details of a tournament."""
        try:
            # Validate setup
            finished_setup = await self.config.guild(ctx.guild).finished_setup()
            if not finished_setup:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Setup Required",
                    "Tournament system is not set up yet."
                ))
                return
                
            guild_id = str(ctx.guild.id)
            tournaments = self.tournaments.get(guild_id, {})
            
            if name not in tournaments:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Tournament Not Found",
                    f"No tournament found with the name `{name}`."
                ))
                return
                
            tournament = tournaments[name]
            creator = ctx.guild.get_member(tournament["creator"])
            status = "🔄 In Progress" if tournament["started"] else "📋 Recruiting"
            
            embed = EmbedBuilder.create_info_embed(
                f"🏆 Tournament: {name}",
                f"**Status:** {status}"
            )
            
            embed.add_field(
                name="📋 Tournament Info",
                value=(
                    f"**Creator:** {creator.mention if creator else 'Unknown'}\n"
                    f"**Created:** {tournament.get('created_at', 'Unknown')[:10]}\n"
                    f"**Participating Crews:** {len(tournament['crews'])}"
                ),
                inline=False
            )
            
            # Add crew information
            crews_text = ""
            crews_dict = self.get_crews_for_guild(guild_id)
            
            for crew_name in tournament["crews"]:
                crew = crews_dict.get(crew_name)
                if crew:
                    emoji = crew.get('emoji', '🏴‍☠️')
                    member_count = len(crew.get('members', []))
                    crews_text += f"• {emoji} **{crew_name}** ({member_count} members)\n"
                else:
                    crews_text += f"• ❓ **{crew_name}** (crew not found)\n"
                    
            embed.add_field(
                name=f"🏴‍☠️ Participating Crews ({len(tournament['crews'])})",
                value=crews_text if crews_text else "No crews yet",
                inline=False
            )
            
            # Add command guidance if not started
            if not tournament["started"]:
                embed.add_field(
                    name="🔧 Available Commands",
                    value=(
                        f"• `tourny add {name} <crew_name>` - Add a crew\n"
                        f"• `tourny remove {name} <crew_name>` - Remove a crew\n"
                        f"• `tourny start {name}` - Start the tournament"
                    ),
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "tournament_view", ctx.guild.id, ctx.author.id,
                tournament_name=name
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "View Failed",
                "An error occurred while loading tournament details."
            ))

    @tournament_commands.command(name="add")
    @commands.admin_or_permissions(administrator=True)
    async def add_crew_to_tournament(self, ctx, tournament_name: str, *, crew_name: str):
        """Add a crew to a tournament. Admin only."""
        try:
            # Validate setup
            finished_setup = await self.config.guild(ctx.guild).finished_setup()
            if not finished_setup:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Setup Required",
                    "Tournament system is not set up yet."
                ))
                return
                
            guild_id = str(ctx.guild.id)
            tournaments = self.tournaments.get(guild_id, {})
            
            if tournament_name not in tournaments:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Tournament Not Found",
                    f"No tournament found with the name `{tournament_name}`."
                ))
                return
                
            tournament = tournaments[tournament_name]
            
            if tournament["started"]:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Tournament Started",
                    "This tournament has already started and cannot be modified."
                ))
                return
                
            # Get crews and validate crew exists
            crews = self.get_crews_for_guild(guild_id)
            
            if crew_name not in crews:
                # Show available crews
                available_crews = list(crews.keys())
                if available_crews:
                    crew_list = ", ".join([f"`{name}`" for name in available_crews[:10]])
                    if len(available_crews) > 10:
                        crew_list += f" ... and {len(available_crews) - 10} more"
                    await ctx.send(embed=EmbedBuilder.create_error_embed(
                        "Crew Not Found",
                        f"No crew found with the name `{crew_name}`.\n\n**Available crews:** {crew_list}"
                    ))
                else:
                    await ctx.send(embed=EmbedBuilder.create_error_embed(
                        "No Crews Available",
                        "No crews are available to add to tournaments."
                    ))
                return
                
            if crew_name in tournament["crews"]:
                await ctx.send(embed=EmbedBuilder.create_warning_embed(
                    "Already Added",
                    f"Crew `{crew_name}` is already in this tournament."
                ))
                return
                
            # Add crew to tournament
            tournament["crews"].append(crew_name)
            await self.save_tournaments(ctx.guild)
            
            self.enhanced_logger.log_crew_action(
                "crew_added_to_tournament", ctx.guild.id, ctx.author.id,
                tournament_name=tournament_name, crew_name=crew_name
            )
            
            crew_data = crews[crew_name]
            embed = EmbedBuilder.create_success_embed(
                "Crew Added",
                f"{crew_data.get('emoji', '🏴‍☠️')} **{crew_name}** has been added to tournament **{tournament_name}**!"
            )
            embed.add_field(
                name="Tournament Status",
                value=f"**Participating Crews:** {len(tournament['crews'])}",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "add_crew_to_tournament", ctx.guild.id, ctx.author.id,
                tournament_name=tournament_name, crew_name=crew_name
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Add Failed",
                "An error occurred while adding the crew to the tournament."
            ))

    @tournament_commands.command(name="start")
    @commands.admin_or_permissions(administrator=True)
    async def tournament_start(self, ctx, *, name: str):
        """Start a tournament. Only the creator or admins can use this command."""
        try:
            # Validate setup
            finished_setup = await self.config.guild(ctx.guild).finished_setup()
            if not finished_setup:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Setup Required",
                    "Tournament system is not set up yet."
                ))
                return
                
            guild_id = str(ctx.guild.id)
            
            # Check if tournament exists
            if guild_id not in self.tournaments or name not in self.tournaments[guild_id]:
                available_tournaments = list(self.tournaments.get(guild_id, {}).keys())
                if available_tournaments:
                    available = ", ".join([f"`{t}`" for t in available_tournaments])
                    await ctx.send(embed=EmbedBuilder.create_error_embed(
                        "Tournament Not Found",
                        f"No tournament found with the name `{name}`.\n\n**Available tournaments:** {available}"
                    ))
                else:
                    await ctx.send(embed=EmbedBuilder.create_error_embed(
                        "No Tournaments",
                        f"No tournament found with the name `{name}`. No tournaments are currently available."
                    ))
                return
            
            lock = self.get_guild_lock(guild_id)
            
            async with lock:
                tournament = self.tournaments[guild_id][name]
                
                # Check permissions
                is_admin = await self.bot.is_admin(ctx.author)
                if tournament["creator"] != ctx.author.id and not is_admin:
                    await ctx.send(embed=EmbedBuilder.create_error_embed(
                        "Permission Denied",
                        "Only the creator or admins can start this tournament."
                    ))
                    return
                    
                if tournament["started"]:
                    await ctx.send(embed=EmbedBuilder.create_warning_embed(
                        "Already Started",
                        "This tournament has already started."
                    ))
                    return
                    
                if len(tournament["crews"]) < 2:
                    await ctx.send(embed=EmbedBuilder.create_error_embed(
                        "Not Enough Crews",
                        f"Tournament needs at least 2 crews to start. Currently has {len(tournament['crews'])} crews.\n\n"
                        f"Use `tourny add {name} <crew_name>` to add more crews."
                    ))
                    return
                
                # Mark as started
                tournament["started"] = True
                tournament["started_at"] = datetime.datetime.now().isoformat()
                await self.save_tournaments(ctx.guild)
                
                self.enhanced_logger.log_crew_action(
                    "tournament_started", ctx.guild.id, ctx.author.id,
                    tournament_name=name, crew_count=len(tournament["crews"])
                )
                
                # Confirm to user
                embed = EmbedBuilder.create_success_embed(
                    "Tournament Started!",
                    f"🏆 Tournament **{name}** has begun with {len(tournament['crews'])} crews!"
                )
                await ctx.send(embed=embed)
            
            # Start the tournament outside the lock
            await self.run_tournament(ctx.channel, name)
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "tournament_start", ctx.guild.id, ctx.author.id,
                tournament_name=name
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Start Failed",
                "An error occurred while starting the tournament."
            ))

    async def run_tournament(self, channel: discord.TextChannel, name: str):
        """Run the tournament matches with enhanced error handling."""
        guild_id = str(channel.guild.id)
        
        if channel.id in self.active_channels:
            await channel.send(embed=EmbedBuilder.create_warning_embed(
                "Channel Busy",
                "A battle is already in progress in this channel. Please wait for it to finish."
            ))
            return
            
        # Mark channel as active
        self.active_channels.add(channel.id)
        self.enhanced_logger.log_crew_action(
            "tournament_battle_started", channel.guild.id,
            tournament_name=name, channel_id=channel.id
        )
        
        try:
            guild = channel.guild
            tournaments = self.tournaments.get(guild_id, {})
            
            if name not in tournaments:
                await channel.send(embed=EmbedBuilder.create_error_embed(
                    "Tournament Not Found",
                    f"Tournament `{name}` not found."
                ))
                return
                
            tournament = tournaments[name]
            
            # Get crew manager and crews
            crew_manager = self.get_crew_manager()
            if not crew_manager:
                await channel.send(embed=EmbedBuilder.create_error_embed(
                    "System Error",
                    "CrewManagement cog is not loaded. Cannot run tournament."
                ))
                return
                
            crews_dict = self.get_crews_for_guild(guild_id)
            if not crews_dict:
                await channel.send(embed=EmbedBuilder.create_error_embed(
                    "No Crews",
                    "No crews found for this server."
                ))
                return
    
            # Get participating crews
            participating_crews = []
            for crew_name in tournament["crews"]:
                if crew_name in crews_dict:
                    participating_crews.append(crews_dict[crew_name])
                else:
                    self.enhanced_logger.warning(f"Crew '{crew_name}' from tournament not found in crews_dict")
            
            if len(participating_crews) < 2:
                await channel.send(embed=EmbedBuilder.create_error_embed(
                    "Insufficient Crews",
                    "Not enough valid crews are participating in this tournament."
                ))
                return
            
            # Update tournament participation stats
            for crew_name in tournament["crews"]:
                if crew_name in crews_dict:
                    crew = crews_dict[crew_name]
                    if "stats" not in crew:
                        crew["stats"] = {"wins": 0, "losses": 0, "tournaments_won": 0, "tournaments_participated": 0}
                    crew["stats"]["tournaments_participated"] = crew["stats"].get("tournaments_participated", 0) + 1
            
            # Shuffle participating crews
            random.shuffle(participating_crews)
            
            # Send tournament start message
            crew_list = "\n".join([f"• {crew.get('emoji', '🏴‍☠️')} **{crew['name']}**" for crew in participating_crews])
            
            embed = EmbedBuilder.create_info_embed(
                f"🏆 Tournament: {name}",
                f"The tournament has begun with **{len(participating_crews)}** crews!"
            )
            embed.add_field(
                name="⚔️ Participating Crews",
                value=crew_list,
                inline=False
            )
            embed.color = 0xFFD700  # Gold color
            
            await channel.send(embed=embed)
            await asyncio.sleep(3)
            
            # Run tournament rounds
            round_number = 1
            remaining_crews = participating_crews.copy()
            
            while len(remaining_crews) > 1:
                # Announce the round
                round_embed = EmbedBuilder.create_info_embed(
                    f"🔥 Round {round_number}",
                    f"Round {round_number} of the tournament begins!"
                )
                await channel.send(embed=round_embed)
                await asyncio.sleep(2)
                
                # Pair crews and run matches
                new_remaining_crews = []
                pairs = []
                
                # Create pairs
                for i in range(0, len(remaining_crews), 2):
                    if i + 1 < len(remaining_crews):
                        pairs.append((remaining_crews[i], remaining_crews[i+1]))
                    else:
                        # If odd number of crews, give a bye to the last crew
                        new_remaining_crews.append(remaining_crews[i])
                        bye_embed = EmbedBuilder.create_info_embed(
                            "🎯 Bye Round",
                            f"{remaining_crews[i].get('emoji', '🏴‍☠️')} **{remaining_crews[i]['name']}** advances to the next round with a bye!"
                        )
                        await channel.send(embed=bye_embed)
                
                # Run each match in the round
                for crew1, crew2 in pairs:
                    await asyncio.sleep(2)
                    
                    # Announce match
                    match_embed = EmbedBuilder.create_info_embed(
                        "⚔️ Battle Match",
                        f"**{crew1.get('emoji', '🏴‍☠️')} {crew1['name']}** vs **{crew2.get('emoji', '🏴‍☠️')} {crew2['name']}**"
                    )
                    await channel.send(embed=match_embed)
                    
                    # Run the match
                    winner = await self.run_match(channel, crew1, crew2)
                    
                    if not winner:
                        self.enhanced_logger.error(f"Match between {crew1['name']} and {crew2['name']} failed to return a winner")
                        winner = crew1  # Default fallback
                        await channel.send(embed=EmbedBuilder.create_warning_embed(
                            "Match Error",
                            f"Error determining winner, defaulting to {crew1.get('emoji', '🏴‍☠️')} **{crew1['name']}**"
                        ))
                    
                    # Add winner to next round
                    new_remaining_crews.append(winner)
                    
                    # Update stats
                    loser = crew2 if winner == crew1 else crew1
                    
                    # Ensure stats dictionaries exist
                    for crew in [winner, loser]:
                        if "stats" not in crew:
                            crew["stats"] = {"wins": 0, "losses": 0, "tournaments_won": 0, "tournaments_participated": 0}
                    
                    winner["stats"]["wins"] = winner["stats"].get("wins", 0) + 1
                    loser["stats"]["losses"] = loser["stats"].get("losses", 0) + 1
                
                # Update remaining crews for next round
                remaining_crews = new_remaining_crews
                round_number += 1
                
                # Announce advancing crews
                if len(remaining_crews) > 1:
                    next_round_crews = "\n".join([f"• {crew.get('emoji', '🏴‍☠️')} **{crew['name']}**" for crew in remaining_crews])
                    
                    advance_embed = EmbedBuilder.create_success_embed(
                        f"Round {round_number-1} Complete",
                        f"The following crews advance to Round {round_number}:"
                    )
                    advance_embed.add_field(
                        name="🏃‍♂️ Advancing Crews",
                        value=next_round_crews,
                        inline=False
                    )
                    
                    await channel.send(embed=advance_embed)
                    await asyncio.sleep(3)
            
            # Tournament complete - we have a winner!
            if remaining_crews:
                winner = remaining_crews[0]
                
                # Update tournament win stats
                if "stats" not in winner:
                    winner["stats"] = {"wins": 0, "losses": 0, "tournaments_won": 0, "tournaments_participated": 0}
                
                winner["stats"]["tournaments_won"] = winner["stats"].get("tournaments_won", 0) + 1
                
                # Final announcement
                final_embed = discord.Embed(
                    title=f"🏆 TOURNAMENT CHAMPION 🏆",
                    description=f"{winner.get('emoji', '🏴‍☠️')} **{winner['name']}** has conquered the tournament!",
                    color=0xFFD700
                )
                
                # Show champion stats
                stats = winner['stats']
                final_embed.add_field(
                    name="🎯 Champion Statistics",
                    value=(
                        f"**Total Wins:** {stats.get('wins', 0)}\n"
                        f"**Total Losses:** {stats.get('losses', 0)}\n"
                        f"**Tournaments Won:** {stats.get('tournaments_won', 0)}\n"
                        f"**Tournaments Entered:** {stats.get('tournaments_participated', 0)}"
                    ),
                    inline=False
                )
                
                await channel.send(embed=final_embed)
                
                # Save updated crew statistics
                await crew_manager.save_crews(guild)
                
                self.enhanced_logger.log_crew_action(
                    "tournament_completed", guild.id,
                    tournament_name=name, winner_crew=winner['name']
                )
            else:
                await channel.send(embed=EmbedBuilder.create_error_embed(
                    "Tournament Error",
                    "No winner could be determined for the tournament."
                ))
            
            # Clean up tournament
            if name in tournaments:
                del tournaments[name]
                await self.save_tournaments(guild)
                
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "run_tournament", channel.guild.id,
                tournament_name=name, channel_id=channel.id
            )
            await channel.send(embed=EmbedBuilder.create_error_embed(
                "Tournament Error",
                "An error occurred during the tournament. Please contact an administrator."
            ))
        finally:
            # Always clean up, even if there's an error
            if channel.id in self.active_channels:
                self.active_channels.remove(channel.id)

    async def run_match(self, channel: discord.TextChannel, crew1: Dict[str, Any], crew2: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run an enhanced battle between two crews."""
        try:
            # Initialize battle data
            crews = [
                {
                    "name": crew1["name"], 
                    "emoji": crew1["emoji"], 
                    "hp": 100, 
                    "status": {"burn": 0, "stun": False}, 
                    "data": crew1
                },
                {
                    "name": crew2["name"], 
                    "emoji": crew2["emoji"], 
                    "hp": 100, 
                    "status": {"burn": 0, "stun": False}, 
                    "data": crew2
                },
            ]
            
            # Create the initial battle embed
            embed = EmbedBuilder.create_info_embed(
                "🏴‍☠️ Crew Battle ⚔️",
                f"Battle begins between **{crew1['emoji']} {crew1['name']}** and **{crew2['emoji']} {crew2['name']}**!"
            )
            embed.add_field(
                name="❤️ Health Status",
                value=(
                    f"**{crew1['emoji']} {crew1['name']}:** {self.generate_health_bar(100)} 100/100\n"
                    f"**{crew2['emoji']} {crew2['name']}:** {self.generate_health_bar(100)} 100/100"
                ),
                inline=False,
            )
            embed.color = 0xFF4444  # Red for battle
            
            message = await channel.send(embed=embed)
            
            turn_index = 0
            turn_count = 0
            max_turns = 25  # Prevent infinite battles
            
            # Battle loop
            while crews[0]["hp"] > 0 and crews[1]["hp"] > 0 and turn_count < max_turns:
                turn_count += 1
                attacker = crews[turn_index]
                defender = crews[1 - turn_index]
                
                # Apply burn damage at start of turn
                if defender["status"]["burn"] > 0:
                    burn_damage = 5 * defender["status"]["burn"]
                    defender["hp"] = max(0, defender["hp"] - burn_damage)
                    defender["status"]["burn"] -= 1
                    
                    burn_embed = EmbedBuilder.create_warning_embed(
                        "🔥 Burn Damage",
                        f"**{defender['emoji']} {defender['name']}** takes {burn_damage} burn damage!"
                    )
                    burn_embed.add_field(
                        name="❤️ Health Status",
                        value=(
                            f"**{crews[0]['emoji']} {crews[0]['name']}:** {self.generate_health_bar(crews[0]['hp'])} {crews[0]['hp']}/100\n"
                            f"**{crews[1]['emoji']} {crews[1]['name']}:** {self.generate_health_bar(crews[1]['hp'])} {crews[1]['hp']}/100"
                        ),
                        inline=False,
                    )
                    
                    await message.edit(embed=burn_embed)
                    await asyncio.sleep(2)
                    
                    # Check if defender died from burn
                    if defender["hp"] <= 0:
                        break
                
                # Skip turn if stunned
                if attacker["status"]["stun"]:
                    attacker["status"]["stun"] = False
                    
                    stun_embed = EmbedBuilder.create_warning_embed(
                        "⚡ Stunned",
                        f"**{attacker['emoji']} {attacker['name']}** is stunned and cannot act!"
                    )
                    await message.edit(embed=stun_embed)
                    await asyncio.sleep(2)
                    turn_index = 1 - turn_index
                    continue
                
                # Select a random move
                move = random.choice(self.MOVES)
                
                # Calculate damage
                damage = self.calculate_damage(move["type"])
                
                # Apply special effects
                effect_text = ""
                if move["effect"] == "burn" and random.random() < move.get("burn_chance", 0):
                    defender["status"]["burn"] += 1
                    effect_text = f"🔥 **{defender['emoji']} {defender['name']}** is set on fire!"
                elif move["effect"] == "stun" and random.random() < move.get("stun_chance", 0):
                    defender["status"]["stun"] = True
                    effect_text = f"⚡ **{defender['emoji']} {defender['name']}** is stunned!"
                    
                # Apply damage
                defender["hp"] = max(0, defender["hp"] - damage)
                
                # Create attack embed
                attack_embed = EmbedBuilder.create_info_embed(
                    f"⚔️ {move['name']}",
                    f"**{attacker['emoji']} {attacker['name']}** used **{move['name']}**!\n"
                    f"{move['description']} - **{damage}** damage dealt!"
                )
                
                if effect_text:
                    attack_embed.description += f"\n\n{effect_text}"
                    
                attack_embed.add_field(
                    name="❤️ Health Status",
                    value=(
                        f"**{crews[0]['emoji']} {crews[0]['name']}:** {self.generate_health_bar(crews[0]['hp'])} {crews[0]['hp']}/100\n"
                        f"**{crews[1]['emoji']} {crews[1]['name']}:** {self.generate_health_bar(crews[1]['hp'])} {crews[1]['hp']}/100"
                    ),
                    inline=False,
                )
                
                await message.edit(embed=attack_embed)
                await asyncio.sleep(3)
                
                # Switch turns
                turn_index = 1 - turn_index
            
            # Determine the winner
            winner = None
            if crews[0]["hp"] <= 0 and crews[1]["hp"] <= 0:
                # Both died - coin flip
                winner_index = random.randint(0, 1)
                winner = crews[winner_index]["data"]
                result_text = f"Both crews fall! 🎲 **{crews[winner_index]['emoji']} {crews[winner_index]['name']}** wins by luck!"
            elif crews[0]["hp"] <= 0:
                winner = crews[1]["data"]
                result_text = f"🏆 **{crews[1]['emoji']} {crews[1]['name']}** emerges victorious!"
            elif crews[1]["hp"] <= 0:
                winner = crews[0]["data"]
                result_text = f"🏆 **{crews[0]['emoji']} {crews[0]['name']}** emerges victorious!"
            else:
                # Time limit reached - higher HP wins
                if crews[0]["hp"] > crews[1]["hp"]:
                    winner = crews[0]["data"]
                    result_text = f"🏆 **{crews[0]['emoji']} {crews[0]['name']}** wins with superior health!"
                elif crews[1]["hp"] > crews[0]["hp"]:
                    winner = crews[1]["data"]
                    result_text = f"🏆 **{crews[1]['emoji']} {crews[1]['name']}** wins with superior health!"
                else:
                    # Equal HP - coin flip
                    winner_index = random.randint(0, 1)
                    winner = crews[winner_index]["data"]
                    result_text = f"Equal health! 🎲 **{crews[winner_index]['emoji']} {crews[winner_index]['name']}** wins by chance!"
            
            # Final result embed
            final_embed = EmbedBuilder.create_success_embed(
                "🏆 Battle Complete!",
                result_text
            )
            final_embed.add_field(
                name="📊 Final Health",
                value=(
                    f"**{crews[0]['emoji']} {crews[0]['name']}:** {crews[0]['hp']}/100\n"
                    f"**{crews[1]['emoji']} {crews[1]['name']}:** {crews[1]['hp']}/100"
                ),
                inline=False,
            )
            
            await message.edit(embed=final_embed)
            return winner
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "run_match", channel.guild.id,
                crew1_name=crew1['name'], crew2_name=crew2['name']
            )
            return crew1  # Default fallback

    def calculate_damage(self, move_type: str) -> int:
        """Calculate damage based on move type with enhanced logic."""
        if move_type == "regular":
            return random.randint(8, 15)  # Regular attacks: 8-15 damage
        elif move_type == "strong":
            return random.randint(12, 20)  # Strong attacks: 12-20 damage
        elif move_type == "critical":
            damage = random.randint(18, 28)  # Critical attacks: 18-28 damage
            if random.random() < 0.25:  # 25% chance of critical hit
                damage = int(damage * 1.5)  # Critical hit multiplier
            return damage
        else:
            return 5  # Default damage

    # Additional tournament commands...
    @tournament_commands.command(name="stats")
    async def tournament_stats(self, ctx, *, crew_name: str = None):
        """View tournament statistics for a crew."""
        try:
            # Validate setup
            finished_setup = await self.config.guild(ctx.guild).finished_setup()
            if not finished_setup:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Setup Required",
                    "Tournament system is not set up yet."
                ))
                return
                
            guild_id = str(ctx.guild.id)
            crews = self.get_crews_for_guild(guild_id)
            
            # If no crew specified, try to find user's crew or show overall stats
            if crew_name is None:
                user_crew = None
                for name, crew in crews.items():
                    if ctx.author.id in crew.get("members", []):
                        user_crew = name
                        break
                        
                if user_crew:
                    crew_name = user_crew
                else:
                    # Show overall tournament stats
                    tournaments = self.tournaments.get(guild_id, {})
                    active_tournaments = [t for t in tournaments.values() if not t.get("started", False)]
                    completed_tournaments = sum(1 for crew in crews.values() 
                                              if crew.get("stats", {}).get("tournaments_participated", 0) > 0)
                    
                    # Get top crews by tournament wins
                    crew_stats = []
                    for name, crew in crews.items():
                        stats = crew.get("stats", {})
                        tournaments_won = stats.get("tournaments_won", 0)
                        tournaments_participated = stats.get("tournaments_participated", 0)
                        if tournaments_participated > 0:
                            crew_stats.append((name, tournaments_won, tournaments_participated))
                    
                    crew_stats.sort(key=lambda x: x[1], reverse=True)
                    
                    embed = EmbedBuilder.create_info_embed(
                        "🏆 Tournament Statistics",
                        "Overall tournament statistics for this server"
                    )
                    
                    embed.add_field(
                        name="📊 Tournament Overview",
                        value=(
                            f"**Active Tournaments:** {len(active_tournaments)}\n"
                            f"**Total Crews with Tournament Experience:** {len(crew_stats)}"
                        ),
                        inline=False
                    )
                    
                    if crew_stats:
                        top_crews = crew_stats[:5]
                        top_crews_text = "\n".join([
                            f"• {crews[name]['emoji']} **{name}**: {wins} wins ({participated} entered)"
                            for name, wins, participated in top_crews
                        ])
                        
                        embed.add_field(
                            name="🥇 Top Tournament Performers",
                            value=top_crews_text,
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="🥇 Top Tournament Performers",
                            value="No tournament winners yet.",
                            inline=False
                        )
                    
                    await ctx.send(embed=embed)
                    return
            
            # Show specific crew stats
            if crew_name not in crews:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Crew Not Found",
                    f"No crew found with the name `{crew_name}`."
                ))
                return
                
            crew = crews[crew_name]
            stats = crew.get("stats", {})
            
            # Calculate statistics
            wins = stats.get("wins", 0)
            losses = stats.get("losses", 0)
            tournaments_won = stats.get("tournaments_won", 0)
            tournaments_participated = stats.get("tournaments_participated", 0)
            
            match_win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
            tourny_win_rate = (tournaments_won / tournaments_participated * 100) if tournaments_participated > 0 else 0
            
            embed = EmbedBuilder.create_crew_embed(
                f"{crew['emoji']} {crew_name} - Tournament Statistics",
                crew_name=crew_name
            )
            
            embed.add_field(
                name="🏆 Tournament Record",
                value=(
                    f"**Tournaments Won:** {tournaments_won}\n"
                    f"**Tournaments Entered:** {tournaments_participated}\n"
                    f"**Tournament Win Rate:** {tourny_win_rate:.1f}%"
                ),
                inline=True
            )
            
            embed.add_field(
                name="⚔️ Battle Record",
                value=(
                    f"**Battle Wins:** {wins}\n"
                    f"**Battle Losses:** {losses}\n"
                    f"**Battle Win Rate:** {match_win_rate:.1f}%"
                ),
                inline=True
            )
            
            # Performance rating
            if tournaments_participated > 0:
                if tourny_win_rate >= 50:
                    performance = "🔥 Dominant"
                elif tourny_win_rate >= 25:
                    performance = "⭐ Strong"
                elif tourny_win_rate >= 10:
                    performance = "📈 Improving"
                else:
                    performance = "🌱 Developing"
                    
                embed.add_field(
                    name="📊 Performance Rating",
                    value=performance,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "tournament_stats", ctx.guild.id, ctx.author.id,
                crew_name=crew_name
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Stats Failed",
                "An error occurred while loading tournament statistics."
            ))

    # Event listeners
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initialize data storage when bot joins a guild."""
        try:
            if str(guild.id) not in self.tournaments:
                self.tournaments[str(guild.id)] = {}
            
            self.enhanced_logger.log_system_event("tournament_guild_joined", guild_id=guild.id)
        except Exception as e:
            self.enhanced_logger.log_error_with_context(e, "on_guild_join", guild.id)

    # Test command
    @commands.command()
    async def tournamenttest(self, ctx):
        """Test if tournament commands are working."""
        embed = EmbedBuilder.create_success_embed(
            "Tournament System Test",
            "✅ Tournament system is loaded and working!"
        )
        embed.add_field(
            name="Available Commands",
            value=(
                "`tournysetup init` - Initialize tournament system\n"
                "`tourny create <name>` - Create a tournament\n"
                "`tourny list` - List tournaments"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    async def cog_unload(self):
        """Cleanup when cog is unloaded"""
        try:
            self.enhanced_logger.log_system_event("tournament_cog_unloaded")
        except Exception as e:
            print(f"Error during tournament cog unload: {e}")


async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(TournamentSystem(bot))
