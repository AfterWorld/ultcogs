"""
crewbattles/commands/setup.py - COMPLETE
Setup and initialization commands for the crew system
"""

import asyncio
import discord
from discord.ext import commands

from .utils import EmbedBuilder, PermissionUtils
from .ui import CrewButton


def setup_commands(cog_class):
    """Add setup commands to the CrewManagement cog"""
    
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
                    "`crewsetup reset` - Reset all crew data\n"
                    "`crewsetup roles` - Create role separators"
                ),
                inline=False
            )
            embed.add_field(
                name="🔧 Advanced Setup",
                value=(
                    "`crewsetup reorganize` - Reorganize crew roles\n"
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
                "✅ The crew system has been successfully initialized for this server.\n"
                "You can now create crews using `crew create`."
            )
            embed.add_field(
                name="Next Steps",
                value=(
                    "1. Run `crewsetup roles` to create role separators\n"
                    "2. Create crews with `crew create`\n"
                    "3. Use `crewsetup finish` to post crew selection interface"
                ),
                inline=False
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

    @crew_setup.command(name="reset")
    async def setup_reset(self, ctx):
        """Reset all crew data for this server."""
        try:
            # Confirmation check
            embed = EmbedBuilder.create_warning_embed(
                "Confirm Reset",
                "⚠️ **WARNING:** This will permanently delete ALL crew data for this server!\n\n"
                "This includes:\n"
                "• All crews and their members\n"
                "• All statistics and achievements\n"
                "• All crew roles (they will be deleted)\n\n"
                "**This action cannot be undone!**\n\n"
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
                    "Reset operation timed out. No data was deleted."
                ))
                return
            
            guild_id = str(ctx.guild.id)
            
            # Create backup before reset
            backup_success = await self.data_manager.create_backup(ctx.guild)
            
            # Count crews for logging
            crew_count = len(self.crews.get(guild_id, {})) if guild_id in self.crews else 0
            
            # Delete all crew roles
            if guild_id in self.crews:
                for crew_name, crew_data in self.crews[guild_id].items():
                    for role_key in ["captain_role", "vice_captain_role", "crew_role"]:
                        role_id = crew_data.get(role_key)
                        if role_id:
                            role = ctx.guild.get_role(role_id)
                            if role:
                                try:
                                    await role.delete()
                                except discord.Forbidden:
                                    pass  # Continue with reset
                                except Exception:
                                    pass  # Continue with reset
            
            # Clear data
            if guild_id in self.crews:
                self.crews[guild_id] = {}
            
            # Reset configuration
            await self.config.guild(ctx.guild).finished_setup.set(False)
            await self.config.guild(ctx.guild).separator_roles.clear()
            
            await self.save_data(ctx.guild)
            
            self.enhanced_logger.log_crew_action(
                "system_reset", ctx.guild.id, ctx.author.id, 
                crew_count=crew_count, backup_created=backup_success
            )
            
            embed = EmbedBuilder.create_success_embed(
                "Reset Complete",
                f"✅ All crew data has been reset for this server.\n"
                f"**{crew_count}** crews were deleted."
            )
            
            if backup_success:
                embed.add_field(
                    name="Backup Created",
                    value="A backup was created before the reset.",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "setup_reset", ctx.guild.id, ctx.author.id
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Reset Failed",
                "An error occurred while resetting crew data."
            ))

    @crew_setup.command(name="roles")
    async def setup_roles(self, ctx):
        """Create separator roles to organize crew roles in the role list."""
        try:
            guild = ctx.guild
            
            # Check permissions
            if not PermissionUtils.can_manage_crews(ctx.author):
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Insufficient Permissions",
                    "You need administrator permissions to create separator roles."
                ))
                return
            
            # Create separator roles
            top_separator = await guild.create_role(
                name="═════════ CREWS ═════════",
                color=discord.Color.dark_theme(),
                hoist=True,
                mentionable=False,
                reason="Crew system role separator"
            )
            
            bottom_separator = await guild.create_role(
                name="═════════════════════════",
                color=discord.Color.dark_theme(),
                mentionable=False,
                reason="Crew system role separator"
            )
            
            # Store separator role IDs in config
            await self.config.guild(guild).set_raw("separator_roles", value={
                "top": top_separator.id,
                "bottom": bottom_separator.id
            })
            
            self.enhanced_logger.log_crew_action(
                "separator_roles_created", guild.id, ctx.author.id,
                top_role_id=top_separator.id, bottom_role_id=bottom_separator.id
            )
            
            embed = EmbedBuilder.create_success_embed(
                "Separator Roles Created",
                "✅ Crew role separators have been created successfully!\n\n"
                "All future crew roles will be organized between these separators."
            )
            embed.add_field(
                name="Created Roles",
                value=f"🔼 {top_separator.mention}\n🔽 {bottom_separator.mention}",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Permission Denied",
                "I don't have permission to manage roles in this server."
            ))
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "setup_roles", ctx.guild.id, ctx.author.id
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Role Creation Failed",
                "An error occurred while creating separator roles."
            ))

    @crew_setup.command(name="reorganize")
    @commands.admin_or_permissions(administrator=True)
    async def reorganize_roles(self, ctx):
        """Reorganize all crew roles between separators."""
        try:
            guild = ctx.guild
            guild_id = str(guild.id)
            crews = self.crews.get(guild_id, {})
            
            if not crews:
                await ctx.send(embed=EmbedBuilder.create_warning_embed(
                    "No Crews Found",
                    "There are no crews to reorganize roles for."
                ))
                return
            
            # Check if separator roles exist
            separator_roles = await self.config.guild(guild).get_raw("separator_roles", default=None)
            if not separator_roles:
                await ctx.send(embed=EmbedBuilder.create_warning_embed(
                    "Separator Roles Missing",
                    "Separator roles don't exist. Creating them now..."
                ))
                await ctx.invoke(self.setup_roles)
                separator_roles = await self.config.guild(guild).get_raw("separator_roles", default={})
            
            top_separator = guild.get_role(separator_roles.get("top"))
            bottom_separator = guild.get_role(separator_roles.get("bottom"))
            
            if not top_separator or not bottom_separator:
                await ctx.send(embed=EmbedBuilder.create_error_embed(
                    "Separator Roles Not Found",
                    "Separator roles couldn't be found. Please run `crewsetup roles` first."
                ))
                return
            
            bottom_position = guild.roles.index(bottom_separator)
            
            # Collect all crew roles
            all_roles = []
            role_count = 0
            
            for crew_name, crew in crews.items():
                for role_key in ["captain_role", "vice_captain_role", "crew_role"]:
                    role_id = crew.get(role_key)
                    if role_id:
                        role = guild.get_role(role_id)
                        if role:
                            all_roles.append((role, crew_name))
                            role_count += 1
            
            if not all_roles:
                await ctx.send(embed=EmbedBuilder.create_warning_embed(
                    "No Roles to Reorganize",
                    "No crew roles were found to reorganize."
                ))
                return
            
            # Move all roles above the bottom separator
            moved_count = 0
            for role, crew_name in all_roles:
                try:
                    await role.edit(position=bottom_position + 1)
                    moved_count += 1
                except discord.Forbidden:
                    pass  # Continue with other roles
                except Exception:
                    pass  # Continue with other roles
            
            self.enhanced_logger.log_crew_action(
                "roles_reorganized", guild.id, ctx.author.id, 
                total_roles=role_count, moved_roles=moved_count
            )
            
            embed = EmbedBuilder.create_success_embed(
                "Roles Reorganized",
                f"✅ Successfully reorganized crew roles!\n\n"
                f"**{moved_count}** out of **{role_count}** roles were moved."
            )
            
            if moved_count < role_count:
                embed.add_field(
                    name="Note",
                    value="Some roles couldn't be moved due to permission restrictions.",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Permission Denied",
                "I don't have permission to manage roles in this server."
            ))
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "reorganize_roles", ctx.guild.id, ctx.author.id
            )
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Reorganization Failed",
                "An error occurred while reorganizing crew roles."
            ))

    @crew_setup.command(name="finish")
    async def setup_finish(self, ctx):
        """Finalizes crew setup and posts an interactive message for users to join crews."""
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
                    "No crews have been created yet. Create some crews first with `crew create`."
                ))
                return
            
            # Create header embed
            header_embed = EmbedBuilder.create_info_embed(
                "🏴‍☠️ Join a Crew Today! 🏴‍☠️",
                "Select a crew below to join. Choose wisely - you can't switch once you join!"
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
            
            await ctx.send(embed=header_embed)
            
            # Post each crew with detailed info and join buttons
            posted_crews = 0
            for crew_name, crew_data in crews.items():
                try:
                    # Create detailed crew embed
                    embed = await self._create_crew_join_embed(ctx.guild, crew_name, crew_data)
                    
                    # Create join button view
                    view = discord.ui.View(timeout=None)
                    join_button = CrewButton(crew_name, crew_data.get("emoji", "🏴‍☠️"), self)
                    view.add_item(join_button)
                    
                    await ctx.send(embed=embed, view=view)
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
                f"✅ Crew setup has been finalized!\n\n"
                f"**{posted_crews}** crew selection interfaces have been posted.\n"
                f"Users can now join crews using the buttons above or by using the `crew join` command."
            )
            completion_embed.add_field(
                name="Available Commands",
                value=(
                    "`crew join <name>` - Join a specific crew\n"
                    "`crew list` - View all available crews\n"
                    "`crew view <name>` - View detailed crew information"
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
                "An error occurred while finalizing crew setup."
            ))

    async def _create_crew_join_embed(self, guild: discord.Guild, crew_name: str, crew_data: dict) -> discord.Embed:
        """Create an enhanced embed for crew joining interface"""
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
            total_battles = wins + losses
            win_rate = (wins / total_battles * 100) if total_battles > 0 else 0.0
            
            # Create embed
            embed = discord.Embed(
                title=f"{emoji} {crew_name} [{tag}]",
                description="Click the button below to join this crew!",
                color=discord.Color.blue()
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
                name="📊 Statistics",
                value=(
                    f"**Win Rate:** {win_rate:.1f}%\n"
                    f"**Battles:** {total_battles}\n"
                    f"**Wins:** {wins}\n"
                    f"**Losses:** {losses}"
                ),
                inline=True
            )
            
            # Add special traits or description if available
            description = crew_data.get('description', 'A mighty crew ready for battle!')
            embed.add_field(
                name="⚡ About",
                value=description,
                inline=False
            )
            
            # Add footer with join instructions
            embed.set_footer(text="🔘 Click the button below to join this crew!")
            
            return embed
            
        except Exception as e:
            self.enhanced_logger.log_error_with_context(
                e, "_create_crew_join_embed", guild.id, crew_name=crew_name
            )
            # Return a basic fallback embed
            return EmbedBuilder.create_info_embed(
                f"{crew_data.get('emoji', '🏴‍☠️')} {crew_name}",
                "Click the button below to join this crew!"
            )

    @crew_setup.command(name="status")
    async def setup_status(self, ctx):
        """Show the current status of the crew system setup."""
        try:
            guild_id = str(ctx.guild.id)
            
            # Check setup status
            finished_setup = await self.config.guild(ctx.guild).finished_setup()
            separator_roles = await self.config.guild(ctx.guild).get_raw("separator_roles", default=None)
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
            
            # Role separator status
            separator_status = "✅ Created" if separator_roles else "❌ Not Created"
            embed.add_field(
                name="📋 Role Separators",
                value=f"**Status:** {separator_status}",
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
            if not separator_roles:
                next_steps.append("• Run `crewsetup roles` to create role separators")
            if not crews:
                next_steps.append("• Create crews with `crew create`")
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
            
            # Data directory status
            data_status = []
            if hasattr(self, 'data_manager'):
                crews_dir_exists = self.data_manager.crews_dir.exists()
                backup_dir_exists = self.data_manager.backup_dir.exists()
                data_status.append(f"**Crews Directory:** {'✅' if crews_dir_exists else '❌'}")
                data_status.append(f"**Backup Directory:** {'✅' if backup_dir_exists else '❌'}")
                
                embed.add_field(
                    name="💾 Data Storage",
                    value="\n".join(data_status),
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

    # Add all commands to the cog class
    cog_class.crew_setup = crew_setup
    cog_class.setup_init = setup_init
    cog_class.setup_reset = setup_reset
    cog_class.setup_roles = setup_roles
    cog_class.reorganize_roles = reorganize_roles
    cog_class.setup_finish = setup_finish
    cog_class._create_crew_join_embed = _create_crew_join_embed
    cog_class.setup_status = setup_status
    
    return cog_class