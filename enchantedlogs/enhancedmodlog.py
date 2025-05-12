import discord
import datetime
import asyncio
from typing import Dict, List, Optional, Union, Literal

from redbot.core import commands, Config, modlog
from redbot.core.utils.chat_formatting import humanize_list, pagify, box
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n

_ = Translator("EnhancedModlog", __file__)

class EnhancedModlog(commands.Cog):
    """
    Enhanced moderation logs with embeds and interactive components.
    
    This cog creates enhanced moderation logs with interactive buttons, allowing
    for quick moderation actions directly from the log channel.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9238472399876, force_registration=True)
        
        default_guild = {
            "log_channel": None,
            "enabled": False,
            "include_reason": True,
            "include_moderator": True,
            "buttons_enabled": True,
            "action_colors": {
                "ban": 0xCB2C31,      # Red
                "unban": 0x5BC0DE,    # Light Blue
                "kick": 0xF0AD4E,     # Orange
                "mute": 0x7F7F7F,     # Grey
                "unmute": 0x5BC0DE,   # Light Blue
                "warn": 0xF5F5F5,     # White
                "voicemute": 0x62717b, # Dark Grey
                "voiceunmute": 0x5BC0DE, # Light Blue
                "role_update": 0x9B59B6, # Purple
                "default": 0x4A90E2   # Blue
            }
        }
        
        self.config.register_guild(**default_guild)
        # Keep track of recently processed cases to avoid duplicates
        self.recently_processed_cases = {}
        self._task = self.bot.loop.create_task(self._init_task())
        
    def cog_unload(self):
        if self._task:
            self._task.cancel()
            
    async def _init_task(self):
        await self.bot.wait_until_ready()
        # Ensure modlog is loaded
        if not self.bot.get_cog("ModLog"):
            self.bot.logger.error("ModLog cog is required for EnhancedModlog to work.")

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        """Nothing to delete, moderation data is essential"""
        pass
    
    @commands.group()
    @commands.admin_or_permissions(administrator=True)
    @commands.guild_only()
    async def enhancedmodlog(self, ctx: commands.Context):
        """Settings for enhanced moderation logs."""
        pass

    @enhancedmodlog.command(name="channel")
    async def set_log_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set the channel for enhanced modlogs.
        
        If channel is not provided, enhanced modlogs will be disabled.
        """
        if channel:
            if not channel.permissions_for(ctx.guild.me).send_messages:
                return await ctx.send(_("I don't have permission to send messages in that channel."))
            
            if not channel.permissions_for(ctx.guild.me).embed_links:
                return await ctx.send(_("I don't have permission to embed links in that channel."))
            
            await self.config.guild(ctx.guild).log_channel.set(channel.id)
            await self.config.guild(ctx.guild).enabled.set(True)
            await ctx.send(_(f"Enhanced modlogs will now be sent to {channel.mention}"))
        else:
            await self.config.guild(ctx.guild).enabled.set(False)
            await ctx.send(_("Enhanced modlogs have been disabled."))

    @enhancedmodlog.command(name="buttons")
    async def toggle_buttons(self, ctx: commands.Context, enabled: bool = None):
        """Toggle interactive buttons on the modlog embeds.
        
        If not specified, shows the current setting.
        """
        if enabled is None:
            current = await self.config.guild(ctx.guild).buttons_enabled()
            return await ctx.send(
                _("Interactive buttons are currently {state}.").format(
                    state=_("enabled") if current else _("disabled")
                )
            )
        
        await self.config.guild(ctx.guild).buttons_enabled.set(enabled)
        if enabled:
            await ctx.send(_("Interactive buttons are now enabled on modlog embeds."))
        else:
            await ctx.send(_("Interactive buttons are now disabled on modlog embeds."))

    @enhancedmodlog.command(name="settings")
    async def show_settings(self, ctx: commands.Context):
        """Show the current enhanced modlog settings."""
        guild_data = await self.config.guild(ctx.guild).all()
        channel = ctx.guild.get_channel(guild_data["log_channel"])
        
        if channel:
            channel_info = f"#{channel.name} ({channel.id})"
        else:
            channel_info = "Not set"
        
        settings_message = _(
            "**Enhanced Modlog Settings**\n\n"
            "Enabled: {enabled}\n"
            "Log Channel: {channel}\n"
            "Interactive Buttons: {buttons}\n"
            "Include Reason: {reason}\n"
            "Include Moderator: {moderator}\n"
        ).format(
            enabled=guild_data["enabled"],
            channel=channel_info,
            buttons=guild_data["buttons_enabled"],
            reason=guild_data["include_reason"],
            moderator=guild_data["include_moderator"],
        )
        
        await ctx.send(settings_message)

    @commands.Cog.listener()
    async def on_modlog_case_create(self, case):
        """Listener for modlog case creation"""
        guild = case.guild
        
        # Check if enhanced modlogs are enabled for this guild
        guild_settings = await self.config.guild(guild).all()
        if not guild_settings["enabled"]:
            return
            
        # Check if the log channel exists
        log_channel_id = guild_settings["log_channel"]
        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        # Check if we've already processed this case recently (to avoid duplicates)
        case_key = f"{guild.id}_{case.case_number}"
        if case_key in self.recently_processed_cases:
            return
            
        self.recently_processed_cases[case_key] = True
        
        # Clean up the recently processed cases dict periodically
        self.bot.loop.call_later(60, lambda: self.recently_processed_cases.pop(case_key, None))
        
        # Generate and send the enhanced modlog embed
        embed = await self._generate_case_embed(case, guild_settings)
        view = await self._create_action_view(case) if guild_settings["buttons_enabled"] else None
        
        try:
            await log_channel.send(embed=embed, view=view)
        except discord.HTTPException as e:
            self.bot.logger.error(f"Failed to send enhanced modlog message: {e}")

    async def _generate_case_embed(self, case, guild_settings):
        """Generate an enhanced embed for a modlog case"""
        action_type = case.action_type
        colors = guild_settings["action_colors"]
        color = colors.get(action_type, colors["default"])
        
        embed = discord.Embed(
            title=f"Case #{case.case_number} | {case.action_type.title()}",
            color=color,
            timestamp=datetime.datetime.fromtimestamp(case.created_at)
        )
        
        # Add user info
        user = case.user
        if user:
            embed.set_author(name=f"{user} ({user.id})", icon_url=user.display_avatar.url)
        else:
            embed.set_author(name="Unknown User")
        
        # Add moderator info if enabled
        if guild_settings["include_moderator"] and case.moderator:
            embed.add_field(name="Moderator", value=f"{case.moderator.mention} ({case.moderator})", inline=True)
        
        # Add reason if enabled
        if guild_settings["include_reason"] and case.reason:
            embed.add_field(name="Reason", value=case.reason or "No reason provided", inline=False)
            
        # Add channel info if available
        if case.channel:
            embed.add_field(name="Channel", value=case.channel.mention, inline=True)
            
        # Add duration info for temporary actions
        if hasattr(case, "until") and case.until:
            time_remaining = case.until - datetime.datetime.utcnow()
            if time_remaining.total_seconds() > 0:
                duration_text = self._format_timedelta(time_remaining)
                embed.add_field(name="Duration", value=duration_text, inline=True)
                embed.add_field(name="Expires", value=f"<t:{int(case.until.timestamp())}:R>", inline=True)
                
        # Add footer with case ID for reference
        embed.set_footer(text=f"Case #{case.case_number}")
        
        return embed
    
    async def _create_action_view(self, case):
        """Create interactive buttons for the modlog case"""
        view = discord.ui.View(timeout=None)
        
        # Add appropriate action buttons based on case type
        if case.action_type == "ban":
            button = discord.ui.Button(
                label="Unban User", 
                style=discord.ButtonStyle.success,
                custom_id=f"enhanced_modlog:unban:{case.guild.id}:{case.user.id}:{case.case_number}"
            )
            view.add_item(button)
            
        elif case.action_type == "mute":
            button = discord.ui.Button(
                label="Unmute User", 
                style=discord.ButtonStyle.success,
                custom_id=f"enhanced_modlog:unmute:{case.guild.id}:{case.user.id}:{case.case_number}"
            )
            view.add_item(button)
            
        elif case.action_type == "voicemute":
            button = discord.ui.Button(
                label="Voice Unmute", 
                style=discord.ButtonStyle.success,
                custom_id=f"enhanced_modlog:voiceunmute:{case.guild.id}:{case.user.id}:{case.case_number}"
            )
            view.add_item(button)
            
        # Add "View User Modlogs" button to all cases
        modlogs_button = discord.ui.Button(
            label="View User Modlogs", 
            style=discord.ButtonStyle.secondary,
            custom_id=f"enhanced_modlog:modlogs:{case.guild.id}:{case.user.id}:{case.case_number}"
        )
        view.add_item(modlogs_button)
        
        return view

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions from modlog embeds"""
        if not interaction.data or not interaction.data.get("custom_id", "").startswith("enhanced_modlog:"):
            return
            
        # Parse the custom ID
        custom_id = interaction.data["custom_id"]
        parts = custom_id.split(":")
        
        if len(parts) < 5:
            return
            
        action_type = parts[1]
        guild_id = int(parts[2])
        user_id = int(parts[3])
        case_number = int(parts[4])
        
        # Check if the user has appropriate permissions
        if not interaction.user.guild_permissions.ban_members and not await self.bot.is_mod(interaction.user):
            return await interaction.response.send_message(
                "You don't have permission to use this button.", ephemeral=True
            )
            
        # Handle different action types
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await interaction.response.send_message(
                "I can't find the server for this action.", ephemeral=True
            )
            
        if action_type == "unban":
            # Perform unban action
            try:
                await guild.unban(discord.Object(id=user_id), reason=f"Unbanned by {interaction.user} via modlog")
                await interaction.response.send_message(
                    f"User <@{user_id}> has been unbanned.", ephemeral=True
                )
                
                # Create a new modlog case for the unban
                await modlog.create_case(
                    self.bot,
                    guild,
                    datetime.datetime.now(),
                    "unban",
                    discord.Object(id=user_id),
                    interaction.user,
                    f"Unbanned via modlog button by {interaction.user}",
                    until=None,
                )
            except discord.NotFound:
                await interaction.response.send_message(
                    f"User with ID {user_id} is not banned.", ephemeral=True
                )
            except discord.HTTPException as e:
                await interaction.response.send_message(
                    f"Failed to unban user: {e}", ephemeral=True
                )
                
        elif action_type == "unmute":
            # Get mute role from Mutes cog if available
            mutes_cog = self.bot.get_cog("Mutes")
            mute_role = None
            member = guild.get_member(user_id)
            
            if not member:
                return await interaction.response.send_message(
                    f"User with ID {user_id} is not in the server anymore.", ephemeral=True
                )
                
            if mutes_cog:
                mute_role_id = await mutes_cog.config.guild(guild).role()
                mute_role = guild.get_role(mute_role_id)
                
            if not mute_role:
                return await interaction.response.send_message(
                    "I couldn't find the mute role configuration.", ephemeral=True
                )
                
            # Perform unmute action
            try:
                await member.remove_roles(mute_role, reason=f"Unmuted by {interaction.user} via modlog")
                await interaction.response.send_message(
                    f"{member.mention} has been unmuted.", ephemeral=True
                )
                
                # Create a new modlog case for the unmute
                await modlog.create_case(
                    self.bot,
                    guild,
                    datetime.datetime.now(),
                    "unmute",
                    member,
                    interaction.user,
                    f"Unmuted via modlog button by {interaction.user}",
                    until=None,
                )
            except discord.HTTPException as e:
                await interaction.response.send_message(
                    f"Failed to unmute user: {e}", ephemeral=True
                )
                
        elif action_type == "voiceunmute":
            member = guild.get_member(user_id)
            
            if not member:
                return await interaction.response.send_message(
                    f"User with ID {user_id} is not in the server anymore.", ephemeral=True
                )
                
            if not member.voice:
                return await interaction.response.send_message(
                    f"{member.mention} is not in a voice channel.", ephemeral=True
                )
                
            # Perform voice unmute action
            try:
                await member.edit(mute=False, reason=f"Voice unmuted by {interaction.user} via modlog")
                await interaction.response.send_message(
                    f"{member.mention} has been voice unmuted.", ephemeral=True
                )
                
                # Create a new modlog case for the voice unmute
                await modlog.create_case(
                    self.bot,
                    guild,
                    datetime.datetime.now(),
                    "voiceunmute",
                    member,
                    interaction.user,
                    f"Voice unmuted via modlog button by {interaction.user}",
                    until=None,
                )
            except discord.HTTPException as e:
                await interaction.response.send_message(
                    f"Failed to voice unmute user: {e}", ephemeral=True
                )
                
        elif action_type == "modlogs":
            # Show user modlogs in an ephemeral message
            modlog_cog = self.bot.get_cog("ModLog")
            if not modlog_cog:
                return await interaction.response.send_message(
                    "The ModLog cog is not loaded.", ephemeral=True
                )
                
            try:
                cases = await modlog.get_cases_for_member(self.bot, guild, user_id=user_id)
                
                if not cases:
                    return await interaction.response.send_message(
                        f"No modlog cases found for <@{user_id}>.", ephemeral=True
                    )
                    
                # Format cases into an embed
                user = await self.bot.fetch_user(user_id)
                embed = discord.Embed(
                    title=f"Modlog Cases for {user}",
                    color=discord.Color.blue(),
                    description=f"Total cases: {len(cases)}"
                )
                embed.set_thumbnail(url=user.display_avatar.url)
                
                # Format cases into field groups by type
                case_groups = {}
                for case in cases:
                    if case.action_type not in case_groups:
                        case_groups[case.action_type] = []
                    case_groups[case.action_type].append(case)
                
                for action_type, case_list in case_groups.items():
                    case_count = len(case_list)
                    latest_cases = sorted(case_list, key=lambda c: c.case_number, reverse=True)[:3]
                    
                    field_value = f"{case_count} total\n"
                    for case in latest_cases:
                        reason = case.reason[:50] + "..." if case.reason and len(case.reason) > 50 else case.reason or "No reason"
                        field_value += f"• #{case.case_number}: {reason}\n"
                        
                    if case_count > 3:
                        field_value += f"• ... and {case_count - 3} more\n"
                        
                    embed.add_field(
                        name=f"{action_type.title()}",
                        value=field_value,
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except discord.HTTPException as e:
                await interaction.response.send_message(
                    f"Failed to retrieve modlog cases: {e}", ephemeral=True
                )
    
    def _format_timedelta(self, delta):
        """Format a timedelta into a human-readable string"""
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        
        parts = []
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            
        if not parts:
            return "less than a minute"
            
        return ", ".join(parts)


async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(EnhancedModlog(bot))
