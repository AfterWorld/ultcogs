import discord
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, List, Dict
from collections import deque

from redbot.core import Config, commands, checks
from redbot.core.bot import Red
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.chat_formatting import pagify, box

# Default config values
DEFAULT_WARNING_EXPIRY_DAYS = 30
DEFAULT_ACTION_THRESHOLDS = {
    "3": {"action": "mute", "duration": 30, "reason": "Exceeded 3 warning points"},
    "5": {"action": "timeout", "duration": 60, "reason": "Exceeded 5 warning points"},
    "10": {"action": "kick", "reason": "Exceeded 10 warning points"}
}

log = logging.getLogger("red.cogs.cautions")

class Cautions(commands.Cog):
    """Enhanced moderation cog with point-based warning system."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=3487613987, force_registration=True)
        
        # Default guild settings
        default_guild = {
            "log_channel": None,
            "mute_role": None,
            "warning_expiry_days": DEFAULT_WARNING_EXPIRY_DAYS,
            "action_thresholds": DEFAULT_ACTION_THRESHOLDS,
            "case_count": 0,  # Track the number of cases
            "modlog": {}  # Store case details
        }
        
        # Default member settings
        default_member = {
            "warnings": [],
            "total_points": 0,
            "muted_until": None,
            "applied_thresholds": []
        }
        
        # Register defaults
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        
        # Rate limiting protection
        self.rate_limit = {
            "message_queue": {},  # Per-channel message queue
            "command_cooldown": {},  # Per-guild command cooldown
            "global_cooldown": deque(maxlen=10),  # Global command timestamps
        }
        
        # Start background tasks
        self.warning_cleanup_task = self.bot.loop.create_task(self.warning_cleanup_loop())
        self.mute_check_task = self.bot.loop.create_task(self.mute_check_loop())
    
    def cog_unload(self):
        """Called when the cog is unloaded."""
        self.warning_cleanup_task.cancel()
        self.mute_check_task.cancel()

    async def warning_cleanup_loop(self):
        """Background task to check and remove expired warnings."""
        await self.bot.wait_until_ready()
        
        while True:
            try:
                log.info("Running warning cleanup task")
                all_guilds = await self.config.all_guilds()
                
                for guild_id, guild_data in all_guilds.items():
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue
                        
                    expiry_days = guild_data["warning_expiry_days"]
                    current_time = datetime.utcnow().timestamp()
                    
                    # Get all members with warnings in this guild
                    all_members = await self.config.all_members(guild)
                    
                    for member_id, member_data in all_members.items():
                        if not member_data.get("warnings"):
                            continue
                            
                        warnings = member_data["warnings"]
                        updated_warnings = []
                        
                        for warning in warnings:
                            issue_time = warning.get("timestamp", 0)
                            expiry_time = issue_time + (expiry_days * 86400)  # Convert days to seconds
                            
                            # Keep warning if not expired
                            if current_time < expiry_time:
                                updated_warnings.append(warning)
                        
                        # Update if warnings were removed
                        if len(warnings) != len(updated_warnings):
                            member_config = self.config.member_from_ids(guild_id, member_id)
                            await member_config.warnings.set(updated_warnings)
                            
                            # Recalculate total points
                            total_points = sum(w.get("points", 1) for w in updated_warnings)
                            await member_config.total_points.set(total_points)
                            
                            # Log that warnings were cleared due to expiry
                            log_channel_id = guild_data.get("log_channel")
                            if log_channel_id:
                                log_channel = guild.get_channel(log_channel_id)
                                if log_channel:
                                    member = guild.get_member(int(member_id))
                                    if member:
                                        embed = discord.Embed(
                                            title="Warnings Expired",
                                            description=f"Some warnings for {member.mention} have expired.",
                                            color=0x00ff00
                                        )
                                        embed.add_field(name="Current Points", value=str(total_points))
                                        embed.set_footer(text=datetime.utcnow().strftime("%m/%d/%Y %I:%M %p"))
                                        await self.safe_send_message(log_channel, embed=embed)
            
            except Exception as e:
                log.error(f"Error in warning expiry check: {e}", exc_info=True)
            
            # Run every 6 hours
            await asyncio.sleep(21600)

    async def mute_check_loop(self):
        """Background task to check and remove expired mutes."""
        await self.bot.wait_until_ready()
        
        while True:
            try:
                for guild in self.bot.guilds:
                    # Get the mute role
                    guild_data = await self.config.guild(guild).all()
                    mute_role_id = guild_data.get("mute_role")
                    if not mute_role_id:
                        continue
                        
                    mute_role = guild.get_role(mute_role_id)
                    if not mute_role:
                        continue
                    
                    # Get all members and check their mute status
                    all_members = await self.config.all_members(guild)
                    current_time = datetime.utcnow().timestamp()
                    
                    for member_id, member_data in all_members.items():
                        # Skip if no mute end time
                        muted_until = member_data.get("muted_until")
                        if not muted_until:
                            continue
                            
                        # Check if mute has expired
                        if current_time > muted_until:
                            try:
                                # Get member
                                member = guild.get_member(int(member_id))
                                if not member:
                                    continue
                                
                                # Check if they still have the mute role
                                if mute_role in member.roles:
                                    # Restore original roles
                                    await self.restore_member_roles(guild, member)
                                    
                                    # Log unmute
                                    await self.log_action(
                                        guild, 
                                        "Auto-Unmute", 
                                        member, 
                                        self.bot.user, 
                                        "Temporary mute duration expired"
                                    )
                            except Exception as e:
                                log.error(f"Error during automatic unmute check: {e}", exc_info=True)
                
            except Exception as e:
                log.error(f"Error in mute check task: {e}", exc_info=True)
            
            # Check every minute
            await asyncio.sleep(60)

    async def safe_send_message(self, channel, content=None, *, embed=None, file=None):
        """
        Rate-limited message sending to avoid hitting Discord's API limits.
        
        This function queues messages and sends them with a delay if too many
        messages are being sent to the same channel in a short period.
        """
        if not channel:
            return None
            
        channel_id = str(channel.id)
        
        # Initialize queue for this channel if it doesn't exist
        if channel_id not in self.rate_limit["message_queue"]:
            self.rate_limit["message_queue"][channel_id] = {
                "queue": [],
                "last_send": 0,
                "processing": False
            }
            
        # Add message to queue
        message_data = {"content": content, "embed": embed, "file": file}
        self.rate_limit["message_queue"][channel_id]["queue"].append(message_data)
        
        # Start processing queue if not already running
        if not self.rate_limit["message_queue"][channel_id]["processing"]:
            self.rate_limit["message_queue"][channel_id]["processing"] = True
            return await self.process_message_queue(channel)
            
        return None

    async def process_message_queue(self, channel):
        """Process the message queue for a channel with rate limiting."""
        channel_id = str(channel.id)
        queue_data = self.rate_limit["message_queue"][channel_id]
        
        try:
            while queue_data["queue"]:
                # Get the next message
                message_data = queue_data["queue"][0]
                
                # Check if we need to delay sending (rate limit prevention)
                current_time = asyncio.get_event_loop().time()
                time_since_last = current_time - queue_data["last_send"]
                
                # If less than 1 second since last message, wait
                if time_since_last < 1:
                    await asyncio.sleep(1 - time_since_last)
                
                # Send the message
                try:
                    await channel.send(
                        content=message_data["content"],
                        embed=message_data["embed"],
                        file=message_data["file"]
                    )
                    queue_data["last_send"] = asyncio.get_event_loop().time()
                except discord.HTTPException as e:
                    if e.status == 429:  # Rate limit hit
                        retry_after = e.retry_after if hasattr(e, 'retry_after') else 5
                        log.info(f"Rate limit hit, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue  # Try again without removing from queue
                    else:
                        log.error(f"Error sending message: {e}")
                
                # Remove sent message from queue
                queue_data["queue"].pop(0)
                
                # Small delay between messages
                await asyncio.sleep(0.5)
        
        except Exception as e:
            log.error(f"Error processing message queue: {e}", exc_info=True)
        
        finally:
            # Mark queue as not processing
            queue_data["processing"] = False

    # Settings commands
    @commands.group(name="cautionset", invoke_without_command=True)
    @checks.admin_or_permissions(administrator=True)
    async def caution_settings(self, ctx):
        """Configure the warning system settings."""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Caution System Settings",
                description="Use these commands to configure the warning system.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Commands",
                value=(
                    f"`{ctx.clean_prefix}cautionset expiry <days>` - Set warning expiry time\n"
                    f"`{ctx.clean_prefix}cautionset setthreshold <points> <action> [duration] [reason]` - Set action thresholds\n"
                    f"`{ctx.clean_prefix}cautionset removethreshold <points>` - Remove a threshold\n"
                    f"`{ctx.clean_prefix}cautionset showthresholds` - List all thresholds\n"
                    f"`{ctx.clean_prefix}cautionset setlogchannel [channel]` - Set the log channel"
                ),
                inline=False
            )
            await ctx.send(embed=embed)

    @caution_settings.command(name="expiry")
    async def set_warning_expiry(self, ctx, days: int):
        """Set how many days until warnings expire automatically."""
        if days < 1:
            return await ctx.send("Expiry time must be at least 1 day.")
        
        await self.config.guild(ctx.guild).warning_expiry_days.set(days)
        await ctx.send(f"Warnings will now expire after {days} days.")

    @caution_settings.command(name="setthreshold")
    async def set_action_threshold(
        self, ctx, 
        points: int, 
        action: str, 
        duration: Optional[int] = None, 
        *, reason: Optional[str] = None
    ):
        """
        Set an automatic action to trigger at a specific warning threshold.
        
        Actions: mute, timeout, kick, ban
        Duration (in minutes) is required for mute and timeout actions.
        """
        valid_actions = ["mute", "timeout", "kick", "ban"]
        if action.lower() not in valid_actions:
            return await ctx.send(f"Invalid action. Choose from: {', '.join(valid_actions)}")
        
        if action.lower() in ["mute", "timeout"] and duration is None:
            return await ctx.send(f"Duration (in minutes) is required for {action} action.")
        
        async with self.config.guild(ctx.guild).action_thresholds() as thresholds:
            # Create new threshold entry
            new_threshold = {"action": action.lower()}
            
            if duration:
                new_threshold["duration"] = duration
                
            if reason:
                new_threshold["reason"] = reason
            else:
                new_threshold["reason"] = f"Exceeded {points} warning points"
            
            # Save the new threshold
            thresholds[str(points)] = new_threshold
        
        # Confirmation message
        confirmation = f"When a member reaches {points} warning points, they will be {action.lower()}ed"
        if duration:
            confirmation += f" for {duration} minutes"
        confirmation += f" with reason: {new_threshold['reason']}"
        
        await ctx.send(confirmation)

    @caution_settings.command(name="removethreshold")
    async def remove_action_threshold(self, ctx, points: int):
        """Remove an automatic action threshold."""
        async with self.config.guild(ctx.guild).action_thresholds() as thresholds:
            if str(points) in thresholds:
                del thresholds[str(points)]
                await ctx.send(f"Removed action threshold for {points} warning points.")
            else:
                await ctx.send(f"No action threshold set for {points} warning points.")

    @caution_settings.command(name="showthresholds")
    async def show_action_thresholds(self, ctx):
        """Show all configured automatic action thresholds."""
        thresholds = await self.config.guild(ctx.guild).action_thresholds()
        
        if not thresholds:
            return await ctx.send("No action thresholds are configured.")
        
        embed = discord.Embed(title="Warning Action Thresholds", color=0x00ff00)
        
        # Sort thresholds by point value
        sorted_thresholds = sorted(thresholds.items(), key=lambda x: int(x[0]))
        
        for points, data in sorted_thresholds:
            action = data["action"]
            duration = data.get("duration", "N/A")
            reason = data.get("reason", f"Exceeded {points} warning points")
            
            value = f"Action: {action.capitalize()}\n"
            if action in ["mute", "timeout"]:
                value += f"Duration: {duration} minutes\n"
            value += f"Reason: {reason}"
            
            embed.add_field(name=f"{points} Warning Points", value=value, inline=False)
        
        await ctx.send(embed=embed)

    @caution_settings.command(name="setlogchannel")
    async def set_log_channel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Set the channel where moderation actions will be logged."""
        if channel is None:
            channel = ctx.channel
            
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(f"Log channel set to {channel.mention}")

    @commands.command(name="caution")
    @checks.mod_or_permissions(kick_members=True)
    async def warn_member(self, ctx, member: discord.Member, points_or_reason: str = "1", *, remaining_reason: Optional[str] = None):
        """
        Issue a caution/warning to a member with optional point value.
        Default is 1 point if not specified.
        
        Examples:
        [p]caution @user 2 Breaking rule #3
        [p]caution @user Spamming in chat
        """
        # Try to parse points as integer
        try:
            points = int(points_or_reason)
            reason = remaining_reason
        except ValueError:
            # If conversion fails, assume it's part of the reason
            points = 1
            reason = points_or_reason
            if remaining_reason:
                reason += " " + remaining_reason
        
        if points < 1:
            return await ctx.send("Warning points must be at least 1.")
        
        # Create warning entry
        expiry_days = await self.config.guild(ctx.guild).warning_expiry_days()
        warning = {
            "points": points,
            "reason": reason or "No reason provided",
            "moderator_id": ctx.author.id,
            "timestamp": datetime.utcnow().timestamp(),
            "expiry": (datetime.utcnow() + timedelta(days=expiry_days)).timestamp()
        }
        
        # Get member config and update warnings
        member_config = self.config.member(member)
        async with member_config.warnings() as warnings:
            warnings.append(warning)
        
        # Update total points
        async with member_config.all() as member_data:
            member_data["total_points"] = sum(w.get("points", 1) for w in member_data["warnings"])
            total_points = member_data["total_points"]
        
        # Create warning embed
        embed = discord.Embed(title=f"Warning Issued", color=0xff9900)
        embed.add_field(name="Member", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        embed.add_field(name="Points", value=str(points))
        embed.add_field(name="Total Points", value=str(total_points))
        embed.add_field(name="Reason", value=warning["reason"], inline=False)
        embed.add_field(name="Expires", value=f"<t:{int(warning['expiry'])}:R>", inline=False)
        embed.set_footer(text=datetime.utcnow().strftime("%m/%d/%Y %I:%M %p"))
        
        # Send warning in channel and log
        await self.safe_send_message(ctx.channel, f"{member.mention} has been cautioned.", embed=embed)
        
        # Log the warning
        await self.log_action(ctx.guild, "Warning", member, ctx.author, warning["reason"], 
                             extra_fields=[
                                 {"name": "Points", "value": str(points)},
                                 {"name": "Total Points", "value": str(total_points)}
                             ])
        
        # Check if any action thresholds were reached
        await self.check_action_thresholds(ctx, member, total_points)

    async def check_action_thresholds(self, ctx, member, total_points):
        """Check and apply any threshold actions that have been crossed."""
        thresholds = await self.config.guild(ctx.guild).action_thresholds()
        
        # Get thresholds that match or are lower than current points, then get highest
        matching_thresholds = []
        for threshold_points, action_data in thresholds.items():
            if int(threshold_points) <= total_points:
                matching_thresholds.append((int(threshold_points), action_data))
        
        if matching_thresholds:
            # Sort by threshold value (descending) to get highest matching threshold
            matching_thresholds.sort(key=lambda x: x[0], reverse=True)
            threshold_points, action_data = matching_thresholds[0]
            
            # Get applied thresholds
            applied_thresholds = await self.config.member(member).applied_thresholds()
            
            # Check if this threshold has already been applied (to prevent repeated actions)
            if threshold_points not in applied_thresholds:
                # Mark this threshold as applied
                applied_thresholds.append(threshold_points)
                await self.config.member(member).applied_thresholds.set(applied_thresholds)
                
                # Apply the action
                await self.apply_threshold_action(ctx, member, action_data)

    async def apply_threshold_action(self, ctx, member, action_data):
        """Apply an automatic action based on crossed threshold."""
        action = action_data["action"]
        reason = action_data.get("reason", "Warning threshold exceeded")
        duration = action_data.get("duration")
        
        try:
            if action == "mute":
                # Get the mute role
                mute_role_id = await self.config.guild(ctx.guild).mute_role()
                if not mute_role_id:
                    await self.safe_send_message(ctx.channel, f"Mute role not found. Please set up a mute role with {ctx.clean_prefix}setupmute")
                    return
                
                mute_role = ctx.guild.get_role(mute_role_id)
                if not mute_role:
                    await self.safe_send_message(ctx.channel, f"Mute role not found. Please set up a mute role with {ctx.clean_prefix}setupmute")
                    return
                
                # Set muted_until time if duration provided
                if duration:
                    muted_until = datetime.utcnow() + timedelta(minutes=duration)
                    await self.config.member(member).muted_until.set(muted_until.timestamp())
                
                # Apply mute by adding the mute role
                try:
                    await member.add_roles(mute_role, reason=reason)
                    
                    await self.safe_send_message(ctx.channel, f"{member.mention} has been muted for {duration} minutes due to: {reason}")
                except discord.Forbidden:
                    await self.safe_send_message(ctx.channel, "I don't have permission to manage roles for this member.")
                    return
                except Exception as e:
                    await self.safe_send_message(ctx.channel, f"Error applying mute: {str(e)}")
                    return
                
                # Log the mute action
                await self.log_action(ctx.guild, "Auto-Mute", member, self.bot.user, reason,
                                    extra_fields=[{"name": "Duration", "value": f"{duration} minutes"}])
            
            elif action == "timeout":
                until = datetime.utcnow() + timedelta(minutes=duration)
                await member.timeout(until=until, reason=reason)
                await self.safe_send_message(ctx.channel, f"{member.mention} has been timed out for {duration} minutes due to: {reason}")
                await self.log_action(ctx.guild, "Auto-Timeout", member, self.bot.user, reason,
                                    extra_fields=[{"name": "Duration", "value": f"{duration} minutes"}])
            
            elif action == "kick":
                await member.kick(reason=reason)
                await self.safe_send_message(ctx.channel, f"{member.mention} has been kicked due to: {reason}")
                await self.log_action(ctx.guild, "Auto-Kick", member, self.bot.user, reason)
            
            elif action == "ban":
                await member.ban(reason=reason)
                await self.safe_send_message(ctx.channel, f"{member.mention} has been banned due to: {reason}")
                await self.log_action(ctx.guild, "Auto-Ban", member, self.bot.user, reason)
                
        except Exception as e:
            await self.safe_send_message(ctx.channel, f"Failed to apply automatic {action}: {str(e)}")
            log.error(f"Error in apply_threshold_action: {e}", exc_info=True)

    @commands.command(name="quiet")
    @checks.mod_or_permissions(manage_roles=True)
    async def mute_member(self, ctx, member: discord.Member, duration: int = 30, *, reason: Optional[str] = None):
        """
        Mute a member for the specified duration (in minutes).
        
        Examples:
        [p]quiet @user 60 Excessive spam
        [p]quiet @user 30
        """
        try:
            # Ensure member isn't a mod/admin by checking permissions
            if member.guild_permissions.kick_members or member.guild_permissions.administrator:
                return await ctx.send(f"⚠️ Cannot mute {member.mention} as they have moderator/admin permissions.")
                
            # Check for role hierarchy - cannot mute someone with a higher role than the bot
            if member.top_role >= ctx.guild.me.top_role:
                return await ctx.send(f"⚠️ Cannot mute {member.mention} as their highest role is above or equal to mine.")
            
            # Get mute role
            mute_role_id = await self.config.guild(ctx.guild).mute_role()
            if not mute_role_id:
                return await ctx.send(f"Mute role not set up. Please use {ctx.clean_prefix}setupmute first.")
            
            mute_role = ctx.guild.get_role(mute_role_id)
            if not mute_role:
                return await ctx.send(f"Mute role not found. Please use {ctx.clean_prefix}setupmute to create a new one.")
            
            # Check if already muted
            if mute_role in member.roles:
                # Update duration if already muted
                muted_until = datetime.utcnow() + timedelta(minutes=duration)
                await self.config.member(member).muted_until.set(muted_until.timestamp())
                await ctx.send(f"{member.mention} was already muted. Updated mute duration to end {duration} minutes from now.")
                return
                
            # Apply the mute - add the role
            try:
                await member.add_roles(mute_role, reason=f"Manual mute: {reason}")
                
                # Also apply a timeout as a secondary measure
                try:
                    timeout_duration = timedelta(minutes=duration)
                    await member.timeout(timeout_duration, reason=f"Manual mute: {reason}")
                except Exception as timeout_error:
                    log.error(f"Could not apply timeout to {member.id}: {timeout_error}")
                    # Continue even if timeout fails
                    
                # Set muted_until time
                muted_until = datetime.utcnow() + timedelta(minutes=duration)
                await self.config.member(member).muted_until.set(muted_until.timestamp())
                
                # Confirm the mute worked by sending a message and checking if the mute role is there
                applied_roles = [role.id for role in member.roles]
                if mute_role.id in applied_roles:
                    await ctx.send(f"✅ {member.mention} has been muted for {duration} minutes. Reason: {reason or 'No reason provided'}")
                else:
                    await ctx.send(f"⚠️ Added mute role to {member.mention} but it doesn't appear in their roles. The mute may not work correctly.")
                    
                # Log action
                await self.log_action(ctx.guild, "Mute", member, ctx.author, reason,
                                    extra_fields=[{"name": "Duration", "value": f"{duration} minutes"}])
                    
            except discord.Forbidden:
                await ctx.send("I don't have permission to manage roles for this member.")
            except Exception as e:
                await ctx.send(f"Error applying mute: {str(e)}")
                log.error(f"Error in mute_member command: {e}", exc_info=True)
                
        except Exception as e:
            await ctx.send(f"Error in mute command: {str(e)}")
            log.error(f"Error in mute_member command: {e}", exc_info=True)
            
    @commands.command(name="testmute")
    @checks.admin_or_permissions(administrator=True)
    async def test_mute_setup(self, ctx):
        """Test if the mute role is properly set up."""
        try:
            mute_role_id = await self.config.guild(ctx.guild).mute_role()
            
            if not mute_role_id:
                return await ctx.send(f"❌ No mute role has been configured. Please run {ctx.clean_prefix}setupmute first.")
                
            mute_role = ctx.guild.get_role(mute_role_id)
            if not mute_role:
                return await ctx.send(f"❌ Mute role not found. The role may have been deleted. Please run {ctx.clean_prefix}setupmute again.")
                
            # Get bot's position to check hierarchy
            bot_position = ctx.guild.me.top_role.position
            mute_position = mute_role.position
            
            # Check role position
            if mute_position < bot_position - 1:
                await ctx.send(f"⚠️ Warning: Mute role position ({mute_position}) is not directly below bot's highest role ({bot_position})")
            else:
                await ctx.send(f"✅ Mute role position ({mute_position}) looks good relative to bot's highest role ({bot_position})")
                
            # Check permissions across different channel types
            text_channels_checked = 0
            text_channels_with_issues = 0
            voice_channels_checked = 0
            voice_channels_with_issues = 0
            
            # Check a sample of text channels
            for channel in ctx.guild.text_channels[:5]:  # Check first 5 text channels
                text_channels_checked += 1
                perms = channel.permissions_for(mute_role)
                if perms.send_messages:
                    text_channels_with_issues += 1
                    
            # Check a sample of voice channels
            for channel in ctx.guild.voice_channels[:5]:  # Check first 5 voice channels
                voice_channels_checked += 1
                perms = channel.permissions_for(mute_role)
                if perms.speak:
                    voice_channels_with_issues += 1
                    
            # Report results
            if text_channels_with_issues > 0:
                await ctx.send(f"❌ Issues found in {text_channels_with_issues}/{text_channels_checked} text channels - mute role can still send messages")
            else:
                await ctx.send(f"✅ Text channel permissions look good for {text_channels_checked} channels checked")
                
            if voice_channels_with_issues > 0:
                await ctx.send(f"❌ Issues found in {voice_channels_with_issues}/{voice_channels_checked} voice channels - mute role can still speak")
            else:
                await ctx.send(f"✅ Voice channel permissions look good for {voice_channels_checked} channels checked")
                
            # Overall assessment
            if text_channels_with_issues == 0 and voice_channels_with_issues == 0:
                await ctx.send("✅ Mute role appears to be correctly configured!")
            else:
                await ctx.send(f"⚠️ Mute role has issues - please run {ctx.clean_prefix}setupmute again to fix permissions")
                
        except Exception as e:
            await ctx.send(f"Error testing mute setup: {str(e)}")
            log.error(f"Error in test_mute_setup: {e}", exc_info=True)

    @commands.command(name="setupmute")
    @checks.admin_or_permissions(administrator=True)
    async def setup_mute_role(self, ctx):
        """Set up the muted role for the server with proper permissions."""
        try:
            # Check if mute role already exists and delete it to start fresh
            existing_mute_role_id = await self.config.guild(ctx.guild).mute_role()
            if existing_mute_role_id:
                existing_role = ctx.guild.get_role(existing_mute_role_id)
                if existing_role:
                    try:
                        await existing_role.delete(reason="Recreating mute role")
                        await ctx.send(f"Deleted existing mute role to create a new one.")
                    except discord.Forbidden:
                        await ctx.send("I don't have permission to delete the existing mute role.")
                    except Exception as e:
                        await ctx.send(f"Error deleting existing role: {e}")
            
            # Create a new role with no permissions
            mute_role = await ctx.guild.create_role(
                name="Muted", 
                reason="Setup for moderation",
                permissions=discord.Permissions.none()  # Start with no permissions
            )
            
            # Position the role as high as possible (directly below the bot's highest role)
            bot_member = ctx.guild.me
            highest_bot_role = max([r for r in bot_member.roles if not r.is_default()], key=lambda r: r.position)
            
            try:
                # Make sure the muted role is positioned directly below the bot's highest role
                positions = {mute_role: highest_bot_role.position - 1}
                await ctx.guild.edit_role_positions(positions)
                await ctx.send(f"Positioned mute role at position {highest_bot_role.position - 1}")
            except Exception as e:
                await ctx.send(f"Error positioning role: {e}")
                log.error(f"Error positioning mute role: {e}", exc_info=True)
            
            # Save the role ID to config
            await self.config.guild(ctx.guild).mute_role.set(mute_role.id)
            
            # Set up permissions for all channels
            status_msg = await ctx.send("Setting up permissions for the mute role... This may take a moment.")
            
            # List to track any errors during permission setup
            permission_errors = []
            
            # Set permissions for each category
            for category in ctx.guild.categories:
                try:
                    await category.set_permissions(
                        mute_role, 
                        send_messages=False, 
                        speak=False, 
                        add_reactions=False,
                        create_public_threads=False,
                        create_private_threads=False,
                        send_messages_in_threads=False,
                        connect=False  # Prevent joining voice channels
                    )
                except Exception as e:
                    error_msg = f"Error setting permissions for category {category.name}: {e}"
                    permission_errors.append(error_msg)
                    log.error(error_msg)
            
            # Set permissions for all text channels individually (to catch any that might inherit differently)
            for channel in ctx.guild.text_channels:
                try:
                    await channel.set_permissions(
                        mute_role,
                        send_messages=False,
                        add_reactions=False,
                        create_public_threads=False,
                        create_private_threads=False,
                        send_messages_in_threads=False
                    )
                except Exception as e:
                    error_msg = f"Error setting permissions for text channel {channel.name}: {e}"
                    permission_errors.append(error_msg)
                    log.error(error_msg)
            
            # Set permissions for all voice channels
            for channel in ctx.guild.voice_channels:
                try:
                    await channel.set_permissions(
                        mute_role,
                        speak=False,
                        connect=False  # Prevent joining voice channels
                    )
                except Exception as e:
                    error_msg = f"Error setting permissions for voice channel {channel.name}: {e}"
                    permission_errors.append(error_msg)
                    log.error(error_msg)
                    
            # Set permissions for all forum channels (if Discord.py version supports it)
            try:
                for channel in [c for c in ctx.guild.channels if isinstance(c, discord.ForumChannel)]:
                    try:
                        await channel.set_permissions(
                            mute_role,
                            send_messages=False,
                            create_public_threads=False,
                            create_private_threads=False,
                            send_messages_in_threads=False
                        )
                    except Exception as e:
                        error_msg = f"Error setting permissions for forum channel {channel.name}: {e}"
                        permission_errors.append(error_msg)
                        log.error(error_msg)
            except AttributeError:
                # ForumChannel might not be available in this discord.py version
                pass
            
            # Report any errors
            if permission_errors:
                error_report = "\n".join(permission_errors[:5])  # Show first 5 errors
                if len(permission_errors) > 5:
                    error_report += f"\n...and {len(permission_errors) - 5} more errors"
                
                await ctx.send(f"⚠️ Some errors occurred while setting permissions:\n{error_report}")
            
            await status_msg.edit(content=f"✅ Mute role setup complete! The role {mute_role.mention} has been configured.")
            
        except Exception as e:
            await ctx.send(f"Failed to set up mute role: {str(e)}")
            log.error(f"Error in setup_mute_role: {e}", exc_info=True)
        
    async def restore_member_roles(self, guild, member):
        """Restore a member's roles after unmuting them."""
        try:
            # Get mute role
            mute_role_id = await self.config.guild(guild).mute_role()
            mute_role = guild.get_role(mute_role_id) if mute_role_id else None
            
            # Remove mute role if they have it
            if mute_role and mute_role in member.roles:
                await member.remove_roles(mute_role, reason="Unmuting member")
                
                # Also remove timeout if there is one
                try:
                    await member.timeout(None, reason="Unmuting member")
                except Exception as e:
                    log.error(f"Error removing timeout: {e}")
            
            # Clear stored mute data
            await self.config.member(member).muted_until.set(None)
            
            # Verify that the mute role was actually removed
            if mute_role and mute_role in member.roles:
                log.error(f"Failed to remove mute role from {member.id}")
                
                # Try once more with force
                try:
                    await member.remove_roles(mute_role, reason="Retry: Unmuting member")
                except Exception as e:
                    log.error(f"Second attempt to remove mute role failed: {e}")
            
            # Log the unmute action
            log_channel_id = await self.config.guild(guild).log_channel()
            if log_channel_id:
                log_channel = guild.get_channel(log_channel_id)
                if log_channel:
                    await self.safe_send_message(log_channel, f"{member.mention} has been unmuted.")
            
        except Exception as e:
            log.error(f"Error restoring member roles: {e}", exc_info=True)
            # Try to get a channel to send the error
            log_channel_id = await self.config.guild(guild).log_channel()
            if log_channel_id:
                log_channel = guild.get_channel(log_channel_id)
                if log_channel:
                    await self.safe_send_message(log_channel, f"Error unmuting {member.mention}: {str(e)}")

    @commands.command(name="unquiet")
    @checks.mod_or_permissions(manage_roles=True)
    async def unmute_member(self, ctx, member: discord.Member):
        """Unmute a member."""
        mute_role_id = await self.config.guild(ctx.guild).mute_role()
        
        if not mute_role_id:
            return await ctx.send("No mute role has been set up for this server.")
        
        mute_role = ctx.guild.get_role(mute_role_id)
        
        if mute_role and mute_role in member.roles:
            await self.restore_member_roles(ctx.guild, member)
            await ctx.send(f"{member.mention} has been unmuted.")
            await self.log_action(ctx.guild, "Unmute", member, ctx.author)
        else:
            await ctx.send(f"{member.mention} is not muted.")

    @commands.command(name="cautions")
    async def list_warnings(self, ctx, member: Optional[discord.Member] = None):
        """
        List all active warnings for a member.
        Moderators can check other members. Members can check themselves.
        """
        if member is None:
            member = ctx.author
        
        # Check permissions if checking someone else
        if member != ctx.author and not ctx.author.guild_permissions.kick_members:
            return await ctx.send("You don't have permission to view other members' warnings.")
        
        # Get member data
        warnings = await self.config.member(member).warnings()
        total_points = await self.config.member(member).total_points()
        
        if not warnings:
            return await ctx.send(f"{member.mention} has no active warnings.")
        
        # Create embed
        embed = discord.Embed(title=f"Warnings for {member.display_name}", color=0xff9900)
        embed.add_field(name="Total Points", value=str(total_points))
        
        # List all warnings
        for i, warning in enumerate(warnings, start=1):
            moderator = ctx.guild.get_member(warning.get("moderator_id"))
            moderator_mention = moderator.mention if moderator else "Unknown Moderator"
            
            # Format timestamp for display
            timestamp = warning.get("timestamp", 0)
            issued_time = f"<t:{int(timestamp)}:R>"
            
            # Format expiry timestamp
            expiry = warning.get("expiry", 0)
            expiry_time = f"<t:{int(expiry)}:R>"
            
            # Build warning details
            value = f"**Points:** {warning.get('points', 1)}\n"
            value += f"**Reason:** {warning.get('reason', 'No reason provided')}\n"
            value += f"**Moderator:** {moderator_mention}\n"
            value += f"**Issued:** {issued_time}\n"
            value += f"**Expires:** {expiry_time}"
            
            embed.add_field(name=f"Warning #{i}", value=value, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="clearcautions")
    @checks.mod_or_permissions(kick_members=True)
    async def clear_warnings(self, ctx, member: discord.Member):
        """Clear all warnings from a member."""
        # Check if there are warnings
        warnings = await self.config.member(member).warnings()
        
        if warnings:
            # Clear warnings and points
            await self.config.member(member).warnings.set([])
            await self.config.member(member).total_points.set(0)
            
            # Clear applied thresholds too
            await self.config.member(member).applied_thresholds.set([])
            
            # Confirm and log
            await ctx.send(f"All warnings for {member.mention} have been cleared.")
            await self.log_action(ctx.guild, "Clear Warnings", member, ctx.author, "Manual clearing of all warnings")
        else:
            await ctx.send(f"{member.mention} has no warnings to clear.")

    @commands.command(name="removecaution")
    @checks.mod_or_permissions(kick_members=True)
    async def remove_warning(self, ctx, member: discord.Member, warning_index: int):
        """
        Remove a specific warning from a member by index.
        Use the 'cautions' command to see indexes.
        """
        if warning_index < 1:
            return await ctx.send("Warning index must be 1 or higher.")
        
        # Get warnings
        async with self.config.member(member).warnings() as warnings:
            if not warnings:
                return await ctx.send(f"{member.mention} has no warnings.")
            
            if warning_index > len(warnings):
                return await ctx.send(f"Invalid warning index. {member.mention} only has {len(warnings)} warnings.")
            
            # Remove warning (adjust for 0-based index)
            removed_warning = warnings.pop(warning_index - 1)
            
        # Recalculate total points
        async with self.config.member(member).warnings() as warnings:
            total_points = sum(w.get("points", 1) for w in warnings)
            await self.config.member(member).total_points.set(total_points)
            
        # Confirm and log
        await ctx.send(f"Warning #{warning_index} for {member.mention} has been removed.")
        await self.log_action(
            ctx.guild, 
            "Remove Warning", 
            member, 
            ctx.author, 
            f"Manually removed warning #{warning_index}",
            extra_fields=[
                {"name": "Warning Points", "value": str(removed_warning.get("points", 1))},
                {"name": "Warning Reason", "value": removed_warning.get("reason", "No reason provided")},
                {"name": "New Total Points", "value": str(total_points)}
            ]
        )

    async def log_action(self, guild, action, target, moderator, reason=None, extra_fields=None):
        """Log moderation actions to the log channel in a case-based format."""
        log_channel_id = await self.config.guild(guild).log_channel()
        if not log_channel_id:
            return
        
        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        # Get current case number
        case_num = await self.config.guild(guild).get_attr("case_count")
        if case_num is None:
            case_num = 1
        else:
            case_num += 1
        
        # Save the incremented case number
        await self.config.guild(guild).case_count.set(case_num)
        
        # Create embed in the style shown in the example
        embed = discord.Embed(color=0x2f3136)  # Dark Discord UI color
        
        # Adding the icon and case number at the top
        embed.set_author(name=f"carsonthecreator", icon_url="https://cdn.discordapp.com/emojis/1061114293952323586.png")
        
        # Case title
        case_title = f"Case #{case_num}"
        embed.title = case_title
        
        # Format the fields like in the example
        embed.description = (
            f"**Action:** {action}\n"
            f"**User:** {target.mention} ( {target.id} )\n"
            f"**Moderator:** {moderator.mention} ( {moderator.id} )\n"
            f"**Reason:** {reason or 'No reason provided'}\n"
            f"**Date:** {datetime.now(timezone.utc).strftime('%b %d, %Y %I:%M %p')} (just now)"
        )
        
        # If there are extra fields, add them to the description
        if extra_fields:
            for field in extra_fields:
                if field and field.get("name") and field.get("value"):
                    embed.description += f"\n**{field['name']}:** {field['value']}"
        
        # Add a footer with the time
        current_time = datetime.now(timezone.utc).strftime('%I:%M %p')
        
        # We're not adding a footer with timestamp as in the example this appears to be a separate message
        
        # Send the case message
        case_message = await self.safe_send_message(log_channel, embed=embed)
        
        # Add entry to the modlog database
        await self.config.guild(guild).modlog.set_raw(
            str(case_num),
            value={
                "case_num": case_num,
                "action": action,
                "user_id": target.id,
                "user_name": str(target),
                "moderator_id": moderator.id,
                "moderator_name": str(moderator),
                "reason": reason or "No reason provided",
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "message_id": case_message.id if case_message else None
            }
        )
        
        # Add a "Koya • Today at XX:XX" type message with timestamp (as shown in screenshot)
        timestamp_embed = discord.Embed(color=0x2f3136)
        current_time = datetime.now(timezone.utc).strftime('%I:%M %p')
        bot_name = guild.me.display_name
        await self.safe_send_message(log_channel, f"{bot_name} • Today at {current_time}")

    # Error handling for commands
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            # If command has own error handler, don't interfere
            return
            
        error = getattr(error, 'original', error)
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have the required permissions to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"I'm missing permissions needed for this command: {error}")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("Member not found. Please provide a valid member.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument: {error}")
        elif isinstance(error, commands.CommandInvokeError):
            log.error(f"Error in {ctx.command.qualified_name}:", exc_info=error)
            await ctx.send(f"An error occurred: {error}")
        else:
            # For other errors, just log them
            log.error(f"Command error in {ctx.command}: {error}", exc_info=True)
