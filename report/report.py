# report.py - Main cog file
import discord
from discord.ext import commands
from redbot.core import commands as red_commands, Config, checks
from redbot.core.utils.chat_formatting import box, humanize_timedelta
from redbot.core.utils.predicates import MessagePredicate
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Union
import re

log = logging.getLogger("red.ultcogs.report")


class ReportView(discord.ui.View):
    """Quick action buttons for staff on reports"""
    
    def __init__(self, cog, reported_user: discord.Member, reporter: discord.Member, 
                 original_message: Optional[discord.Message] = None):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.cog = cog
        self.reported_user = reported_user
        self.reporter = reporter
        self.original_message = original_message
        self.handled_by = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only staff can use these buttons"""
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "❌ You don't have permission to handle reports.", 
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label="Caution", style=discord.ButtonStyle.primary, emoji="⚠️")
    async def caution_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a caution/warning to the reported user via Cautions cog"""
        try:
            # Get the Cautions cog
            cautions_cog = self.cog.bot.get_cog("Cautions")
            if not cautions_cog:
                await interaction.response.send_message(
                    "❌ Cautions cog not loaded. Please load it first with `[p]load cautions`", 
                    ephemeral=True
                )
                return
            
            # Create a modal for caution details
            class CautionModal(discord.ui.Modal, title="Add Caution"):
                def __init__(self, view_instance):
                    super().__init__()
                    self.view_instance = view_instance
                
                points = discord.ui.TextInput(
                    label="Warning Points",
                    placeholder="Enter number of points (default: 1)",
                    default="1",
                    max_length=2,
                    required=False
                )
                
                reason = discord.ui.TextInput(
                    label="Reason for Caution",
                    placeholder="Enter the reason for this warning...",
                    style=discord.TextStyle.paragraph,
                    max_length=500,
                    required=True
                )
                
                async def on_submit(self, interaction: discord.Interaction):
                    try:
                        # Validate points
                        try:
                            point_value = int(self.points.value) if self.points.value.strip() else 1
                            if point_value < 1:
                                point_value = 1
                        except ValueError:
                            point_value = 1
                        
                        # Validate reason
                        caution_reason = await self.view_instance.cog.validate_input(self.reason.value, 500)
                        
                        # Add the warning using Cautions cog functionality
                        await self.add_caution_to_user(interaction, point_value, caution_reason)
                        
                    except Exception as e:
                        log.error(f"Error in caution modal: {e}")
                        await interaction.response.send_message(
                            "❌ An error occurred while adding the caution.", 
                            ephemeral=True
                        )
                
                async def add_caution_to_user(self, interaction, points, reason):
                    """Add caution using the Cautions cog logic"""
                    cautions_cog = self.view_instance.cog.bot.get_cog("Cautions")
                    member = self.view_instance.reported_user
                    
                    # Get warning expiry days from Cautions cog config
                    expiry_days = await cautions_cog.config.guild(interaction.guild).warning_expiry_days()
                    
                    # Create warning data structure
                    warning = {
                        "points": points,
                        "reason": reason,
                        "moderator_id": interaction.user.id,
                        "timestamp": datetime.utcnow().timestamp(),
                        "expiry": (datetime.utcnow() + timedelta(days=expiry_days)).timestamp()
                    }
                    
                    # Add warning to member's record
                    member_config = cautions_cog.config.member(member)
                    async with member_config.warnings() as warnings:
                        warnings.append(warning)
                    
                    # Update total points
                    async with member_config.all() as member_data:
                        member_data["total_points"] = sum(w.get("points", 1) for w in member_data["warnings"])
                        total_points = member_data["total_points"]
                    
                    # Create response embed
                    embed = discord.Embed(
                        title="✅ Caution Added",
                        description=f"{member.mention} has been given a caution via report system.",
                        color=discord.Color.orange(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.add_field(name="Points Added", value=str(points), inline=True)
                    embed.add_field(name="Total Points", value=str(total_points), inline=True)
                    embed.add_field(name="Reason", value=reason, inline=False)
                    embed.set_footer(text=f"Handled by {interaction.user}")
                    
                    await interaction.response.edit_message(embed=embed, view=None)
                    self.view_instance.handled_by = interaction.user
                    
                    # Log the caution using Cautions cog logging
                    await cautions_cog.log_action(
                        interaction.guild, 
                        "Warning", 
                        member, 
                        interaction.user, 
                        reason,
                        extra_fields=[
                            {"name": "Points", "value": str(points)},
                            {"name": "Total Points", "value": str(total_points)},
                            {"name": "Via", "value": "Report System"}
                        ]
                    )
                    
                    # Check thresholds using Cautions cog logic
                    await self.check_caution_thresholds(interaction, member, total_points, cautions_cog)
                
                async def check_caution_thresholds(self, interaction, member, total_points, cautions_cog):
                    """Check and apply threshold actions from Cautions cog"""
                    try:
                        thresholds = await cautions_cog.config.guild(interaction.guild).action_thresholds()
                        
                        # Get thresholds that match or are lower than current points
                        matching_thresholds = []
                        for threshold_points, action_data in thresholds.items():
                            if int(threshold_points) <= total_points:
                                matching_thresholds.append((int(threshold_points), action_data))
                        
                        if matching_thresholds:
                            # Sort by threshold value (descending) to get highest matching threshold
                            matching_thresholds.sort(key=lambda x: x[0], reverse=True)
                            threshold_points, action_data = matching_thresholds[0]
                            
                            # Get applied thresholds to prevent duplicate actions
                            applied_thresholds = await cautions_cog.config.member(member).applied_thresholds()
                            
                            # Check if this threshold has already been applied
                            if threshold_points not in applied_thresholds:
                                # Mark this threshold as applied
                                applied_thresholds.append(threshold_points)
                                await cautions_cog.config.member(member).applied_thresholds.set(applied_thresholds)
                                
                                # Apply the threshold action
                                await self.apply_threshold_action(interaction, member, action_data, cautions_cog)
                    
                    except Exception as e:
                        log.error(f"Error checking caution thresholds: {e}")
                
                async def apply_threshold_action(self, interaction, member, action_data, cautions_cog):
                    """Apply threshold action using Cautions cog logic"""
                    action = action_data["action"]
                    reason = action_data.get("reason", "Warning threshold exceeded")
                    duration = action_data.get("duration")
                    
                    try:
                        if action == "mute":
                            # Use Cautions cog mute logic
                            mute_role_id = await cautions_cog.config.guild(interaction.guild).mute_role()
                            if not mute_role_id:
                                await interaction.followup.send(
                                    f"⚠️ Threshold reached for {action} but no mute role is configured. "
                                    f"Please set up with `[p]setupmute`",
                                    ephemeral=True
                                )
                                return
                            
                            mute_role = interaction.guild.get_role(mute_role_id)
                            if not mute_role:
                                await interaction.followup.send(
                                    f"⚠️ Mute role not found. Please reconfigure with `[p]setupmute`",
                                    ephemeral=True
                                )
                                return
                            
                            # Set muted_until time if duration provided
                            if duration:
                                muted_until = datetime.utcnow() + timedelta(minutes=duration)
                                await cautions_cog.config.member(member).muted_until.set(muted_until.timestamp())
                            
                            # Apply mute role
                            await member.add_roles(mute_role, reason=reason)
                            
                            # Also apply timeout as backup
                            if duration:
                                timeout_duration = timedelta(minutes=duration)
                                await member.timeout(timeout_duration, reason=reason)
                            
                            await interaction.followup.send(
                                f"🔇 {member.mention} has been automatically muted for {duration} minutes due to reaching warning threshold.",
                                ephemeral=True
                            )
                            
                            # Log the auto-mute
                            await cautions_cog.log_action(
                                interaction.guild, 
                                "Auto-Mute", 
                                member, 
                                interaction.client.user, 
                                reason,
                                extra_fields=[{"name": "Duration", "value": f"{duration} minutes"}]
                            )
                        
                        elif action == "timeout":
                            if duration:
                                until = datetime.utcnow() + timedelta(minutes=duration)
                                await member.timeout(until=until, reason=reason)
                                
                                await interaction.followup.send(
                                    f"⏰ {member.mention} has been automatically timed out for {duration} minutes due to reaching warning threshold.",
                                    ephemeral=True
                                )
                                
                                await cautions_cog.log_action(
                                    interaction.guild, 
                                    "Auto-Timeout", 
                                    member, 
                                    interaction.client.user, 
                                    reason,
                                    extra_fields=[{"name": "Duration", "value": f"{duration} minutes"}]
                                )
                        
                        elif action == "kick":
                            await member.kick(reason=reason)
                            
                            await interaction.followup.send(
                                f"👢 {member.mention} has been automatically kicked due to reaching warning threshold.",
                                ephemeral=True
                            )
                            
                            await cautions_cog.log_action(
                                interaction.guild, 
                                "Auto-Kick", 
                                member, 
                                interaction.client.user, 
                                reason
                            )
                        
                        elif action == "ban":
                            await member.ban(reason=reason)
                            
                            await interaction.followup.send(
                                f"🔨 {member.mention} has been automatically banned due to reaching warning threshold.",
                                ephemeral=True
                            )
                            
                            await cautions_cog.log_action(
                                interaction.guild, 
                                "Auto-Ban", 
                                member, 
                                interaction.client.user, 
                                reason
                            )
                    
                    except discord.Forbidden:
                        await interaction.followup.send(
                            f"❌ I don't have permission to {action} this user.",
                            ephemeral=True
                        )
                    except Exception as e:
                        log.error(f"Error applying threshold action {action}: {e}")
                        await interaction.followup.send(
                            f"❌ Error applying automatic {action}: {str(e)}",
                            ephemeral=True
                        )
            
            # Show the modal
            modal = CautionModal(self)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            log.error(f"Error in caution button: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing the caution.", 
                ephemeral=True
            )
    
    @discord.ui.button(label="Mute 1h", style=discord.ButtonStyle.secondary, emoji="🔇")
    async def mute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Mute the reported user for 1 hour"""
        try:
            until = discord.utils.utcnow() + timedelta(hours=1)
            await self.reported_user.timeout(until, reason=f"Report handled by {interaction.user}")
            
            embed = discord.Embed(
                title="✅ Action Taken",
                description=f"{self.reported_user.mention} has been muted for 1 hour.",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Handled by {interaction.user}")
            
            await interaction.response.edit_message(embed=embed, view=None)
            self.handled_by = interaction.user
            
            # Log the action
            await self.cog.log_action("mute", interaction.user, self.reported_user, 
                                    self.reporter, "1 hour timeout via report")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to timeout this user.", 
                ephemeral=True
            )
        except Exception as e:
            log.error(f"Error in mute button: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while muting the user.", 
                ephemeral=True
            )
    
    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ban the reported user"""
        try:
            await self.reported_user.ban(
                reason=f"Report handled by {interaction.user} - Banned via report system"
            )
            
            embed = discord.Embed(
                title="✅ Action Taken",
                description=f"{self.reported_user.mention} has been banned.",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Handled by {interaction.user}")
            
            await interaction.response.edit_message(embed=embed, view=None)
            self.handled_by = interaction.user
            
            # Log the action
            await self.cog.log_action("ban", interaction.user, self.reported_user, 
                                    self.reporter, "Banned via report system")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to ban this user.", 
                ephemeral=True
            )
        except Exception as e:
            log.error(f"Error in ban button: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while banning the user.", 
                ephemeral=True
            )
    
    @discord.ui.button(label="Blacklist Reporter", style=discord.ButtonStyle.secondary, emoji="🚫")
    async def blacklist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Blacklist the reporter for false reports"""
        try:
            async with self.cog.config.guild(interaction.guild).blacklisted_users() as blacklist:
                if self.reporter.id not in blacklist:
                    blacklist.append(self.reporter.id)
            
            embed = discord.Embed(
                title="✅ Action Taken",
                description=f"{self.reporter.mention} has been blacklisted from using the report system.",
                color=discord.Color.dark_gray(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Handled by {interaction.user}")
            
            await interaction.response.edit_message(embed=embed, view=None)
            self.handled_by = interaction.user
            
            # Log the action
            await self.cog.log_action("blacklist", interaction.user, self.reporter, 
                                    self.reporter, "Blacklisted for false reporting")
            
        except Exception as e:
            log.error(f"Error in blacklist button: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while blacklisting the reporter.", 
                ephemeral=True
            )
    
    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.success, emoji="✅")
    async def dismiss_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Dismiss the report without action"""
        embed = discord.Embed(
            title="✅ Report Dismissed",
            description="This report has been reviewed and dismissed.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Dismissed by {interaction.user}")
        
        await interaction.response.edit_message(embed=embed, view=None)
        self.handled_by = interaction.user
        
        # Log the action
        await self.cog.log_action("dismiss", interaction.user, self.reported_user, 
                                self.reporter, "Report dismissed")


class Report(red_commands.Cog):
    """Advanced reporting system with staff quick actions"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=987654321, force_registration=True)
        
        # Default settings
        self.config.register_guild(
            report_channel=None,
            staff_roles=[],
            blacklisted_users=[],
            log_channel=None,
            cooldown_seconds=300,  # 5 minutes between reports
            enabled=True
        )
        
        self.config.register_user(
            last_report_time=0,
            total_reports=0
        )
        
        # Cooldown tracking
        self.user_cooldowns = {}
    
    async def cog_load(self):
        """Initialize the cog"""
        log.info("Report cog loaded successfully")
    
    def cog_unload(self):
        """Cleanup when unloading"""
        log.info("Report cog unloaded")
    
    async def validate_input(self, text: str, max_length: int = 1000) -> str:
        """Validate and sanitize user input"""
        if not text or not text.strip():
            raise commands.BadArgument("Input cannot be empty")
        
        text = text.strip()
        if len(text) > max_length:
            raise commands.BadArgument(f"Input too long (max {max_length} characters)")
        
        # Basic sanitization - remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text
    
    async def is_blacklisted(self, guild: discord.Guild, user: discord.Member) -> bool:
        """Check if user is blacklisted from reporting"""
        blacklist = await self.config.guild(guild).blacklisted_users()
        return user.id in blacklist
    
    async def check_cooldown(self, user: discord.Member) -> bool:
        """Check if user is on cooldown"""
        guild_config = self.config.guild(user.guild)
        cooldown_seconds = await guild_config.cooldown_seconds()
        
        last_report = await self.config.user(user).last_report_time()
        current_time = datetime.utcnow().timestamp()
        
        if current_time - last_report < cooldown_seconds:
            return False
        
        # Update last report time
        await self.config.user(user).last_report_time.set(current_time)
        return True
    
    async def get_staff_mention(self, guild: discord.Guild) -> str:
        """Get staff role mentions for pinging"""
        staff_roles = await self.config.guild(guild).staff_roles()
        mentions = []
        
        for role_id in staff_roles:
            role = guild.get_role(role_id)
            if role:
                mentions.append(role.mention)
        
        return " ".join(mentions) if mentions else "@here"
    
    async def log_action(self, action: str, moderator: discord.Member, 
                        target_user: discord.Member, reporter: discord.Member, 
                        reason: str):
        """Log moderation actions to the log channel"""
        log_channel_id = await self.config.guild(moderator.guild).log_channel()
        if not log_channel_id:
            return
        
        log_channel = moderator.guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title=f"Report Action: {action.title()}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="Moderator", value=f"{moderator.mention} ({moderator})", inline=True)
        embed.add_field(name="Target", value=f"{target_user.mention} ({target_user})", inline=True)
        embed.add_field(name="Reporter", value=f"{reporter.mention} ({reporter})", inline=True)
        embed.add_field(name="Action", value=action.title(), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        try:
            await log_channel.send(embed=embed)
        except Exception as e:
            log.error(f"Failed to send log message: {e}")
    
    async def send_report(self, guild: discord.Guild, reporter: discord.Member, 
                         reported_user: discord.Member, reason: str, 
                         original_message: Optional[discord.Message] = None):
        """Send the report to the designated channel"""
        report_channel_id = await self.config.guild(guild).report_channel()
        if not report_channel_id:
            return None
        
        report_channel = guild.get_channel(report_channel_id)
        if not report_channel:
            return None
        
        # Create the main report embed
        embed = discord.Embed(
            title="🚨 User Report",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="Reporter", 
            value=f"{reporter.mention} ({reporter})\n`{reporter.id}`", 
            inline=True
        )
        embed.add_field(
            name="Reported User", 
            value=f"{reported_user.mention} ({reported_user})\n`{reported_user.id}`", 
            inline=True
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        
        if original_message:
            embed.add_field(
                name="Message Content", 
                value=f"```{original_message.content[:800]}{'...' if len(original_message.content) > 800 else ''}```", 
                inline=False
            )
            embed.add_field(
                name="Message Link", 
                value=f"[Jump to Message]({original_message.jump_url})", 
                inline=True
            )
        
        embed.add_field(
            name="Channel", 
            value=f"#{original_message.channel.name if original_message else 'N/A'}", 
            inline=True
        )
        
        # Get staff mentions
        staff_mention = await self.get_staff_mention(guild)
        
        # Create the view with action buttons
        view = ReportView(self, reported_user, reporter, original_message)
        
        try:
            message = await report_channel.send(
                content=f"{staff_mention} New report received!",
                embed=embed,
                view=view
            )
            
            # Update report count
            current_reports = await self.config.user(reporter).total_reports()
            await self.config.user(reporter).total_reports.set(current_reports + 1)
            
            return message
            
        except Exception as e:
            log.error(f"Failed to send report: {e}")
            return None
    
    @red_commands.command(name="report")
    @red_commands.guild_only()
    async def report_command(self, ctx, user: discord.Member, *, reason: str):
        """Report a user to staff with a reason
        
        Usage: [p]report @user <reason>
        """
        try:
            # Check if reporting is enabled
            if not await self.config.guild(ctx.guild).enabled():
                await ctx.send("❌ The reporting system is currently disabled.", delete_after=10)
                return
            
            # Check if user is blacklisted
            if await self.is_blacklisted(ctx.guild, ctx.author):
                await ctx.send("❌ You are blacklisted from using the report system.", delete_after=10)
                return
            
            # Check cooldown
            if not await self.check_cooldown(ctx.author):
                cooldown_seconds = await self.config.guild(ctx.guild).cooldown_seconds()
                await ctx.send(
                    f"❌ You're on cooldown. Please wait {cooldown_seconds // 60} minutes between reports.", 
                    delete_after=10
                )
                return
            
            # Validate reason
            reason = await self.validate_input(reason, 1000)
            
            # Can't report yourself
            if user == ctx.author:
                await ctx.send("❌ You cannot report yourself.", delete_after=10)
                return
            
            # Can't report bots (unless it's a specific case)
            if user.bot:
                await ctx.send("❌ You cannot report bots.", delete_after=10)
                return
            
            # Get the message being replied to if this is a reply
            original_message = None
            if ctx.message.reference and ctx.message.reference.message_id:
                try:
                    original_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                except:
                    pass
            
            # Send the report
            report_message = await self.send_report(ctx.guild, ctx.author, user, reason, original_message)
            
            if report_message:
                await ctx.send("✅ Report submitted successfully. Staff have been notified.", delete_after=10)
                # Delete the command message for privacy
                try:
                    await ctx.message.delete()
                except:
                    pass
            else:
                await ctx.send("❌ Failed to submit report. Please contact an administrator.", delete_after=10)
                
        except commands.BadArgument as e:
            await ctx.send(f"❌ {e}", delete_after=10)
        except Exception as e:
            log.error(f"Error in report command: {e}")
            await ctx.send("❌ An error occurred while processing your report.", delete_after=10)
    
    # Context menu command for right-click reporting
    @red_commands.context_menu(name="Report Message")
    async def report_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        """Right-click context menu to report a message"""
        try:
            # Check if reporting is enabled
            if not await self.config.guild(interaction.guild).enabled():
                await interaction.response.send_message(
                    "❌ The reporting system is currently disabled.", 
                    ephemeral=True
                )
                return
            
            # Check if user is blacklisted
            if await self.is_blacklisted(interaction.guild, interaction.user):
                await interaction.response.send_message(
                    "❌ You are blacklisted from using the report system.", 
                    ephemeral=True
                )
                return
            
            # Check cooldown
            if not await self.check_cooldown(interaction.user):
                cooldown_seconds = await self.config.guild(interaction.guild).cooldown_seconds()
                await interaction.response.send_message(
                    f"❌ You're on cooldown. Please wait {cooldown_seconds // 60} minutes between reports.", 
                    ephemeral=True
                )
                return
            
            # Can't report yourself
            if message.author == interaction.user:
                await interaction.response.send_message(
                    "❌ You cannot report yourself.", 
                    ephemeral=True
                )
                return
            
            # Can't report bots
            if message.author.bot:
                await interaction.response.send_message(
                    "❌ You cannot report bots.", 
                    ephemeral=True
                )
                return
            
            # Create a modal for the reason
            class ReportModal(discord.ui.Modal, title="Report User"):
                def __init__(self, cog, reported_user, original_message):
                    super().__init__()
                    self.cog = cog
                    self.reported_user = reported_user
                    self.original_message = original_message
                
                reason = discord.ui.TextInput(
                    label="Reason for Report",
                    placeholder="Please provide a detailed reason for this report...",
                    style=discord.TextStyle.paragraph,
                    max_length=1000,
                    required=True
                )
                
                async def on_submit(self, interaction: discord.Interaction):
                    try:
                        reason_text = await self.cog.validate_input(self.reason.value, 1000)
                        
                        # Send the report
                        report_message = await self.cog.send_report(
                            interaction.guild, 
                            interaction.user, 
                            self.reported_user, 
                            reason_text, 
                            self.original_message
                        )
                        
                        if report_message:
                            await interaction.response.send_message(
                                "✅ Report submitted successfully. Staff have been notified.", 
                                ephemeral=True
                            )
                        else:
                            await interaction.response.send_message(
                                "❌ Failed to submit report. Please contact an administrator.", 
                                ephemeral=True
                            )
                    except Exception as e:
                        log.error(f"Error in report modal: {e}")
                        await interaction.response.send_message(
                            "❌ An error occurred while processing your report.", 
                            ephemeral=True
                        )
            
            modal = ReportModal(self, message.author, message)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            log.error(f"Error in context menu report: {e}")
            await interaction.followup.send(
                "❌ An error occurred while processing your report.", 
                ephemeral=True
            )
    
    @red_commands.group(name="reportset")
    @red_commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def report_settings(self, ctx):
        """Configure the report system"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @report_settings.command(name="channel")
    async def set_report_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel where reports will be sent"""
        if channel is None:
            current_channel_id = await self.config.guild(ctx.guild).report_channel()
            if current_channel_id:
                current_channel = ctx.guild.get_channel(current_channel_id)
                if current_channel:
                    await ctx.send(f"Current report channel: {current_channel.mention}")
                else:
                    await ctx.send("Report channel is set but the channel no longer exists.")
            else:
                await ctx.send("No report channel is currently set.")
            return
        
        await self.config.guild(ctx.guild).report_channel.set(channel.id)
        await ctx.send(f"✅ Report channel set to {channel.mention}")
    
    @report_settings.command(name="staffrole")
    async def manage_staff_roles(self, ctx, action: str, role: discord.Role = None):
        """Manage staff roles that get pinged on reports
        
        Actions: add, remove, list
        """
        action = action.lower()
        
        if action == "list":
            staff_roles = await self.config.guild(ctx.guild).staff_roles()
            if not staff_roles:
                await ctx.send("No staff roles configured.")
                return
            
            role_mentions = []
            for role_id in staff_roles:
                role_obj = ctx.guild.get_role(role_id)
                if role_obj:
                    role_mentions.append(role_obj.mention)
            
            if role_mentions:
                await ctx.send(f"Staff roles: {', '.join(role_mentions)}")
            else:
                await ctx.send("No valid staff roles found.")
            
        elif action == "add":
            if role is None:
                await ctx.send("Please specify a role to add.")
                return
            
            async with self.config.guild(ctx.guild).staff_roles() as staff_roles:
                if role.id not in staff_roles:
                    staff_roles.append(role.id)
                    await ctx.send(f"✅ Added {role.mention} to staff roles.")
                else:
                    await ctx.send(f"{role.mention} is already in staff roles.")
        
        elif action == "remove":
            if role is None:
                await ctx.send("Please specify a role to remove.")
                return
            
            async with self.config.guild(ctx.guild).staff_roles() as staff_roles:
                if role.id in staff_roles:
                    staff_roles.remove(role.id)
                    await ctx.send(f"✅ Removed {role.mention} from staff roles.")
                else:
                    await ctx.send(f"{role.mention} is not in staff roles.")
        
        else:
            await ctx.send("Invalid action. Use: add, remove, or list")
    
    @report_settings.command(name="logchannel")
    async def set_log_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for logging report actions"""
        if channel is None:
            current_channel_id = await self.config.guild(ctx.guild).log_channel()
            if current_channel_id:
                current_channel = ctx.guild.get_channel(current_channel_id)
                if current_channel:
                    await ctx.send(f"Current log channel: {current_channel.mention}")
                else:
                    await ctx.send("Log channel is set but the channel no longer exists.")
            else:
                await ctx.send("No log channel is currently set.")
            return
        
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(f"✅ Log channel set to {channel.mention}")
    
    @report_settings.command(name="cooldown")
    async def set_cooldown(self, ctx, seconds: int):
        """Set the cooldown between reports (in seconds)"""
        if seconds < 0:
            await ctx.send("Cooldown cannot be negative.")
            return
        
        await self.config.guild(ctx.guild).cooldown_seconds.set(seconds)
        
        if seconds == 0:
            await ctx.send("✅ Report cooldown disabled.")
        else:
            minutes = seconds // 60
            await ctx.send(f"✅ Report cooldown set to {minutes} minutes ({seconds} seconds).")
    
    @report_settings.command(name="toggle")
    async def toggle_reports(self, ctx):
        """Enable or disable the report system"""
        current_state = await self.config.guild(ctx.guild).enabled()
        new_state = not current_state
        
        await self.config.guild(ctx.guild).enabled.set(new_state)
        
        if new_state:
            await ctx.send("✅ Report system enabled.")
        else:
            await ctx.send("❌ Report system disabled.")
    
    @report_settings.command(name="blacklist")
    async def manage_blacklist(self, ctx, action: str, user: discord.Member = None):
        """Manage the report blacklist
        
        Actions: add, remove, list
        """
        action = action.lower()
        
        if action == "list":
            blacklisted = await self.config.guild(ctx.guild).blacklisted_users()
            if not blacklisted:
                await ctx.send("No users are blacklisted.")
                return
            
            user_mentions = []
            for user_id in blacklisted:
                user_obj = ctx.guild.get_member(user_id)
                if user_obj:
                    user_mentions.append(f"{user_obj.mention} ({user_obj})")
                else:
                    user_mentions.append(f"<@{user_id}> (ID: {user_id})")
            
            embed = discord.Embed(
                title="Blacklisted Users",
                description="\n".join(user_mentions),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
        elif action == "add":
            if user is None:
                await ctx.send("Please specify a user to blacklist.")
                return
            
            async with self.config.guild(ctx.guild).blacklisted_users() as blacklist:
                if user.id not in blacklist:
                    blacklist.append(user.id)
                    await ctx.send(f"✅ {user.mention} has been blacklisted from reporting.")
                else:
                    await ctx.send(f"{user.mention} is already blacklisted.")
        
        elif action == "remove":
            if user is None:
                await ctx.send("Please specify a user to remove from blacklist.")
                return
            
            async with self.config.guild(ctx.guild).blacklisted_users() as blacklist:
                if user.id in blacklist:
                    blacklist.remove(user.id)
                    await ctx.send(f"✅ {user.mention} has been removed from the blacklist.")
                else:
                    await ctx.send(f"{user.mention} is not blacklisted.")
        
        else:
            await ctx.send("Invalid action. Use: add, remove, or list")
    
    @report_settings.command(name="status")
    async def show_status(self, ctx):
        """Show current report system configuration"""
        config = self.config.guild(ctx.guild)
        
        enabled = await config.enabled()
        report_channel_id = await config.report_channel()
        log_channel_id = await config.log_channel()
        staff_roles = await config.staff_roles()
        cooldown = await config.cooldown_seconds()
        blacklisted = await config.blacklisted_users()
        
        embed = discord.Embed(
            title="Report System Status",
            color=discord.Color.green() if enabled else discord.Color.red()
        )
        
        embed.add_field(
            name="Status", 
            value="✅ Enabled" if enabled else "❌ Disabled", 
            inline=True
        )
        
        # Report channel
        if report_channel_id:
            report_channel = ctx.guild.get_channel(report_channel_id)
            channel_text = report_channel.mention if report_channel else "Channel not found"
        else:
            channel_text = "Not set"
        embed.add_field(name="Report Channel", value=channel_text, inline=True)
        
        # Log channel
        if log_channel_id:
            log_channel = ctx.guild.get_channel(log_channel_id)
            log_text = log_channel.mention if log_channel else "Channel not found"
        else:
            log_text = "Not set"
        embed.add_field(name="Log Channel", value=log_text, inline=True)
        
        # Staff roles
        if staff_roles:
            role_mentions = []
            for role_id in staff_roles[:5]:  # Limit to 5 roles to prevent embed overflow
                role = ctx.guild.get_role(role_id)
                if role:
                    role_mentions.append(role.mention)
            staff_text = ", ".join(role_mentions)
            if len(staff_roles) > 5:
                staff_text += f" (+{len(staff_roles) - 5} more)"
        else:
            staff_text = "None set"
        embed.add_field(name="Staff Roles", value=staff_text, inline=False)
        
        # Cooldown
        if cooldown > 0:
            cooldown_text = f"{cooldown // 60} minutes"
        else:
            cooldown_text = "Disabled"
        embed.add_field(name="Cooldown", value=cooldown_text, inline=True)
        
        # Blacklisted users
        embed.add_field(name="Blacklisted Users", value=str(len(blacklisted)), inline=True)
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(Report(bot))
