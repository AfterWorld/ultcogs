import discord
from discord.ext import commands
from redbot.core import commands as red_commands, Config, checks
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.predicates import MessagePredicate
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import json

log = logging.getLogger("red.advancedreport")

class ReportView(discord.ui.View):
    """Interactive view with quick action buttons for staff"""
    
    def __init__(self, cog, report_data: dict, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.report_data = report_data
        self.processed = False
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only staff can use the buttons"""
        return await self.cog.is_staff_member(interaction.user, interaction.guild)
    
    @discord.ui.button(label="Mute", style=discord.ButtonStyle.secondary, emoji="🔇")
    async def mute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Mute the reported user"""
        try:
            reported_user = interaction.guild.get_member(self.report_data['reported_user_id'])
            if not reported_user:
                await interaction.response.send_message("❌ User not found in server", ephemeral=True)
                return
            
            # Get mute role or create timeout
            mute_role_id = await self.cog.config.guild(interaction.guild).mute_role()
            duration_minutes = await self.cog.config.guild(interaction.guild).default_mute_duration()
            
            if mute_role_id:
                mute_role = interaction.guild.get_role(mute_role_id)
                if mute_role:
                    await reported_user.add_roles(mute_role, reason=f"Report action by {interaction.user}")
                    action_text = f"Added mute role"
                else:
                    # Fallback to timeout
                    await reported_user.timeout(discord.utils.utcnow() + discord.timedelta(minutes=duration_minutes), 
                                              reason=f"Report action by {interaction.user}")
                    action_text = f"Timed out for {duration_minutes} minutes"
            else:
                # Use Discord's built-in timeout
                await reported_user.timeout(discord.utils.utcnow() + discord.timedelta(minutes=duration_minutes), 
                                           reason=f"Report action by {interaction.user}")
                action_text = f"Timed out for {duration_minutes} minutes"
            
            await self.update_report_status(interaction, f"🔇 {action_text}", discord.Color.orange())
            await self.log_action(interaction, "MUTE", action_text)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to mute this user", ephemeral=True)
        except Exception as e:
            log.exception("Error in mute button")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ban the reported user"""
        try:
            reported_user_id = self.report_data['reported_user_id']
            reason = f"Report action by {interaction.user} - Original report: {self.report_data['reason']}"
            
            await interaction.guild.ban(discord.Object(id=reported_user_id), 
                                       reason=reason, delete_message_days=1)
            
            await self.update_report_status(interaction, "🔨 User banned", discord.Color.red())
            await self.log_action(interaction, "BAN", "User banned from server")
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to ban this user", ephemeral=True)
        except Exception as e:
            log.exception("Error in ban button")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Caution", style=discord.ButtonStyle.primary, emoji="⚠️")
    async def caution_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Issue a caution using the Cautions cog system"""
        try:
            reported_user = interaction.guild.get_member(self.report_data['reported_user_id'])
            if not reported_user:
                await interaction.response.send_message("❌ User not found in server", ephemeral=True)
                return
            
            # Check if Cautions cog is loaded
            cautions_cog = self.cog.bot.get_cog("Cautions")
            if not cautions_cog:
                # Fallback to simple warning system
                await self._fallback_warning(interaction, reported_user)
                return
            
            # Create a caution using the Cautions cog system
            points = await self.cog.get_caution_points(interaction.guild)
            reason = f"Report: {self.report_data['reason']}"
            
            # Get warning expiry days from Cautions cog config
            expiry_days = await cautions_cog.config.guild(interaction.guild).warning_expiry_days()
            
            warning = {
                "points": points,
                "reason": reason,
                "moderator_id": interaction.user.id,
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "expiry": (datetime.now(timezone.utc) + timedelta(days=expiry_days)).timestamp()
            }
            
            # Add to member's warnings using Cautions cog structure
            member_config = cautions_cog.config.member(reported_user)
            async with member_config.warnings() as warnings_list:
                warnings_list.append(warning)
            
            # Update total points
            async with member_config.all() as member_data:
                member_data["total_points"] = sum(w.get("points", 1) for w in member_data["warnings"])
                total_points = member_data["total_points"]
            
            # Try to DM the user
            try:
                embed = discord.Embed(
                    title="⚠️ Caution Issued",
                    description=f"You have been cautioned in **{interaction.guild.name}**",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="Points", value=str(points), inline=True)
                embed.add_field(name="Total Points", value=str(total_points), inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                embed.add_field(name="Expires", value=f"<t:{int(warning['expiry'])}:R>", inline=True)
                embed.set_footer(text="Please follow the server rules to avoid further action")
                
                await reported_user.send(embed=embed)
                dm_status = "✅ User notified via DM"
            except discord.Forbidden:
                dm_status = "⚠️ Could not DM user"
            
            # Log the action using Cautions cog system
            await cautions_cog.log_action(
                interaction.guild, 
                "Caution", 
                reported_user, 
                interaction.user, 
                reason,
                extra_fields=[
                    {"name": "Points", "value": str(points)},
                    {"name": "Total Points", "value": str(total_points)},
                    {"name": "Report ID", "value": self.report_data.get('report_id', 'N/A')}
                ]
            )
            
            # Check if any action thresholds were reached
            await cautions_cog.check_action_thresholds(interaction, reported_user, total_points)
            
            await self.update_report_status(interaction, f"⚠️ Caution issued ({points} point) - Total: {total_points} - {dm_status}", discord.Color.yellow())
            await self.log_action(interaction, "CAUTION", f"Caution issued ({points} point) - Total: {total_points} - {dm_status}")
            
        except Exception as e:
            log.exception("Error in caution button")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def _fallback_warning(self, interaction: discord.Interaction, reported_user: discord.Member):
        """Fallback warning system if Cautions cog is not available"""
        try:
            # Store warning in our own config as fallback
            async with self.cog.config.member(reported_user).warnings() as warnings:
                warning_data = {
                    "reason": f"Report: {self.report_data['reason']}",
                    "moderator": interaction.user.id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "report_id": self.report_data.get('report_id', 'unknown')
                }
                warnings.append(warning_data)
            
            # Try to DM the user
            try:
                embed = discord.Embed(
                    title="⚠️ Warning Issued",
                    description=f"You have been warned in **{interaction.guild.name}**",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="Reason", value=self.report_data['reason'], inline=False)
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                embed.set_footer(text="Please follow the server rules to avoid further action")
                
                await reported_user.send(embed=embed)
                dm_status = "✅ User notified via DM"
            except discord.Forbidden:
                dm_status = "⚠️ Could not DM user"
            
            await self.update_report_status(interaction, f"⚠️ Warning issued - {dm_status} (Cautions cog not available)", discord.Color.yellow())
            await self.log_action(interaction, "WARN", f"Warning issued - {dm_status}")
            
        except Exception as e:
            log.exception("Error in fallback warning")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Blacklist Reporter", style=discord.ButtonStyle.secondary, emoji="🚫")
    async def blacklist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Blacklist the reporter for false reports"""
        try:
            async with self.cog.config.guild(interaction.guild).blacklisted_users() as blacklisted:
                if self.report_data['reporter_id'] not in blacklisted:
                    blacklisted.append(self.report_data['reporter_id'])
                    
                    await self.update_report_status(interaction, "🚫 Reporter blacklisted", discord.Color.dark_red())
                    await self.log_action(interaction, "BLACKLIST", "Reporter blacklisted for false reports")
                else:
                    await interaction.response.send_message("❌ Reporter is already blacklisted", ephemeral=True)
                    
        except Exception as e:
            log.exception("Error in blacklist button")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.success, emoji="✅")
    async def dismiss_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Dismiss the report"""
        try:
            await self.update_report_status(interaction, "✅ Report dismissed", discord.Color.green())
            await self.log_action(interaction, "DISMISS", "Report dismissed - no action taken")
            
        except Exception as e:
            log.exception("Error in dismiss button")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def update_report_status(self, interaction: discord.Interaction, status: str, color: discord.Color):
        """Update the report embed with action status"""
        if self.processed:
            await interaction.response.send_message("❌ This report has already been processed", ephemeral=True)
            return
            
        self.processed = True
        
        # Get original embed and update it
        original_embed = interaction.message.embeds[0] if interaction.message.embeds else None
        if original_embed:
            # Create new embed with updated status
            embed = discord.Embed(
                title=original_embed.title,
                description=original_embed.description,
                color=color
            )
            
            # Copy original fields
            for field in original_embed.fields:
                embed.add_field(name=field.name, value=field.value, inline=field.inline)
            
            # Add status field
            embed.add_field(name="📋 Status", value=status, inline=False)
            embed.add_field(name="🔧 Action by", value=interaction.user.mention, inline=True)
            embed.add_field(name="⏰ Processed at", 
                          value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>", inline=True)
            
            if original_embed.footer:
                embed.set_footer(text=original_embed.footer.text, icon_url=original_embed.footer.icon_url)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def log_action(self, interaction: discord.Interaction, action: str, details: str):
        """Log the moderation action"""
        log_channel_id = await self.cog.config.guild(interaction.guild).log_channel()
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title=f"📋 Report Action: {action}",
                    color=discord.Color.blue(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                embed.add_field(name="Action", value=details, inline=True)
                embed.add_field(name="Report ID", value=self.report_data.get('report_id', 'N/A'), inline=True)
                embed.add_field(name="Original Reason", value=self.report_data['reason'], inline=False)
                
                try:
                    await log_channel.send(embed=embed)
                except discord.Forbidden:
                    log.warning(f"Cannot send to log channel {log_channel_id}")

class AdvancedReport(red_commands.Cog):
    """Advanced reporting system with context menus and quick actions"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890987654321, force_registration=True)
        
        # Default settings
        self.config.register_guild(
            report_channel=None,
            staff_roles=[],
            ping_staff=True,
            log_channel=None,
            mute_role=None,
            default_mute_duration=60,  # minutes
            blacklisted_users=[],
            auto_thread=False,
            require_reason=True,
            default_caution_points=1  # For Cautions cog integration
        )
        
        self.config.register_member(
            warnings=[],
            report_count=0,
            total_points=0,  # For compatibility with Cautions cog
            applied_thresholds=[]  # For compatibility with Cautions cog
        )
        
        self.config.register_global(
            total_reports=0
        )
        
        # Add context menu commands
        self.bot.add_view(ReportView(self, {}))  # Persistent view
        
    async def cog_load(self):
        """Called when the cog is loaded"""
        log.info("AdvancedReport cog loaded successfully")
    
    async def cog_unload(self):
        """Called when the cog is unloaded"""
        log.info("AdvancedReport cog unloaded")
    
    async def is_staff_member(self, user: discord.Member, guild: discord.Guild) -> bool:
        """Check if user is a staff member"""
        if user.guild_permissions.administrator:
            return True
            
        staff_roles = await self.config.guild(guild).staff_roles()
        user_role_ids = [role.id for role in user.roles]
        return any(role_id in user_role_ids for role_id in staff_roles)
    
    async def is_blacklisted(self, user_id: int, guild: discord.Guild) -> bool:
        """Check if user is blacklisted from reporting"""
        blacklisted = await self.config.guild(guild).blacklisted_users()
        return user_id in blacklisted
    
    async def get_caution_points(self, guild: discord.Guild) -> int:
        """Get the configured caution points for this guild"""
        points = await self.config.guild(guild).default_caution_points()
        return max(1, min(10, points))  # Ensure it's between 1-10
    
    @red_commands.group(name="reportset", aliases=["rset"])
    @checks.admin_or_permissions(administrator=True)
    async def report_settings(self, ctx):
        """Configure the report system"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @report_settings.command(name="channel")
    async def set_report_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel where reports are sent"""
        if channel is None:
            channel = ctx.channel
        
        await self.config.guild(ctx.guild).report_channel.set(channel.id)
        await ctx.send(f"✅ Report channel set to {channel.mention}")
    
    @report_settings.command(name="staffroles")
    async def set_staff_roles(self, ctx, *roles: discord.Role):
        """Set the staff roles that can handle reports"""
        if not roles:
            await ctx.send("❌ Please specify at least one role")
            return
        
        role_ids = [role.id for role in roles]
        await self.config.guild(ctx.guild).staff_roles.set(role_ids)
        
        role_mentions = [role.mention for role in roles]
        await ctx.send(f"✅ Staff roles set to: {', '.join(role_mentions)}")
    
    @report_settings.command(name="logchannel")
    async def set_log_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for logging moderation actions"""
        if channel is None:
            channel = ctx.channel
        
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(f"✅ Log channel set to {channel.mention}")
    
    @report_settings.command(name="muterole")
    async def set_mute_role(self, ctx, role: discord.Role = None):
        """Set the mute role for quick mute actions"""
        if role:
            await self.config.guild(ctx.guild).mute_role.set(role.id)
            await ctx.send(f"✅ Mute role set to {role.mention}")
        else:
            await self.config.guild(ctx.guild).mute_role.clear()
            await ctx.send("✅ Mute role cleared - will use timeout instead")
    
    @report_settings.command(name="muteduration")
    async def set_mute_duration(self, ctx, minutes: int):
        """Set default mute duration in minutes"""
        if minutes < 1 or minutes > 40320:  # Discord max timeout is 28 days
            await ctx.send("❌ Duration must be between 1 and 40320 minutes (28 days)")
            return
        
        await self.config.guild(ctx.guild).default_mute_duration.set(minutes)
        await ctx.send(f"✅ Default mute duration set to {minutes} minutes")
    
    @report_settings.command(name="cautionpoints")
    async def set_caution_points(self, ctx, points: int = 1):
        """Set default caution points for reports (requires Cautions cog)"""
        if points < 1 or points > 10:
            await ctx.send("❌ Caution points must be between 1 and 10")
            return
        
        cautions_cog = self.bot.get_cog("Cautions")
        if not cautions_cog:
            await ctx.send("❌ Cautions cog is not loaded. This setting requires the Cautions cog.")
            return
        
        await self.config.guild(ctx.guild).default_caution_points.set(points)
        await ctx.send(f"✅ Default caution points for reports set to {points}")
    
    @report_settings.command(name="integration")
    async def check_integration(self, ctx):
        """Check integration status with other cogs"""
        embed = discord.Embed(
            title="🔗 Cog Integration Status",
            color=discord.Color.blue()
        )
        
        # Check Cautions cog
        cautions_cog = self.bot.get_cog("Cautions")
        if cautions_cog:
            embed.add_field(
                name="⚠️ Cautions Cog",
                value="✅ **Available** - Warning button will use the Cautions system",
                inline=False
            )
            
            # Get some stats from Cautions cog
            try:
                guild_config = await cautions_cog.config.guild(ctx.guild).all()
                expiry_days = guild_config.get('warning_expiry_days', 30)
                thresholds = guild_config.get('action_thresholds', {})
                
                embed.add_field(
                    name="📊 Cautions Settings",
                    value=f"Warning Expiry: {expiry_days} days\nAction Thresholds: {len(thresholds)} configured",
                    inline=True
                )
            except Exception as e:
                embed.add_field(
                    name="📊 Cautions Settings",
                    value=f"⚠️ Error reading settings: {str(e)}",
                    inline=True
                )
        else:
            embed.add_field(
                name="⚠️ Cautions Cog",
                value="❌ **Not Available** - Warning button will use fallback system",
                inline=False
            )
            embed.add_field(
                name="💡 Recommendation",
                value="Install the Cautions cog for advanced warning features with points, thresholds, and automatic actions.",
                inline=False
            )
        
        # Check Bank system
        try:
            from redbot.core import bank
            embed.add_field(
                name="💰 Bank System",
                value="✅ **Available** - Can integrate economy features if needed",
                inline=True
            )
        except ImportError:
            embed.add_field(
                name="💰 Bank System", 
                value="❌ **Not Available**",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @report_settings.command(name="view")
    async def view_settings(self, ctx):
        """View current report system settings"""
        settings = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(
            title="📋 Report System Settings",
            color=discord.Color.blue()
        )
        
        # Report channel
        report_channel = ctx.guild.get_channel(settings['report_channel'])
        embed.add_field(
            name="Report Channel",
            value=report_channel.mention if report_channel else "Not set",
            inline=True
        )
        
        # Staff roles
        staff_roles = [ctx.guild.get_role(role_id) for role_id in settings['staff_roles']]
        staff_roles = [role.mention for role in staff_roles if role]
        embed.add_field(
            name="Staff Roles",
            value=', '.join(staff_roles) if staff_roles else "Not set",
            inline=True
        )
        
        # Log channel
        log_channel = ctx.guild.get_channel(settings['log_channel'])
        embed.add_field(
            name="Log Channel",
            value=log_channel.mention if log_channel else "Not set",
            inline=True
        )
        
        # Mute settings
        mute_role = ctx.guild.get_role(settings['mute_role'])
        embed.add_field(
            name="Mute Role",
            value=mute_role.mention if mute_role else "Uses timeout",
            inline=True
        )
        
        embed.add_field(
            name="Mute Duration",
            value=f"{settings['default_mute_duration']} minutes",
            inline=True
        )
        
        embed.add_field(
            name="Caution Points",
            value=str(settings['default_caution_points']),
            inline=True
        )
        
        embed.add_field(
            name="Blacklisted Users",
            value=str(len(settings['blacklisted_users'])),
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @red_commands.command(name="report")
    async def report_command(self, ctx, user: discord.Member, *, reason: str):
        """Report a user to the staff team"""
        # Check if reporter is blacklisted
        if await self.is_blacklisted(ctx.author.id, ctx.guild):
            await ctx.send("❌ You are blacklisted from using the report system.", delete_after=10)
            try:
                await ctx.message.delete(delay=10)
            except discord.NotFound:
                pass
            return
        
        # Basic validation
        if user == ctx.author:
            await ctx.send("❌ You cannot report yourself!", delete_after=10)
            return
        
        if user.bot:
            await ctx.send("❌ You cannot report bots!", delete_after=10)
            return
        
        if await self.is_staff_member(user, ctx.guild):
            await ctx.send("❌ You cannot report staff members through this system!", delete_after=10)
            return
        
        await self.process_report(ctx.guild, ctx.author, user, reason, ctx.message, ctx.channel)
        
        # Delete the original report command for privacy
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        
        # Send confirmation to reporter
        try:
            await ctx.author.send(f"✅ Your report against **{user}** has been submitted to the staff team.")
        except discord.Forbidden:
            # If we can't DM, send a temporary message
            await ctx.send(f"✅ {ctx.author.mention}, your report has been submitted.", delete_after=10)
    
    @red_commands.command(name="reportmsg")
    async def report_message_command(self, ctx, message_id: int, *, reason: str):
        """Report a specific message by ID"""
        # Check if reporter is blacklisted  
        if await self.is_blacklisted(ctx.author.id, ctx.guild):
            await ctx.send("❌ You are blacklisted from using the report system.", delete_after=10)
            return
        
        # Find the message
        target_message = None
        for channel in ctx.guild.text_channels:
            try:
                target_message = await channel.fetch_message(message_id)
                break
            except (discord.NotFound, discord.Forbidden):
                continue
        
        if not target_message:
            await ctx.send("❌ Message not found!", delete_after=10)
            return
        
        if target_message.author == ctx.author:
            await ctx.send("❌ You cannot report your own message!", delete_after=10)
            return
        
        if target_message.author.bot:
            await ctx.send("❌ You cannot report bot messages!", delete_after=10)
            return
        
        if await self.is_staff_member(target_message.author, ctx.guild):
            await ctx.send("❌ You cannot report staff members!", delete_after=10)
            return
        
        await self.process_report(ctx.guild, ctx.author, target_message.author, reason, 
                                target_message, target_message.channel)
        
        # Clean up command message
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        
        # Confirm to reporter
        try:
            await ctx.author.send(f"✅ Your report against **{target_message.author}** has been submitted.")
        except discord.Forbidden:
            await ctx.send(f"✅ {ctx.author.mention}, your report has been submitted.", delete_after=10)
    
    @red_commands.command(name="reportcautions")
    async def check_user_cautions(self, ctx, user: discord.Member):
        """Check a user's cautions (integrates with Cautions cog if available)"""
        if not await self.is_staff_member(ctx.author, ctx.guild):
            await ctx.send("❌ Only staff members can check user cautions.")
            return
        
        cautions_cog = self.bot.get_cog("Cautions")
        if cautions_cog:
            # Use Cautions cog to get detailed information
            try:
                warnings = await cautions_cog.config.member(user).warnings()
                total_points = await cautions_cog.config.member(user).total_points()
                
                if not warnings:
                    await ctx.send(f"📊 {user.mention} has no active cautions.")
                    return
                
                embed = discord.Embed(
                    title=f"📊 Cautions for {user.display_name}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Total Points", value=str(total_points), inline=True)
                embed.add_field(name="Active Cautions", value=str(len(warnings)), inline=True)
                
                # Show recent cautions
                recent_cautions = warnings[-3:]  # Last 3 cautions
                for i, warning in enumerate(recent_cautions, 1):
                    moderator_id = warning.get("moderator_id")
                    moderator = ctx.guild.get_member(moderator_id) if moderator_id else None
                    moderator_name = moderator.display_name if moderator else "Unknown"
                    
                    timestamp = warning.get("timestamp", 0)
                    issued_time = f"<t:{int(timestamp)}:R>"
                    
                    value = f"**Points:** {warning.get('points', 1)}\n"
                    value += f"**Reason:** {warning.get('reason', 'No reason')[:100]}...\n"
                    value += f"**By:** {moderator_name} • {issued_time}"
                    
                    embed.add_field(name=f"Recent Caution #{i}", value=value, inline=False)
                
                if len(warnings) > 3:
                    embed.set_footer(text=f"Showing 3 most recent cautions. Use [p]cautions {user.mention} for full list.")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ Error accessing caution data: {str(e)}")
        else:
            # Fallback to our own warning system
            warnings = await self.config.member(user).warnings()
            if not warnings:
                await ctx.send(f"📊 {user.mention} has no warnings on record.")
                return
            
            embed = discord.Embed(
                title=f"📊 Warnings for {user.display_name}",
                color=discord.Color.orange()
            )
            embed.add_field(name="Total Warnings", value=str(len(warnings)), inline=True)
            
            # Show recent warnings
            recent_warnings = warnings[-3:]
            for i, warning in enumerate(recent_warnings, 1):
                moderator_id = warning.get("moderator")
                moderator = ctx.guild.get_member(moderator_id) if moderator_id else None
                moderator_name = moderator.display_name if moderator else "Unknown"
                
                timestamp = warning.get("timestamp", "Unknown")
                reason = warning.get("reason", "No reason")[:100]
                
                value = f"**Reason:** {reason}...\n"
                value += f"**By:** {moderator_name} • {timestamp}"
                
                embed.add_field(name=f"Recent Warning #{i}", value=value, inline=False)
            
            embed.set_footer(text="⚠️ Using fallback warning system - install Cautions cog for advanced features")
            await ctx.send(embed=embed)
    
    @red_commands.context_menu(name="Report Message")
    async def report_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        """Context menu command to report a message"""
        # Check if reporter is blacklisted
        if await self.is_blacklisted(interaction.user.id, interaction.guild):
            await interaction.response.send_message("❌ You are blacklisted from using the report system.", ephemeral=True)
            return
        
        # Validation
        if message.author == interaction.user:
            await interaction.response.send_message("❌ You cannot report your own message!", ephemeral=True)
            return
        
        if message.author.bot:
            await interaction.response.send_message("❌ You cannot report bot messages!", ephemeral=True)
            return
        
        if await self.is_staff_member(message.author, interaction.guild):
            await interaction.response.send_message("❌ You cannot report staff members!", ephemeral=True)
            return
        
        # Create modal for reason input
        modal = ReportModal(self, interaction.user, message.author, message, message.channel)
        await interaction.response.send_modal(modal)
    
    async def process_report(self, guild: discord.Guild, reporter: discord.User, 
                           reported_user: discord.User, reason: str, 
                           source_message: discord.Message, source_channel: discord.TextChannel):
        """Process and send the report to staff"""
        
        # Get report channel
        report_channel_id = await self.config.guild(guild).report_channel()
        if not report_channel_id:
            log.warning(f"No report channel set for guild {guild.id}")
            return
        
        report_channel = guild.get_channel(report_channel_id)
        if not report_channel:
            log.warning(f"Report channel {report_channel_id} not found in guild {guild.id}")
            return
        
        # Generate report ID
        report_count = await self.config.global.total_reports()
        report_count += 1
        await self.config.global.total_reports.set(report_count)
        report_id = f"RPT-{report_count:06d}"
        
        # Create report embed
        embed = discord.Embed(
            title="🚨 New User Report",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="📋 Report ID", value=f"`{report_id}`", inline=True)
        embed.add_field(name="👤 Reported User", value=f"{reported_user.mention}\n`{reported_user}` (ID: {reported_user.id})", inline=True)
        embed.add_field(name="👮 Reporter", value=f"{reporter.mention}\n`{reporter}` (ID: {reporter.id})", inline=True)
        
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.add_field(name="📍 Channel", value=source_channel.mention, inline=True)
        
        # Add message link if available
        if source_message:
            embed.add_field(name="🔗 Message Link", 
                          value=f"[Jump to Message]({source_message.jump_url})", inline=True)
            
            # Add message content preview
            if source_message.content:
                content_preview = source_message.content[:500]
                if len(source_message.content) > 500:
                    content_preview += "..."
                embed.add_field(name="💬 Message Content", value=f"```{content_preview}```", inline=False)
        
        embed.set_footer(text=f"Report submitted at")
        
        # Add reporter's avatar
        if reporter.avatar:
            embed.set_author(name=f"Report by {reporter}", icon_url=reporter.avatar.url)
        
        # Prepare report data for buttons
        report_data = {
            'report_id': report_id,
            'reporter_id': reporter.id,
            'reported_user_id': reported_user.id,
            'reason': reason,
            'guild_id': guild.id,
            'channel_id': source_channel.id,
            'message_id': source_message.id if source_message else None
        }
        
        # Create view with action buttons
        view = ReportView(self, report_data)
        
        # Get staff roles for pinging
        staff_roles = await self.config.guild(guild).staff_roles()
        ping_staff = await self.config.guild(guild).ping_staff()
        
        content = ""
        if ping_staff and staff_roles:
            staff_mentions = [f"<@&{role_id}>" for role_id in staff_roles]
            content = f"🚨 **Staff Alert**: New report requires attention\n{' '.join(staff_mentions)}"
        
        # Send the report
        try:
            report_message = await report_channel.send(content=content, embed=embed, view=view)
            
            # Update member report count
            current_count = await self.config.member_from_ids(guild.id, reporter.id).report_count()
            await self.config.member_from_ids(guild.id, reporter.id).report_count.set(current_count + 1)
            
            log.info(f"Report {report_id} sent to {report_channel.name} in {guild.name}")
            
        except discord.Forbidden:
            log.error(f"Cannot send report to channel {report_channel.id} in guild {guild.id}")
        except Exception as e:
            log.exception(f"Error sending report: {e}")

class ReportModal(discord.ui.Modal, title="Report User"):
    """Modal for collecting report reason"""
    
    def __init__(self, cog, reporter, reported_user, message, channel):
        super().__init__()
        self.cog = cog
        self.reporter = reporter
        self.reported_user = reported_user
        self.message = message
        self.channel = channel
    
    reason = discord.ui.TextInput(
        label="Reason for Report",
        placeholder="Please explain why you are reporting this user/message...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Your report has been submitted to the staff team.", ephemeral=True)
        
        await self.cog.process_report(
            interaction.guild,
            self.reporter,
            self.reported_user,
            self.reason.value,
            self.message,
            self.channel
        )

# Setup function for Red
async def setup(bot):
    cog = AdvancedReport(bot)
    await bot.add_cog(cog)
