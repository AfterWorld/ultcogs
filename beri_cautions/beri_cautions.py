"""
BeriCautions - Complete Refactored Version
Enhanced moderation cog with point-based warning system and Beri economy integration.

Key improvements:
1. Fixed datetime.utcnow() -> datetime.now(timezone.utc)
2. Added comprehensive type hints
3. Fixed threshold action application logic
4. Added concurrency locks to prevent race conditions
5. Improved async operation batching
6. Better error handling and logging
"""

import discord
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, List, Dict, Tuple
from collections import deque

from redbot.core import Config, commands, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_number

# ========== CONSTANTS ==========

# Default configuration
DEFAULT_WARNING_EXPIRY_DAYS = 30
DEFAULT_ACTION_THRESHOLDS = {
    "3": {"action": "mute", "duration": 30, "reason": "Exceeded 3 warning points"},
    "5": {"action": "timeout", "duration": 60, "reason": "Exceeded 5 warning points"},
    "10": {"action": "kick", "reason": "Exceeded 10 warning points"}
}

# Fine reason prefixes
FINE_REASON_WARNING = "warning"
FINE_REASON_MANUAL_MUTE = "manual_mute"
FINE_REASON_THRESHOLD = "threshold"

# Background task intervals (seconds)
WARNING_CLEANUP_INTERVAL = 21600  # 6 hours
MUTE_CHECK_INTERVAL = 60  # 1 minute

# Batch processing sizes
BATCH_PROCESS_SIZE_GUILDS = 5
BATCH_PROCESS_SIZE_MEMBERS = 10

# Rate limiting
MESSAGE_QUEUE_MIN_DELAY = 1.0
MESSAGE_QUEUE_BATCH_DELAY = 0.5

log = logging.getLogger("red.cogs.cautions")


class BeriCautions(commands.Cog):
    """Enhanced moderation cog with point-based warning system and Beri economy integration."""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot
        self.config: Config = Config.get_conf(
            self, 
            identifier=3487613988, 
            force_registration=True
        )
        
        self._register_config()
        self._init_rate_limiting()
        self._member_locks: Dict[int, asyncio.Lock] = {}
        self._start_background_tasks()
    
    def _register_config(self) -> None:
        """Register default configuration."""
        default_guild = {
            "log_channel": None,
            "mute_role": None,
            "warning_expiry_days": DEFAULT_WARNING_EXPIRY_DAYS,
            "action_thresholds": DEFAULT_ACTION_THRESHOLDS,
            "case_count": 0,
            "modlog": {},
            "warning_fine_base": 1000,
            "warning_fine_multiplier": 1.5,
            "mute_fine": 5000,
            "timeout_fine": 3000,
            "kick_fine": 10000,
            "ban_fine": 25000,
            "fine_exempt_roles": [],
            "max_fine_per_action": 50000,
        }
        
        default_member = {
            "warnings": [],
            "total_points": 0,
            "muted_until": None,
            "applied_thresholds": [],
            "total_fines_paid": 0,
            "warning_count": 0,
        }
        
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
    
    def _init_rate_limiting(self) -> None:
        """Initialize rate limiting structures."""
        self.rate_limit: Dict = {
            "message_queue": {},
            "command_cooldown": {},
        }
    
    def _start_background_tasks(self) -> None:
        """Start background tasks."""
        self.warning_cleanup_task: asyncio.Task = self.bot.loop.create_task(
            self.warning_cleanup_loop()
        )
        self.mute_check_task: asyncio.Task = self.bot.loop.create_task(
            self.mute_check_loop()
        )
    
    def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        self.warning_cleanup_task.cancel()
        self.mute_check_task.cancel()

    # ========== HELPER METHODS ==========
    
    def _core(self):
        """Get BeriCore instance."""
        return self.bot.get_cog("BeriCore")

    def _get_current_time(self) -> datetime:
        """Get current time with timezone awareness."""
        return datetime.now(timezone.utc)
    
    def _get_current_timestamp(self) -> float:
        """Get current Unix timestamp."""
        return self._get_current_time().timestamp()

    async def _get_member_lock(self, member_id: int) -> asyncio.Lock:
        """Get or create a lock for a specific member to prevent race conditions."""
        if member_id not in self._member_locks:
            self._member_locks[member_id] = asyncio.Lock()
        return self._member_locks[member_id]

    async def _is_fine_exempt(self, member: discord.Member) -> bool:
        """Check if member is exempt from fines."""
        exempt_roles: List[int] = await self.config.guild(member.guild).fine_exempt_roles()
        member_role_ids: List[int] = [role.id for role in member.roles]
        return any(role_id in member_role_ids for role_id in exempt_roles)

    async def _calculate_warning_fine(self, member: discord.Member, points: int) -> int:
        """Calculate fine for a warning based on points and history."""
        guild_config: Dict = await self.config.guild(member.guild).all()
        member_data: Dict = await self.config.member(member).all()
        
        base_fine: int = guild_config.get("warning_fine_base", 1000)
        multiplier: float = guild_config.get("warning_fine_multiplier", 1.5)
        max_fine: int = guild_config.get("max_fine_per_action", 50000)
        
        # Calculate base fine
        fine: int = base_fine * points
        
        # Apply escalation based on warning history
        warning_count: int = member_data.get("warning_count", 0)
        if warning_count > 0:
            escalation: float = multiplier ** min(warning_count, 5)
            fine = int(fine * escalation)
        
        return min(fine, max_fine)

    async def _apply_beri_fine(
        self, 
        member: discord.Member, 
        amount: int, 
        reason: str, 
        moderator: Union[discord.Member, discord.User]
    ) -> bool:
        """Apply a Beri fine to a member. Returns True if successful."""
        core = self._core()
        if not core:
            return False
        
        if await self._is_fine_exempt(member):
            return True
        
        try:
            current_balance: int = await core.get_beri(member)
            
            if current_balance >= amount:
                await core.add_beri(
                    member, 
                    -amount, 
                    reason=f"fine:{reason}", 
                    actor=moderator, 
                    bypass_cap=True
                )
                await self._update_member_fines(member, amount)
                return True
            else:
                # Take partial payment
                if current_balance > 0:
                    await core.add_beri(
                        member, 
                        -current_balance, 
                        reason=f"partial_fine:{reason}", 
                        actor=moderator, 
                        bypass_cap=True
                    )
                    await self._update_member_fines(member, current_balance)
                return False
                
        except Exception as e:
            log.error(f"Error applying Beri fine to {member.id}: {e}", exc_info=True)
            return False

    async def _update_member_fines(self, member: discord.Member, amount: int) -> None:
        """Update member's total fines paid."""
        member_config = self.config.member(member)
        async with member_config.all() as data:
            data["total_fines_paid"] = data.get("total_fines_paid", 0) + amount

    # ========== BACKGROUND TASKS ==========

    async def warning_cleanup_loop(self) -> None:
        """Background task to check and remove expired warnings."""
        await self.bot.wait_until_ready()
        
        while True:
            try:
                log.info("Running warning cleanup task")
                await self._process_warning_cleanup()
            except Exception as e:
                log.error(f"Error in warning cleanup: {e}", exc_info=True)
            
            await asyncio.sleep(WARNING_CLEANUP_INTERVAL)

    async def _process_warning_cleanup(self) -> None:
        """Process warning cleanup for all guilds."""
        all_guilds: Dict = await self.config.all_guilds()
        
        for guild_count, (guild_id, guild_data) in enumerate(all_guilds.items(), 1):
            if guild_count % BATCH_PROCESS_SIZE_GUILDS == 0:
                await asyncio.sleep(0)
            
            guild: Optional[discord.Guild] = self.bot.get_guild(guild_id)
            if guild:
                await self._cleanup_guild_warnings(guild, guild_data)

    async def _cleanup_guild_warnings(
        self, 
        guild: discord.Guild, 
        guild_data: Dict
    ) -> None:
        """Clean up expired warnings for a specific guild."""
        expiry_days: int = guild_data["warning_expiry_days"]
        current_time: float = self._get_current_timestamp()
        all_members: Dict = await self.config.all_members(guild)
        
        for member_count, (member_id, member_data) in enumerate(all_members.items(), 1):
            if member_count % BATCH_PROCESS_SIZE_MEMBERS == 0:
                await asyncio.sleep(0)
            
            if member_data.get("warnings"):
                await self._cleanup_member_warnings(
                    guild, 
                    member_id, 
                    member_data, 
                    current_time, 
                    expiry_days,
                    guild_data.get("log_channel")
                )

    async def _cleanup_member_warnings(
        self,
        guild: discord.Guild,
        member_id: int,
        member_data: Dict,
        current_time: float,
        expiry_days: int,
        log_channel_id: Optional[int]
    ) -> None:
        """Clean up warnings for a specific member."""
        warnings: List[Dict] = member_data["warnings"]
        updated_warnings: List[Dict] = [
            w for w in warnings
            if current_time < w.get("timestamp", 0) + (expiry_days * 86400)
        ]
        
        if len(warnings) != len(updated_warnings):
            async with await self._get_member_lock(member_id):
                member_config = self.config.member_from_ids(guild.id, member_id)
                await member_config.warnings.set(updated_warnings)
                
                total_points: int = sum(w.get("points", 1) for w in updated_warnings)
                await member_config.total_points.set(total_points)
            
            await self._log_warning_expiry(guild, member_id, total_points, log_channel_id)

    async def _log_warning_expiry(
        self,
        guild: discord.Guild,
        member_id: int,
        total_points: int,
        log_channel_id: Optional[int]
    ) -> None:
        """Log warning expiry to the log channel."""
        if not log_channel_id:
            return
        
        log_channel: Optional[discord.TextChannel] = guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        member: Optional[discord.Member] = guild.get_member(member_id)
        if not member:
            return
        
        embed = discord.Embed(
            title="Warnings Expired",
            description=f"Some warnings for {member.mention} have expired.",
            color=0x00ff00
        )
        embed.add_field(name="Current Points", value=str(total_points))
        embed.set_footer(text=self._get_current_time().strftime("%m/%d/%Y %I:%M %p"))
        
        await self.safe_send_message(log_channel, embed=embed)

    async def mute_check_loop(self) -> None:
        """Background task to check and remove expired mutes."""
        await self.bot.wait_until_ready()
        
        while True:
            try:
                await self._process_mute_checks()
            except Exception as e:
                log.error(f"Error in mute check task: {e}", exc_info=True)
            
            await asyncio.sleep(MUTE_CHECK_INTERVAL)

    async def _process_mute_checks(self) -> None:
        """Process mute checks for all guilds."""
        for guild_count, guild in enumerate(self.bot.guilds, 1):
            if guild_count % BATCH_PROCESS_SIZE_GUILDS == 0:
                await asyncio.sleep(0)
            
            await self._check_guild_mutes(guild)

    async def _check_guild_mutes(self, guild: discord.Guild) -> None:
        """Check mutes for a specific guild."""
        guild_data: Dict = await self.config.guild(guild).all()
        mute_role_id: Optional[int] = guild_data.get("mute_role")
        
        if not mute_role_id:
            return
        
        mute_role: Optional[discord.Role] = guild.get_role(mute_role_id)
        if not mute_role:
            return
        
        all_members: Dict = await self.config.all_members(guild)
        current_time: float = self._get_current_timestamp()
        
        for member_count, (member_id, member_data) in enumerate(all_members.items(), 1):
            if member_count % BATCH_PROCESS_SIZE_MEMBERS == 0:
                await asyncio.sleep(0)
            
            await self._check_member_mute(
                guild, 
                member_id, 
                member_data, 
                current_time, 
                mute_role
            )

    async def _check_member_mute(
        self,
        guild: discord.Guild,
        member_id: int,
        member_data: Dict,
        current_time: float,
        mute_role: discord.Role
    ) -> None:
        """Check if a member's mute has expired."""
        muted_until: Optional[float] = member_data.get("muted_until")
        
        if not muted_until or current_time <= muted_until:
            return
        
        try:
            member: Optional[discord.Member] = guild.get_member(member_id)
            if member and mute_role in member.roles:
                await self.restore_member_roles(guild, member)
                await self.log_action(
                    guild,
                    "Auto-Unmute",
                    member,
                    self.bot.user,
                    "Temporary mute duration expired"
                )
        except Exception as e:
            log.error(f"Error during auto-unmute for {member_id}: {e}", exc_info=True)

    # ========== RATE LIMITING ==========

    async def safe_send_message(
        self, 
        channel: discord.TextChannel, 
        content: Optional[str] = None, 
        *, 
        embed: Optional[discord.Embed] = None, 
        file: Optional[discord.File] = None
    ) -> Optional[discord.Message]:
        """Rate-limited message sending to avoid hitting Discord's API limits."""
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

    async def process_message_queue(
        self, 
        channel: discord.TextChannel
    ) -> Optional[discord.Message]:
        """Process the message queue for a channel with rate limiting."""
        channel_id = str(channel.id)
        queue_data = self.rate_limit["message_queue"][channel_id]
        
        try:
            while queue_data["queue"]:
                message_data = queue_data["queue"][0]
                
                # Check if we need to delay sending
                current_time = asyncio.get_event_loop().time()
                time_since_last = current_time - queue_data["last_send"]
                
                if time_since_last < MESSAGE_QUEUE_MIN_DELAY:
                    await asyncio.sleep(MESSAGE_QUEUE_MIN_DELAY - time_since_last)
                
                # Send the message
                try:
                    msg = await channel.send(
                        content=message_data["content"],
                        embed=message_data["embed"],
                        file=message_data["file"]
                    )
                    queue_data["last_send"] = asyncio.get_event_loop().time()
                except discord.HTTPException as e:
                    if e.status == 429:
                        retry_after = e.retry_after if hasattr(e, 'retry_after') else 5
                        log.info(f"Rate limit hit, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        log.error(f"Error sending message: {e}")
                
                # Remove sent message from queue
                queue_data["queue"].pop(0)
                await asyncio.sleep(MESSAGE_QUEUE_BATCH_DELAY)
        
        except Exception as e:
            log.error(f"Error processing message queue: {e}", exc_info=True)
        
        finally:
            queue_data["processing"] = False
        
        return None

    # ========== SETTINGS COMMANDS ==========

    @commands.group(name="cautionset", invoke_without_command=True)
    @checks.admin_or_permissions(administrator=True)
    async def caution_settings(self, ctx: commands.Context) -> None:
        """Configure the warning system settings."""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Caution System Settings",
                description="Use these commands to configure the warning system.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Basic Commands",
                value=(
                    f"`{ctx.clean_prefix}cautionset expiry <days>` - Set warning expiry time\n"
                    f"`{ctx.clean_prefix}cautionset setthreshold <points> <action> [duration] [reason]` - Set action thresholds\n"
                    f"`{ctx.clean_prefix}cautionset removethreshold <points>` - Remove a threshold\n"
                    f"`{ctx.clean_prefix}cautionset showthresholds` - List all thresholds\n"
                    f"`{ctx.clean_prefix}cautionset setlogchannel [channel]` - Set the log channel\n"
                    f"`{ctx.clean_prefix}cautionset mute [role]` - Set the mute role\n"
                ),
                inline=False
            )
            embed.add_field(
                name="Beri Economy Settings",
                value=(
                    f"`{ctx.clean_prefix}cautionset fines` - Configure fine amounts\n"
                    f"`{ctx.clean_prefix}cautionset exemptfines <role>` - Exempt role from fines\n"
                ),
                inline=False
            )
            await ctx.send(embed=embed)

    @caution_settings.group(name="fines", invoke_without_command=True)
    async def fine_settings(self, ctx: commands.Context) -> None:
        """Configure Beri fine settings."""
        guild_config = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(title="Current Fine Settings", color=discord.Color.blue())
        embed.add_field(name="Warning Base Fine", value=f"{humanize_number(guild_config.get('warning_fine_base', 1000))} Beri", inline=True)
        embed.add_field(name="Warning Multiplier", value=f"{guild_config.get('warning_fine_multiplier', 1.5)}x", inline=True)
        embed.add_field(name="Mute Fine", value=f"{humanize_number(guild_config.get('mute_fine', 5000))} Beri", inline=True)
        embed.add_field(name="Timeout Fine", value=f"{humanize_number(guild_config.get('timeout_fine', 3000))} Beri", inline=True)
        embed.add_field(name="Kick Fine", value=f"{humanize_number(guild_config.get('kick_fine', 10000))} Beri", inline=True)
        embed.add_field(name="Ban Fine", value=f"{humanize_number(guild_config.get('ban_fine', 25000))} Beri", inline=True)
        embed.add_field(name="Max Fine Per Action", value=f"{humanize_number(guild_config.get('max_fine_per_action', 50000))} Beri", inline=True)
        
        exempt_roles = guild_config.get('fine_exempt_roles', [])
        if exempt_roles:
            role_mentions = [role.mention for role_id in exempt_roles if (role := ctx.guild.get_role(role_id))]
            embed.add_field(name="Exempt Roles", value="\n".join(role_mentions) or "None", inline=False)
        else:
            embed.add_field(name="Exempt Roles", value="None", inline=False)
        
        await ctx.send(embed=embed)

    @fine_settings.command(name="warningbase")
    async def set_warning_base_fine(self, ctx: commands.Context, amount: int) -> None:
        """Set the base fine amount per warning point."""
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        
        await self.config.guild(ctx.guild).warning_fine_base.set(amount)
        await ctx.send(f"Base warning fine set to {humanize_number(amount)} Beri per point.")

    @fine_settings.command(name="warningmultiplier")
    async def set_warning_multiplier(self, ctx: commands.Context, multiplier: float) -> None:
        """Set the fine multiplier for repeat offenses."""
        if multiplier < 1.0:
            return await ctx.send("Multiplier must be at least 1.0.")
        
        await self.config.guild(ctx.guild).warning_fine_multiplier.set(multiplier)
        await ctx.send(f"Warning fine multiplier set to {multiplier}x.")

    @fine_settings.command(name="mute")
    async def set_mute_fine(self, ctx: commands.Context, amount: int) -> None:
        """Set the additional fine for mutes."""
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        
        await self.config.guild(ctx.guild).mute_fine.set(amount)
        await ctx.send(f"Mute fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="timeout")
    async def set_timeout_fine(self, ctx: commands.Context, amount: int) -> None:
        """Set the additional fine for timeouts."""
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        
        await self.config.guild(ctx.guild).timeout_fine.set(amount)
        await ctx.send(f"Timeout fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="kick")
    async def set_kick_fine(self, ctx: commands.Context, amount: int) -> None:
        """Set the fine for kicks."""
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        
        await self.config.guild(ctx.guild).kick_fine.set(amount)
        await ctx.send(f"Kick fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="ban")
    async def set_ban_fine(self, ctx: commands.Context, amount: int) -> None:
        """Set the fine for bans."""
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        
        await self.config.guild(ctx.guild).ban_fine.set(amount)
        await ctx.send(f"Ban fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="maxfine")
    async def set_max_fine(self, ctx: commands.Context, amount: int) -> None:
        """Set the maximum fine per single action."""
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        
        await self.config.guild(ctx.guild).max_fine_per_action.set(amount)
        await ctx.send(f"Maximum fine per action set to {humanize_number(amount)} Beri.")

    @caution_settings.command(name="exemptfines")
    async def exempt_role_from_fines(self, ctx: commands.Context, role: discord.Role) -> None:
        """Add or remove a role from fine exemption."""
        async with self.config.guild(ctx.guild).fine_exempt_roles() as exempt_roles:
            if role.id in exempt_roles:
                exempt_roles.remove(role.id)
                await ctx.send(f"{role.mention} is no longer exempt from fines.")
            else:
                exempt_roles.append(role.id)
                await ctx.send(f"{role.mention} is now exempt from fines.")

    @caution_settings.command(name="expiry")
    async def set_warning_expiry(self, ctx: commands.Context, days: int) -> None:
        """Set how many days until warnings expire automatically."""
        if days < 1:
            return await ctx.send("Expiry time must be at least 1 day.")
        
        await self.config.guild(ctx.guild).warning_expiry_days.set(days)
        await ctx.send(f"Warnings will now expire after {days} days.")

    @caution_settings.command(name="setthreshold")
    async def set_action_threshold(
        self, 
        ctx: commands.Context, 
        points: int, 
        action: str, 
        duration: Optional[int] = None, 
        *, 
        reason: Optional[str] = None
    ) -> None:
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
            new_threshold = {"action": action.lower()}
            
            if duration:
                new_threshold["duration"] = duration
                
            if reason:
                new_threshold["reason"] = reason
            else:
                new_threshold["reason"] = f"Exceeded {points} warning points"
            
            thresholds[str(points)] = new_threshold
        
        confirmation = f"When a member reaches {points} warning points, they will be {action.lower()}ed"
        if duration:
            confirmation += f" for {duration} minutes"
        confirmation += f" with reason: {new_threshold['reason']}"
        
        await ctx.send(confirmation)

    @caution_settings.command(name="removethreshold")
    async def remove_action_threshold(self, ctx: commands.Context, points: int) -> None:
        """Remove an automatic action threshold."""
        async with self.config.guild(ctx.guild).action_thresholds() as thresholds:
            if str(points) in thresholds:
                del thresholds[str(points)]
                await ctx.send(f"Removed action threshold for {points} warning points.")
            else:
                await ctx.send(f"No action threshold set for {points} warning points.")

    @caution_settings.command(name="showthresholds")
    async def show_action_thresholds(self, ctx: commands.Context) -> None:
        """Show all configured automatic action thresholds."""
        thresholds = await self.config.guild(ctx.guild).action_thresholds()
        
        if not thresholds:
            return await ctx.send("No action thresholds are configured.")
        
        embed = discord.Embed(title="Warning Action Thresholds", color=0x00ff00)
        
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
    async def set_log_channel(
        self, 
        ctx: commands.Context, 
        channel: Optional[discord.TextChannel] = None) -> None:
        """Set the channel where moderation actions will be logged."""
        if channel is None:
            channel = ctx.channel
            
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(f"Log channel set to {channel.mention}")
        
    @caution_settings.command(name="mute")
    async def set_mute_role(
        self, 
        ctx: commands.Context, 
        role: Optional[discord.Role] = None
    ) -> None:
        """Set the mute role for the caution system."""
        if role is None:
            mute_role_id = await self.config.guild(ctx.guild).mute_role()
            if not mute_role_id:
                return await ctx.send("No mute role is currently set. Use this command with a role to set one.")
                
            mute_role = ctx.guild.get_role(mute_role_id)
            if not mute_role:
                return await ctx.send("The configured mute role no longer exists. Please set a new one.")
                
            return await ctx.send(f"Current mute role: {mute_role.mention} (ID: {mute_role.id})")
        
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I need the 'Manage Roles' permission to apply the mute role.")
        
        if role.position >= ctx.guild.me.top_role.position:
            return await ctx.send(f"I cannot manage {role.mention} - it's higher than or equal to my highest role.")
        
        await self.config.guild(ctx.guild).mute_role.set(role.id)
        await ctx.send(f"Mute role set to {role.mention}.")

    # ========== WARNING COMMANDS ==========

    @commands.command(name="caution")
    @checks.mod_or_permissions(kick_members=True)
    async def warn_member(
        self, 
        ctx: commands.Context, 
        member: discord.Member, 
        points_or_reason: str = "1", 
        *, 
        remaining_reason: Optional[str] = None
    ) -> None:
        """
        Issue a caution/warning to a member with optional point value.
        Default is 1 point if not specified. Includes Beri fine.
        
        Examples:
        [p]caution @user 2 Breaking rule #3
        [p]caution @user Spamming in chat
        """
        # Parse points and reason
        try:
            points = int(points_or_reason)
            reason = remaining_reason
        except ValueError:
            points = 1
            reason = points_or_reason
            if remaining_reason:
                reason += " " + remaining_reason
        
        if points < 1:
            return await ctx.send("Warning points must be at least 1.")
        
        # Use lock to prevent race conditions
        async with await self._get_member_lock(member.id):
            # Check if BeriCore is available and apply fine
            core = self._core()
            beri_available = core is not None
            fine_amount = 0
            fine_applied = True
            
            if beri_available:
                fine_amount = await self._calculate_warning_fine(member, points)
                fine_applied = await self._apply_beri_fine(
                    member, 
                    fine_amount, 
                    f"{FINE_REASON_WARNING}:{points}pt", 
                    ctx.author
                )
            
            # Create warning record
            expiry_days = await self.config.guild(ctx.guild).warning_expiry_days()
            current_time = self._get_current_time()
            
            warning = {
                "points": points,
                "reason": reason or "No reason provided",
                "moderator_id": ctx.author.id,
                "timestamp": current_time.timestamp(),
                "expiry": (current_time + timedelta(days=expiry_days)).timestamp(),
                "fine_amount": fine_amount,
                "fine_applied": fine_applied
            }
            
            # Update member's warnings
            member_config = self.config.member(member)
            async with member_config.all() as member_data:
                member_data["warnings"].append(warning)
                member_data["warning_count"] = member_data.get("warning_count", 0) + 1
                member_data["total_points"] = sum(w.get("points", 1) for w in member_data["warnings"])
                total_points = member_data["total_points"]
        
        # Create warning embed
        embed = discord.Embed(title="Warning Issued", color=0xff9900)
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Points", value=str(points), inline=True)
        embed.add_field(name="Total Points", value=str(total_points), inline=True)
        embed.add_field(name="Reason", value=warning["reason"], inline=False)
        embed.add_field(name="Expires", value=f"<t:{int(warning['expiry'])}:R>", inline=False)
        
        if beri_available and fine_amount > 0:
            status = "Applied" if fine_applied else "Failed/Partial"
            embed.add_field(name="Fine", value=f"{humanize_number(fine_amount)} Beri ({status})", inline=True)
        elif beri_available:
            exempt_status = "Exempt from fines" if await self._is_fine_exempt(member) else "No fine (0 Beri balance)"
            embed.add_field(name="Fine Status", value=exempt_status, inline=True)
        
        embed.set_footer(text=current_time.strftime("%m/%d/%Y %I:%M %p"))
        
        # Send warning
        await self.safe_send_message(ctx.channel, f"{member.mention} has been cautioned.", embed=embed)
        
        # Log action
        extra_fields = [
            {"name": "Points", "value": str(points)},
            {"name": "Total Points", "value": str(total_points)}
        ]
        
        if beri_available and fine_amount > 0:
            extra_fields.append({
                "name": "Beri Fine", 
                "value": f"{humanize_number(fine_amount)} ({'Applied' if fine_applied else 'Failed/Partial'})"
            })
        
        await self.log_action(
            ctx.guild, 
            "Warning", 
            member, 
            ctx.author, 
            warning["reason"], 
            extra_fields=extra_fields
        )
        
        # Dispatch custom event
        self.bot.dispatch("caution_issued", ctx.guild, ctx.author, member, warning["reason"])
        
        # Check action thresholds
        await self.check_action_thresholds(ctx, member, total_points)

    async def check_action_thresholds(
        self, 
        ctx: commands.Context, 
        member: discord.Member, 
        total_points: int
    ) -> None:
        """Check and apply any threshold actions that have been crossed."""
        thresholds = await self.config.guild(ctx.guild).action_thresholds()
        applied_thresholds = await self.config.member(member).applied_thresholds()
        
        # Find all matching thresholds that haven't been applied yet
        matching_thresholds = []
        for threshold_str, action_data in thresholds.items():
            threshold_points = int(threshold_str)
            # Only include if we've reached the threshold and haven't applied it yet
            if threshold_points <= total_points and threshold_points not in applied_thresholds:
                matching_thresholds.append((threshold_points, action_data))
        
        if not matching_thresholds:
            return
        
        # Sort by threshold value (highest first) and apply only the highest
        matching_thresholds.sort(key=lambda x: x[0], reverse=True)
        threshold_points, action_data = matching_thresholds[0]
        
        # Mark this threshold as applied
        applied_thresholds.append(threshold_points)
        await self.config.member(member).applied_thresholds.set(applied_thresholds)
        
        # Apply the action
        await self.apply_threshold_action(ctx, member, threshold_points, action_data)

    async def apply_threshold_action(
        self, 
        ctx: commands.Context, 
        member: discord.Member, 
        threshold_points: int,
        action_data: Dict
    ) -> None:
        """Apply an automatic action based on crossed threshold."""
        action = action_data["action"]
        reason = action_data.get("reason", "Warning threshold exceeded")
        duration = action_data.get("duration")
        
        # Calculate and apply additional fine
        core = self._core()
        fine_amount = 0
        fine_applied = True
        
        if core:
            guild_config = await self.config.guild(ctx.guild).all()
            if action == "mute":
                fine_amount = guild_config.get("mute_fine", 5000)
            elif action == "timeout":
                fine_amount = guild_config.get("timeout_fine", 3000)
            elif action == "kick":
                fine_amount = guild_config.get("kick_fine", 10000)
            elif action == "ban":
                fine_amount = guild_config.get("ban_fine", 25000)
            
            if fine_amount > 0:
                fine_applied = await self._apply_beri_fine(
                    member, 
                    fine_amount, 
                    f"{FINE_REASON_THRESHOLD}:{action}", 
                    self.bot.user
                )
        
        try:
            if action == "mute":
                await self._apply_mute_action(ctx, member, duration, reason, fine_amount, fine_applied)
            elif action == "timeout":
                await self._apply_timeout_action(ctx, member, duration, reason, fine_amount, fine_applied)
            elif action == "kick":
                await self._apply_kick_action(ctx, member, reason, fine_amount, fine_applied)
            elif action == "ban":
                await self._apply_ban_action(ctx, member, reason, fine_amount, fine_applied)
        except Exception as e:
            await self.safe_send_message(ctx.channel, f"Failed to apply automatic {action}: {str(e)}")
            log.error(f"Error in apply_threshold_action: {e}", exc_info=True)

    async def _apply_mute_action(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: int,
        reason: str,
        fine_amount: int,
        fine_applied: bool
    ) -> None:
        """Apply mute action."""
        mute_role_id = await self.config.guild(ctx.guild).mute_role()
        if not mute_role_id:
            await self.safe_send_message(
                ctx.channel, 
                f"Mute role not configured. Use {ctx.clean_prefix}cautionset mute to set one."
            )
            return
        
        mute_role = ctx.guild.get_role(mute_role_id)
        if not mute_role:
            await self.safe_send_message(
                ctx.channel, 
                f"Mute role not found. Use {ctx.clean_prefix}cautionset mute to set one."
            )
            return
        
        # Set muted_until time
        if duration:
            muted_until = self._get_current_time() + timedelta(minutes=duration)
            await self.config.member(member).muted_until.set(muted_until.timestamp())
        
        # Apply mute role
        try:
            await member.add_roles(mute_role, reason=reason)
            
            message = f"{member.mention} has been muted for {duration} minutes due to: {reason}"
            if fine_amount > 0:
                status = "Applied" if fine_applied else "Failed/Partial"
                message += f"\nAdditional fine: {humanize_number(fine_amount)} Beri ({status})"
            await self.safe_send_message(ctx.channel, message)
        except discord.Forbidden:
            await self.safe_send_message(ctx.channel, "I don't have permission to manage roles for this member.")
            return
        
        # Log action
        extra_fields = [{"name": "Duration", "value": f"{duration} minutes"}]
        if fine_amount > 0:
            extra_fields.append({"name": "Additional Fine", "value": f"{humanize_number(fine_amount)} Beri"})
        await self.log_action(ctx.guild, "Auto-Mute", member, self.bot.user, reason, extra_fields=extra_fields)

    async def _apply_timeout_action(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: int,
        reason: str,
        fine_amount: int,
        fine_applied: bool
    ) -> None:
        """Apply timeout action."""
        until = self._get_current_time() + timedelta(minutes=duration)
        await member.timeout(until=until, reason=reason)
        
        message = f"{member.mention} has been timed out for {duration} minutes due to: {reason}"
        if fine_amount > 0:
            status = "Applied" if fine_applied else "Failed/Partial"
            message += f"\nAdditional fine: {humanize_number(fine_amount)} Beri ({status})"
        await self.safe_send_message(ctx.channel, message)
        
        extra_fields = [{"name": "Duration", "value": f"{duration} minutes"}]
        if fine_amount > 0:
            extra_fields.append({"name": "Additional Fine", "value": f"{humanize_number(fine_amount)} Beri"})
        await self.log_action(ctx.guild, "Auto-Timeout", member, self.bot.user, reason, extra_fields=extra_fields)

    async def _apply_kick_action(
        self,
        ctx: commands.Context,
        member: discord.Member,
        reason: str,
        fine_amount: int,
        fine_applied: bool
    ) -> None:
        """Apply kick action."""
        await member.kick(reason=reason)
        
        message = f"{member.mention} has been kicked due to: {reason}"
        if fine_amount > 0:
            status = "Applied" if fine_applied else "Failed/Partial"
            message += f"\nFine applied: {humanize_number(fine_amount)} Beri ({status})"
        await self.safe_send_message(ctx.channel, message)
        
        extra_fields = []
        if fine_amount > 0:
            extra_fields.append({"name": "Fine", "value": f"{humanize_number(fine_amount)} Beri"})
        await self.log_action(ctx.guild, "Auto-Kick", member, self.bot.user, reason, extra_fields=extra_fields)

    async def _apply_ban_action(
        self,
        ctx: commands.Context,
        member: discord.Member,
        reason: str,
        fine_amount: int,
        fine_applied: bool
    ) -> None:
        """Apply ban action."""
        await member.ban(reason=reason)
        
        message = f"{member.mention} has been banned due to: {reason}"
        if fine_amount > 0:
            status = "Applied" if fine_applied else "Failed/Partial"
            message += f"\nFine applied: {humanize_number(fine_amount)} Beri ({status})"
        await self.safe_send_message(ctx.channel, message)
        
        extra_fields = []
        if fine_amount > 0:
            extra_fields.append({"name": "Fine", "value": f"{humanize_number(fine_amount)} Beri"})
        await self.log_action(ctx.guild, "Auto-Ban", member, self.bot.user, reason, extra_fields=extra_fields)

    # ========== MUTE COMMANDS ==========

    @commands.command(name="quiet")
    @checks.mod_or_permissions(manage_roles=True)
    async def mute_member(
        self, 
        ctx: commands.Context, 
        member: discord.Member, 
        duration: int = 30, 
        *, 
        reason: Optional[str] = None
    ) -> None:
        """
        Mute a member for the specified duration (in minutes).
        Includes additional Beri fine.
        """
        if member.guild_permissions.kick_members or member.guild_permissions.administrator:
            return await ctx.send(f"Cannot mute {member.mention} - they have moderator/admin permissions.")
            
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send(f"Cannot mute {member.mention} - their role is above or equal to mine.")
        
        mute_role_id = await self.config.guild(ctx.guild).mute_role()
        if not mute_role_id:
            return await ctx.send(f"Mute role not set. Use {ctx.clean_prefix}cautionset mute first.")
        
        mute_role = ctx.guild.get_role(mute_role_id)
        if not mute_role:
            return await ctx.send(f"Mute role not found. Use {ctx.clean_prefix}cautionset mute to create one.")
        
        # Apply Beri fine
        core = self._core()
        fine_amount = 0
        fine_applied = True
        if core:
            guild_config = await self.config.guild(ctx.guild).all()
            fine_amount = guild_config.get("mute_fine", 5000)
            if fine_amount > 0:
                fine_applied = await self._apply_beri_fine(
                    member, 
                    fine_amount, 
                    FINE_REASON_MANUAL_MUTE, 
                    ctx.author
                )
        
        # Check if already muted
        if mute_role in member.roles:
            muted_until = self._get_current_time() + timedelta(minutes=duration)
            await self.config.member(member).muted_until.set(muted_until.timestamp())
            message = f"{member.mention} was already muted. Updated duration to {duration} minutes."
            if fine_amount > 0:
                status = "Applied" if fine_applied else "Failed/Partial"
                message += f"\nAdditional fine: {humanize_number(fine_amount)} Beri ({status})"
            await ctx.send(message)
            return
            
        # Apply mute
        try:
            await member.add_roles(mute_role, reason=f"Manual mute: {reason}")
            
            # Also timeout as backup
            try:
                timeout_duration = timedelta(minutes=duration)
                await member.timeout(timeout_duration, reason=f"Manual mute: {reason}")
            except Exception as e:
                log.error(f"Could not apply timeout to {member.id}: {e}")
                
            # Set muted_until
            muted_until = self._get_current_time() + timedelta(minutes=duration)
            await self.config.member(member).muted_until.set(muted_until.timestamp())
            
            message = f"{member.mention} has been muted for {duration} minutes. Reason: {reason or 'No reason provided'}"
            if fine_amount > 0:
                status = "Applied" if fine_applied else "Failed/Partial"
                message += f"\nFine applied: {humanize_number(fine_amount)} Beri ({status})"
            await ctx.send(message)
                
            # Log
            extra_fields = [{"name": "Duration", "value": f"{duration} minutes"}]
            if fine_amount > 0:
                extra_fields.append({"name": "Fine", "value": f"{humanize_number(fine_amount)} Beri"})
            await self.log_action(ctx.guild, "Mute", member, ctx.author, reason, extra_fields=extra_fields)
                
        except discord.Forbidden:
            await ctx.send("I don't have permission to manage roles for this member.")
        except Exception as e:
            await ctx.send(f"Error applying mute: {str(e)}")
            log.error(f"Error in mute_member: {e}", exc_info=True)

    @commands.command(name="unquiet")
    @checks.mod_or_permissions(manage_roles=True)
    async def unmute_member(self, ctx: commands.Context, member: discord.Member) -> None:
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

    async def restore_member_roles(
        self, 
        guild: discord.Guild, 
        member: discord.Member
    ) -> None:
        """Restore a member's roles after unmuting."""
        try:
            mute_role_id = await self.config.guild(guild).mute_role()
            mute_role = guild.get_role(mute_role_id) if mute_role_id else None
            
            if mute_role and mute_role in member.roles:
                await member.remove_roles(mute_role, reason="Unmuting member")
                
                # Remove timeout
                try:
                    await member.timeout(None, reason="Unmuting member")
                except Exception as e:
                    log.error(f"Error removing timeout: {e}")
            
            # Clear mute data
            await self.config.member(member).muted_until.set(None)
            
            # Verify removal
            if mute_role and mute_role in member.roles:
                log.error(f"Failed to remove mute role from {member.id}")
                try:
                    await member.remove_roles(mute_role, reason="Retry: Unmuting member")
                except Exception as e:
                    log.error(f"Second attempt failed: {e}")
            
            # Log
            log_channel_id = await self.config.guild(guild).log_channel()
            if log_channel_id:
                log_channel = guild.get_channel(log_channel_id)
                if log_channel:
                    await self.safe_send_message(log_channel, f"{member.mention} has been unmuted.")
            
        except Exception as e:
            log.error(f"Error restoring member roles: {e}", exc_info=True)

    @commands.command(name="setupmute")
    @checks.admin_or_permissions(administrator=True)
    async def setup_mute_role(self, ctx: commands.Context) -> None:
        """Set up the muted role for the server with proper permissions."""
        try:
            # Delete existing mute role
            existing_mute_role_id = await self.config.guild(ctx.guild).mute_role()
            if existing_mute_role_id:
                existing_role = ctx.guild.get_role(existing_mute_role_id)
                if existing_role:
                    try:
                        await existing_role.delete(reason="Recreating mute role")
                        await ctx.send("Deleted existing mute role.")
                    except Exception as e:
                        await ctx.send(f"Error deleting existing role: {e}")
            
            # Create new mute role
            mute_role = await ctx.guild.create_role(
                name="Muted", 
                reason="Setup for moderation",
                permissions=discord.Permissions.none()
            )
            
            # Position role
            bot_member = ctx.guild.me
            highest_bot_role = max(
                [r for r in bot_member.roles if not r.is_default()], 
                key=lambda r: r.position
            )
            
            try:
                positions = {mute_role: highest_bot_role.position - 1}
                await ctx.guild.edit_role_positions(positions)
            except Exception as e:
                log.error(f"Error positioning mute role: {e}")
            
            # Save to config
            await self.config.guild(ctx.guild).mute_role.set(mute_role.id)
            
            status_msg = await ctx.send("Setting up permissions... This may take a moment.")
            
            # Set permissions for categories
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
                        connect=False
                    )
                except Exception as e:
                    log.error(f"Error setting permissions for category {category.name}: {e}")
            
            # Set for all text channels
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
                    log.error(f"Error for text channel {channel.name}: {e}")
            
            # Set for voice channels
            for channel in ctx.guild.voice_channels:
                try:
                    await channel.set_permissions(
                        mute_role,
                        speak=False,
                        connect=False
                    )
                except Exception as e:
                    log.error(f"Error for voice channel {channel.name}: {e}")
            
            await status_msg.edit(content=f"Mute role setup complete! {mute_role.mention} configured.")
            
        except Exception as e:
            await ctx.send(f"Failed to set up mute role: {str(e)}")
            log.error(f"Error in setup_mute_role: {e}", exc_info=True)

    # ========== VIEW/MANAGE WARNINGS ==========

    @commands.command(name="cautions")
    async def list_warnings(
        self, 
        ctx: commands.Context, 
        member: Optional[discord.Member] = None
    ) -> None:
        """List all active warnings for a member."""
        if member is None:
            member = ctx.author
        
        if member != ctx.author and not ctx.author.guild_permissions.kick_members:
            return await ctx.send("You don't have permission to view other members' warnings.")
        
        warnings = await self.config.member(member).warnings()
        total_points = await self.config.member(member).total_points()
        total_fines = await self.config.member(member).total_fines_paid()
        
        if not warnings:
            return await ctx.send(f"{member.mention} has no active warnings.")
        
        embed = discord.Embed(title=f"Warnings for {member.display_name}", color=0xff9900)
        embed.add_field(name="Total Points", value=str(total_points))
        embed.add_field(name="Total Fines Paid", value=f"{humanize_number(total_fines)} Beri")
        
        for i, warning in enumerate(warnings, start=1):
            moderator = ctx.guild.get_member(warning.get("moderator_id"))
            moderator_mention = moderator.mention if moderator else "Unknown Moderator"
            
            timestamp = warning.get("timestamp", 0)
            issued_time = f"<t:{int(timestamp)}:R>"
            
            expiry = warning.get("expiry", 0)
            expiry_time = f"<t:{int(expiry)}:R>"
            
            value = f"**Points:** {warning.get('points', 1)}\n"
            value += f"**Reason:** {warning.get('reason', 'No reason provided')}\n"
            value += f"**Moderator:** {moderator_mention}\n"
            value += f"**Issued:** {issued_time}\n"
            value += f"**Expires:** {expiry_time}\n"
            
            fine_amount = warning.get("fine_amount", 0)
            if fine_amount > 0:
                fine_applied = warning.get("fine_applied", False)
                value += f"**Fine:** {humanize_number(fine_amount)} Beri {'(Applied)' if fine_applied else '(Failed/Partial)'}"
            
            embed.add_field(name=f"Warning #{i}", value=value, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="clearcautions")
    @checks.mod_or_permissions(kick_members=True)
    async def clear_warnings(self, ctx: commands.Context, member: discord.Member) -> None:
        """Clear all warnings from a member."""
        warnings = await self.config.member(member).warnings()
        
        if warnings:
            await self.config.member(member).warnings.set([])
            await self.config.member(member).total_points.set(0)
            await self.config.member(member).applied_thresholds.set([])
            
            await ctx.send(f"All warnings for {member.mention} have been cleared.")
            await self.log_action(
                ctx.guild, 
                "Clear Warnings", 
                member, 
                ctx.author, 
                "Manual clearing of all warnings"
            )
        else:
            await ctx.send(f"{member.mention} has no warnings to clear.")

    @commands.command(name="removecaution")
    @checks.mod_or_permissions(kick_members=True)
    async def remove_warning(
        self, 
        ctx: commands.Context, 
        member: discord.Member, 
        warning_index: int
    ) -> None:
        """Remove a specific warning by index. Use cautions command to see indexes."""
        if warning_index < 1:
            return await ctx.send("Warning index must be 1 or higher.")
        
        async with self.config.member(member).warnings() as warnings:
            if not warnings:
                return await ctx.send(f"{member.mention} has no warnings.")
            
            if warning_index > len(warnings):
                return await ctx.send(f"Invalid index. {member.mention} only has {len(warnings)} warnings.")
            
            # Remove warning (adjust for 0-based index)
            removed_warning = warnings.pop(warning_index - 1)
        
        # Recalculate total points
        async with self.config.member(member).warnings() as warnings:
            total_points = sum(w.get("points", 1) for w in warnings)
            await self.config.member(member).total_points.set(total_points)
        
        await ctx.send(f"Warning #{warning_index} for {member.mention} has been removed.")
        
        # Log action
        extra_fields = [
            {"name": "Warning Points", "value": str(removed_warning.get("points", 1))},
            {"name": "Warning Reason", "value": removed_warning.get("reason", "No reason provided")},
            {"name": "New Total Points", "value": str(total_points)}
        ]
        
        fine_amount = removed_warning.get("fine_amount", 0)
        if fine_amount > 0:
            extra_fields.append({"name": "Fine Amount", "value": f"{humanize_number(fine_amount)} Beri"})
        
        await self.log_action(
            ctx.guild, 
            "Remove Warning", 
            member, 
            ctx.author, 
            f"Manually removed warning #{warning_index}",
            extra_fields=extra_fields
        )

    @commands.command(name="fineinfo")
    async def fine_info(
        self, 
        ctx: commands.Context, 
        member: Optional[discord.Member] = None
    ) -> None:
        """Show fine information for a member."""
        if member is None:
            member = ctx.author
        
        if member != ctx.author and not ctx.author.guild_permissions.kick_members:
            return await ctx.send("You don't have permission to view other members' fine information.")
        
        core = self._core()
        if not core:
            return await ctx.send("BeriCore is not loaded - fine information unavailable.")
        
        member_data = await self.config.member(member).all()
        total_fines = member_data.get("total_fines_paid", 0)
        warning_count = member_data.get("warning_count", 0)
        current_balance = await core.get_beri(member)
        
        is_exempt = await self._is_fine_exempt(member)
        
        guild_config = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(title=f"Fine Information for {member.display_name}", color=0x00aeef)
        embed.add_field(name="Current Beri Balance", value=f"{humanize_number(current_balance)} Beri", inline=True)
        embed.add_field(name="Total Fines Paid", value=f"{humanize_number(total_fines)} Beri", inline=True)
        embed.add_field(name="Warning Count", value=str(warning_count), inline=True)
        embed.add_field(name="Fine Exempt", value="Yes" if is_exempt else "No", inline=True)
        
        if not is_exempt:
            next_fine = await self._calculate_warning_fine(member, 1)
            embed.add_field(name="Next Warning Fine (1pt)", value=f"{humanize_number(next_fine)} Beri", inline=True)
        
        fine_info = f"**Warning Base:** {humanize_number(guild_config.get('warning_fine_base', 1000))} Beri\n"
        fine_info += f"**Escalation Multiplier:** {guild_config.get('warning_fine_multiplier', 1.5)}x\n"
        fine_info += f"**Mute Fine:** {humanize_number(guild_config.get('mute_fine', 5000))} Beri\n"
        fine_info += f"**Timeout Fine:** {humanize_number(guild_config.get('timeout_fine', 3000))} Beri\n"
        fine_info += f"**Kick Fine:** {humanize_number(guild_config.get('kick_fine', 10000))} Beri\n"
        fine_info += f"**Ban Fine:** {humanize_number(guild_config.get('ban_fine', 25000))} Beri"
        
        embed.add_field(name="Current Fine Rates", value=fine_info, inline=False)
        
        await ctx.send(embed=embed)

    # ========== LOGGING ==========

    async def log_action(
        self, 
        guild: discord.Guild, 
        action: str, 
        target: discord.Member, 
        moderator: Union[discord.Member, discord.User], 
        reason: Optional[str] = None, 
        extra_fields: Optional[List[Dict[str, str]]] = None
    ) -> Optional[discord.Message]:
        """Log moderation actions to the log channel in a case-based format."""
        log_channel_id = await self.config.guild(guild).log_channel()
        if not log_channel_id:
            return None
        
        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return None
        
        # Get and increment case number
        case_num = await self.config.guild(guild).case_count()
        if case_num is None:
            case_num = 1
        else:
            case_num += 1
        
        await self.config.guild(guild).case_count.set(case_num)
        
        # Create embed
        embed = discord.Embed(color=0x2f3136)
        embed.set_author(name=f"{guild.me.display_name}", icon_url=guild.me.display_avatar.url)
        embed.title = f"Case #{case_num}"
        
        # Build description
        current_time = self._get_current_time()
        embed.description = (
            f"**Action:** {action}\n"
            f"**User:** {target.mention} ( {target.id} )\n"
            f"**Moderator:** {moderator.mention} ( {moderator.id} )\n"
            f"**Reason:** {reason or 'No reason provided'}\n"
            f"**Date:** {current_time.strftime('%b %d, %Y %I:%M %p')} (just now)"
        )
        
        # Add extra fields
        if extra_fields:
            for field in extra_fields:
                if field and field.get("name") and field.get("value"):
                    embed.description += f"\n**{field['name']}:** {field['value']}"
        
        # Add footer
        embed.set_footer(text=f"{guild.me.display_name} Support • Today at {current_time.strftime('%I:%M %p')}")
        
        # Create view with buttons
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="View All Cautions",
            custom_id=f"cautions_view_{target.id}",
        ))
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Clear All Cautions",
            custom_id=f"cautions_clear_{target.id}",
        ))
        
        # Send message
        try:
            case_message = await log_channel.send(embed=embed, view=view)
        except discord.HTTPException as e:
            log.error(f"Error sending embed with buttons: {e}")
            try:
                case_message = await log_channel.send(embed=embed)
            except discord.HTTPException as e2:
                log.error(f"Error sending embed without buttons: {e2}")
                case_message = None
        
        # Save to modlog
        if case_message:
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
                    "timestamp": current_time.timestamp(),
                    "message_id": case_message.id
                }
            )
        
        return case_message

    # ========== EVENT HANDLERS ==========

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        """Handle button interactions for moderation actions."""
        if not interaction.data or not interaction.data.get("custom_id"):
            return
            
        custom_id = interaction.data["custom_id"]
        
        # Handle cautions view button
        if custom_id.startswith("cautions_view_"):
            await self._handle_view_cautions(interaction, custom_id)
        
        # Handle cautions clear button
        elif custom_id.startswith("cautions_clear_"):
            await self._handle_clear_cautions(interaction, custom_id)

    async def _handle_view_cautions(
        self, 
        interaction: discord.Interaction, 
        custom_id: str
    ) -> None:
        """Handle the view cautions button."""
        try:
            user_id = int(custom_id.split("_")[-1])
            member = interaction.guild.get_member(user_id)
            
            if not member:
                await interaction.response.send_message(
                    "Member not found or has left the server.", 
                    ephemeral=True
                )
                return
            
            if not interaction.user.guild_permissions.kick_members:
                await interaction.response.send_message(
                    "You don't have permission to view warnings.", 
                    ephemeral=True
                )
                return
            
            warnings = await self.config.member(member).warnings()
            total_points = await self.config.member(member).total_points()
            total_fines = await self.config.member(member).total_fines_paid()
            
            if not warnings:
                await interaction.response.send_message(
                    f"{member.mention} has no active warnings.", 
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(title=f"Warnings for {member.display_name}", color=0xff9900)
            embed.add_field(name="Total Points", value=str(total_points))
            embed.add_field(name="Total Fines Paid", value=f"{humanize_number(total_fines)} Beri")
            
            # Show max 10 warnings
            for i, warning in enumerate(warnings[:10], start=1):
                moderator = interaction.guild.get_member(warning.get("moderator_id"))
                moderator_mention = moderator.mention if moderator else "Unknown Moderator"
                
                timestamp = warning.get("timestamp", 0)
                issued_time = f"<t:{int(timestamp)}:R>"
                
                expiry = warning.get("expiry", 0)
                expiry_time = f"<t:{int(expiry)}:R>"
                
                value = f"**Points:** {warning.get('points', 1)}\n"
                value += f"**Reason:** {warning.get('reason', 'No reason provided')[:50]}...\n"
                value += f"**Moderator:** {moderator_mention}\n"
                value += f"**Issued:** {issued_time}\n"
                value += f"**Expires:** {expiry_time}\n"
                
                fine_amount = warning.get("fine_amount", 0)
                if fine_amount > 0:
                    fine_applied = warning.get("fine_applied", False)
                    value += f"**Fine:** {humanize_number(fine_amount)} Beri {'✓' if fine_applied else '✗'}"
                
                embed.add_field(name=f"Warning #{i}", value=value, inline=False)
            
            if len(warnings) > 10:
                embed.add_field(
                    name="Note", 
                    value=f"Showing 10 of {len(warnings)} warnings. Use the cautions command to see all.", 
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"Error processing request: {str(e)}", 
                ephemeral=True
            )

    async def _handle_clear_cautions(
        self, 
        interaction: discord.Interaction, 
        custom_id: str
    ) -> None:
        """Handle the clear cautions button."""
        try:
            user_id = int(custom_id.split("_")[-1])
            member = interaction.guild.get_member(user_id)
            
            if not member:
                await interaction.response.send_message(
                    "Member not found or has left the server.", 
                    ephemeral=True
                )
                return
            
            if not interaction.user.guild_permissions.kick_members:
                await interaction.response.send_message(
                    "You don't have permission to clear warnings.", 
                    ephemeral=True
                )
                return
            
            warnings = await self.config.member(member).warnings()
            
            if not warnings:
                await interaction.response.send_message(
                    f"{member.mention} has no warnings to clear.", 
                    ephemeral=True
                )
                return
            
            # Clear warnings
            await self.config.member(member).warnings.set([])
            await self.config.member(member).total_points.set(0)
            await self.config.member(member).applied_thresholds.set([])
            
            # Log action
            await self.log_action(
                interaction.guild, 
                "Clear Warnings", 
                member, 
                interaction.user, 
                "Cleared via button interaction"
            )
            
            await interaction.response.send_message(
                f"All warnings for {member.mention} have been cleared.", 
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"Error processing request: {str(e)}", 
                ephemeral=True
            )

    # ========== ERROR HANDLING ==========

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """Handle command errors."""
        if hasattr(ctx.command, 'on_error'):
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
            log.error(f"Command error in {ctx.command}: {error}", exc_info=True)

    # ========== UTILITY COMMANDS ==========

    @commands.command(name="testmute")
    @checks.admin_or_permissions(administrator=True)
    async def test_mute_setup(self, ctx: commands.Context) -> None:
        """Test if the mute role is properly set up."""
        try:
            mute_role_id = await self.config.guild(ctx.guild).mute_role()
            
            if not mute_role_id:
                return await ctx.send(f"No mute role configured. Use {ctx.clean_prefix}setupmute first.")
            
            mute_role = ctx.guild.get_role(mute_role_id)
            if not mute_role:
                return await ctx.send(f"Mute role not found. Use {ctx.clean_prefix}setupmute again.")
            
            # Check role position
            bot_position = ctx.guild.me.top_role.position
            mute_position = mute_role.position
            
            if mute_position < bot_position - 1:
                await ctx.send(f"Warning: Mute role position ({mute_position}) is not directly below bot's highest role ({bot_position})")
            else:
                await ctx.send(f"Mute role position ({mute_position}) looks good relative to bot's highest role ({bot_position})")
            
            # Check permissions
            text_channels_checked = 0
            text_channels_with_issues = 0
            voice_channels_checked = 0
            voice_channels_with_issues = 0
            
            for channel in ctx.guild.text_channels[:5]:
                text_channels_checked += 1
                perms = channel.permissions_for(mute_role)
                if perms.send_messages:
                    text_channels_with_issues += 1
            
            for channel in ctx.guild.voice_channels[:5]:
                voice_channels_checked += 1
                perms = channel.permissions_for(mute_role)
                if perms.speak:
                    voice_channels_with_issues += 1
            
            # Report results
            if text_channels_with_issues > 0:
                await ctx.send(f"Issues in {text_channels_with_issues}/{text_channels_checked} text channels - mute role can still send messages")
            else:
                await ctx.send(f"Text channel permissions look good for {text_channels_checked} channels checked")
            
            if voice_channels_with_issues > 0:
                await ctx.send(f"Issues in {voice_channels_with_issues}/{voice_channels_checked} voice channels - mute role can still speak")
            else:
                await ctx.send(f"Voice channel permissions look good for {voice_channels_checked} channels checked")
            
            # Overall assessment
            if text_channels_with_issues == 0 and voice_channels_with_issues == 0:
                await ctx.send("✅ Mute role appears to be correctly configured!")
            else:
                await ctx.send(f"⚠️ Mute role has issues - please run {ctx.clean_prefix}setupmute again")
            
        except Exception as e:
            await ctx.send(f"Error testing mute setup: {str(e)}")
            log.error(f"Error in test_mute_setup: {e}", exc_info=True)


# ========== COG SETUP ==========

async def setup(bot: Red) -> None:
    """Load the BeriCautions cog."""
    await bot.add_cog(BeriCautions(bot))
            
