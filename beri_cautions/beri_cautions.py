"""
BeriCautions - Modern Refactored Version
Enhanced moderation cog with point-based warning system and Beri economy integration.

Features:
- Point-based warning system with auto-expiry
- Threshold-based automated actions (mute, timeout, kick, ban)
- Integration with Beri economy for fines
- Comprehensive modlog with case tracking
- Slash command support with modern UI
- Background task management for cleanup and mute tracking
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any

import discord
from discord import app_commands
from redbot.core import Config, commands, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import (
    humanize_number,
    humanize_timedelta,
    box,
    pagify,
)
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

log = logging.getLogger("red.bericautions")

# Constants
DEFAULT_WARNING_EXPIRY_DAYS = 30
DEFAULT_ACTION_THRESHOLDS = {
    "3": {"action": "mute", "duration": 30, "reason": "Exceeded 3 warning points"},
    "5": {"action": "timeout", "duration": 60, "reason": "Exceeded 5 warning points"},
    "10": {"action": "kick", "reason": "Exceeded 10 warning points"},
}

WARNING_CLEANUP_INTERVAL = 21600  # 6 hours
MUTE_CHECK_INTERVAL = 60  # 1 minute


class BeriCautions(commands.Cog):
    """Enhanced moderation with point-based warnings and Beri economy integration."""

    __version__ = "2.0.0"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=3487613988, force_registration=True
        )

        # Register default configuration
        self.config.register_guild(
            log_channel=None,
            mute_role=None,
            warning_expiry_days=DEFAULT_WARNING_EXPIRY_DAYS,
            action_thresholds=DEFAULT_ACTION_THRESHOLDS,
            case_count=0,
            modlog={},
            warning_fine_base=1000,
            warning_fine_multiplier=1.5,
            mute_fine=5000,
            timeout_fine=3000,
            kick_fine=10000,
            ban_fine=25000,
            fine_exempt_roles=[],
            max_fine_per_action=50000,
        )

        self.config.register_member(
            warnings=[],
            total_points=0,
            muted_until=None,
            applied_thresholds=[],
            total_fines_paid=0,
            warning_count=0,
        )

        # Internal state
        self._member_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._tasks: list[asyncio.Task] = []

    async def cog_load(self) -> None:
        """Called when the cog is loaded."""
        self._tasks = [
            asyncio.create_task(self._warning_cleanup_loop()),
            asyncio.create_task(self._mute_check_loop()),
        ]
        log.info("BeriCautions loaded successfully")

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        for task in self._tasks:
            task.cancel()
        log.info("BeriCautions unloaded")

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Show version in help."""
        return f"{super().format_help_for_context(ctx)}\n\nVersion: {self.__version__}"

    # ========== CORE UTILITIES ==========

    @property
    def _core(self) -> Optional[commands.Cog]:
        """Get BeriCore instance."""
        return self.bot.get_cog("BeriCore")

    def _now(self) -> datetime:
        """Get current UTC time."""
        return datetime.now(timezone.utc)

    def _timestamp(self) -> float:
        """Get current Unix timestamp."""
        return self._now().timestamp()

    async def _get_member_lock(self, member_id: int) -> asyncio.Lock:
        """Get lock for member to prevent race conditions."""
        return self._member_locks[member_id]

    # ========== FINE HANDLING ==========

    async def _is_fine_exempt(self, member: discord.Member) -> bool:
        """Check if member is exempt from fines."""
        exempt_roles = await self.config.guild(member.guild).fine_exempt_roles()
        return any(role.id in exempt_roles for role in member.roles)

    async def _calculate_warning_fine(
        self, member: discord.Member, points: int
    ) -> int:
        """Calculate fine for a warning based on points and history."""
        guild_config = await self.config.guild(member.guild).all()
        member_data = await self.config.member(member).all()

        base_fine = guild_config["warning_fine_base"]
        multiplier = guild_config["warning_fine_multiplier"]
        max_fine = guild_config["max_fine_per_action"]

        # Calculate base fine
        fine = base_fine * points

        # Apply escalation based on warning history
        warning_count = member_data["warning_count"]
        if warning_count > 0:
            escalation = multiplier ** min(warning_count, 5)
            fine = int(fine * escalation)

        return min(fine, max_fine)

    async def _apply_beri_fine(
        self,
        member: discord.Member,
        amount: int,
        reason: str,
        moderator: Union[discord.Member, discord.User],
    ) -> bool:
        """Apply a Beri fine to a member. Returns True if successful."""
        if not self._core or await self._is_fine_exempt(member):
            return True

        try:
            current_balance = await self._core.get_beri(member)

            if current_balance >= amount:
                await self._core.add_beri(
                    member,
                    -amount,
                    reason=f"fine:{reason}",
                    actor=moderator,
                    bypass_cap=True,
                )
                await self._update_member_fines(member, amount)
                return True
            else:
                # Partial payment
                if current_balance > 0:
                    await self._core.add_beri(
                        member,
                        -current_balance,
                        reason=f"partial_fine:{reason}",
                        actor=moderator,
                        bypass_cap=True,
                    )
                    await self._update_member_fines(member, current_balance)
                return False

        except Exception as e:
            log.error(f"Failed to apply fine to {member}: {e}")
            return False

    async def _update_member_fines(self, member: discord.Member, amount: int) -> None:
        """Update member's total fines paid."""
        async with self.config.member(member).total_fines_paid() as total:
            total += amount

    # ========== WARNING MANAGEMENT ==========

    async def _add_warning(
        self,
        member: discord.Member,
        moderator: Union[discord.Member, discord.User],
        reason: str,
        points: int,
    ) -> dict[str, Any]:
        """Add a warning to a member with concurrency protection."""
        async with await self._get_member_lock(member.id):
            expiry_days = await self.config.guild(member.guild).warning_expiry_days()
            expiry = self._timestamp() + (expiry_days * 86400)

            warning = {
                "id": self._timestamp(),
                "timestamp": self._timestamp(),
                "expiry": expiry,
                "moderator_id": moderator.id,
                "reason": reason,
                "points": points,
                "fine_amount": 0,
                "fine_applied": False,
            }

            # Calculate and apply fine
            fine_amount = await self._calculate_warning_fine(member, points)
            if fine_amount > 0:
                fine_success = await self._apply_beri_fine(
                    member, fine_amount, f"warning:{reason}", moderator
                )
                warning["fine_amount"] = fine_amount
                warning["fine_applied"] = fine_success

            # Save warning
            async with self.config.member(member).warnings() as warnings:
                warnings.append(warning)

            # Update totals
            await self.config.member(member).total_points.set(
                await self._recalculate_points(member)
            )
            await self.config.member(member).warning_count.set(
                await self.config.member(member).warning_count() + 1
            )

            return warning

    async def _recalculate_points(self, member: discord.Member) -> int:
        """Recalculate active warning points for a member."""
        warnings = await self.config.member(member).warnings()
        current_time = self._timestamp()
        return sum(w["points"] for w in warnings if w["expiry"] > current_time)

    async def _clean_expired_warnings(self, member: discord.Member) -> int:
        """Remove expired warnings and return count removed."""
        current_time = self._timestamp()

        async with self.config.member(member).warnings() as warnings:
            before = len(warnings)
            warnings[:] = [w for w in warnings if w["expiry"] > current_time]
            removed = before - len(warnings)

        if removed > 0:
            await self.config.member(member).total_points.set(
                await self._recalculate_points(member)
            )

        return removed

    # ========== THRESHOLD ACTIONS ==========

    async def _check_and_apply_thresholds(
        self,
        member: discord.Member,
        moderator: Union[discord.Member, discord.User],
    ) -> None:
        """Check if member exceeded thresholds and apply actions."""
        total_points = await self.config.member(member).total_points()
        applied_thresholds = await self.config.member(member).applied_thresholds()
        action_thresholds = await self.config.guild(member.guild).action_thresholds()

        for threshold_str, config in sorted(
            action_thresholds.items(), key=lambda x: int(x[0])
        ):
            threshold = int(threshold_str)

            # Skip if already applied or not exceeded
            if threshold in applied_thresholds or total_points < threshold:
                continue

            action = config["action"]
            reason = config.get("reason", f"Exceeded {threshold} warning points")

            try:
                if action == "mute":
                    duration = config.get("duration", 30)
                    await self._mute_member(member, moderator, reason, duration)
                elif action == "timeout":
                    duration = config.get("duration", 60)
                    await self._timeout_member(member, moderator, reason, duration)
                elif action == "kick":
                    await self._kick_member(member, moderator, reason)
                elif action == "ban":
                    await self._ban_member(member, moderator, reason)

                # Mark threshold as applied
                async with self.config.member(
                    member
                ).applied_thresholds() as thresholds:
                    thresholds.append(threshold)

                await self._log_action(
                    member.guild,
                    f"Threshold Action ({action.title()})",
                    member,
                    moderator,
                    f"{reason} (Threshold: {threshold} points)",
                )

            except Exception as e:
                log.error(f"Failed to apply threshold action: {e}")

    # ========== MODERATION ACTIONS ==========

    async def _mute_member(
        self,
        member: discord.Member,
        moderator: Union[discord.Member, discord.User],
        reason: str,
        duration: int,
    ) -> None:
        """Mute a member using the mute role."""
        mute_role_id = await self.config.guild(member.guild).mute_role()
        if not mute_role_id:
            raise ValueError("Mute role not configured")

        mute_role = member.guild.get_role(mute_role_id)
        if not mute_role:
            raise ValueError("Mute role not found")

        await member.add_roles(mute_role, reason=reason)

        # Set unmute time
        unmute_time = self._timestamp() + (duration * 60)
        await self.config.member(member).muted_until.set(unmute_time)

        # Apply fine
        fine_amount = await self.config.guild(member.guild).mute_fine()
        await self._apply_beri_fine(member, fine_amount, f"mute:{reason}", moderator)

    async def _timeout_member(
        self,
        member: discord.Member,
        moderator: Union[discord.Member, discord.User],
        reason: str,
        duration: int,
    ) -> None:
        """Timeout a member using Discord's built-in timeout."""
        until = self._now() + timedelta(minutes=duration)
        await member.timeout(until, reason=reason)

        # Apply fine
        fine_amount = await self.config.guild(member.guild).timeout_fine()
        await self._apply_beri_fine(member, fine_amount, f"timeout:{reason}", moderator)

    async def _kick_member(
        self,
        member: discord.Member,
        moderator: Union[discord.Member, discord.User],
        reason: str,
    ) -> None:
        """Kick a member from the guild."""
        # Apply fine before kicking
        fine_amount = await self.config.guild(member.guild).kick_fine()
        await self._apply_beri_fine(member, fine_amount, f"kick:{reason}", moderator)

        await member.kick(reason=reason)

    async def _ban_member(
        self,
        member: discord.Member,
        moderator: Union[discord.Member, discord.User],
        reason: str,
    ) -> None:
        """Ban a member from the guild."""
        # Apply fine before banning
        fine_amount = await self.config.guild(member.guild).ban_fine()
        await self._apply_beri_fine(member, fine_amount, f"ban:{reason}", moderator)

        await member.ban(reason=reason, delete_message_seconds=0)

    # ========== MODLOG ==========

    async def _log_action(
        self,
        guild: discord.Guild,
        action_type: str,
        target: Union[discord.Member, discord.User],
        moderator: Union[discord.Member, discord.User],
        reason: str,
        **extra,
    ) -> int:
        """Log a moderation action and return case number."""
        case_num = await self.config.guild(guild).case_count() + 1
        await self.config.guild(guild).case_count.set(case_num)

        case_data = {
            "case_num": case_num,
            "timestamp": self._timestamp(),
            "action_type": action_type,
            "target_id": target.id,
            "target_name": str(target),
            "moderator_id": moderator.id,
            "moderator_name": str(moderator),
            "reason": reason,
            **extra,
        }

        async with self.config.guild(guild).modlog() as modlog:
            modlog[str(case_num)] = case_data

        # Send to log channel
        await self._send_log_message(guild, case_data)

        return case_num

    async def _send_log_message(
        self, guild: discord.Guild, case_data: dict[str, Any]
    ) -> None:
        """Send a log message to the configured log channel."""
        log_channel_id = await self.config.guild(guild).log_channel()
        if not log_channel_id:
            return

        log_channel = guild.get_channel(log_channel_id)
        if not log_channel or not isinstance(log_channel, discord.TextChannel):
            return

        embed = discord.Embed(
            title=f"Case #{case_data['case_num']} | {case_data['action_type']}",
            color=discord.Color.red(),
            timestamp=datetime.fromtimestamp(case_data["timestamp"], tz=timezone.utc),
        )

        embed.add_field(name="Target", value=case_data["target_name"], inline=True)
        embed.add_field(
            name="Moderator", value=case_data["moderator_name"], inline=True
        )
        embed.add_field(name="Reason", value=case_data["reason"], inline=False)

        # Add extra fields
        for key, value in case_data.items():
            if key not in [
                "case_num",
                "timestamp",
                "action_type",
                "target_id",
                "target_name",
                "moderator_id",
                "moderator_name",
                "reason",
            ]:
                embed.add_field(name=key.replace("_", " ").title(), value=str(value))

        try:
            await log_channel.send(embed=embed)
        except discord.HTTPException as e:
            log.error(f"Failed to send log message: {e}")

    # ========== BACKGROUND TASKS ==========

    async def _warning_cleanup_loop(self) -> None:
        """Background task to clean up expired warnings."""
        await self.bot.wait_until_red_ready()

        while True:
            try:
                await asyncio.sleep(WARNING_CLEANUP_INTERVAL)

                for guild in self.bot.guilds:
                    for member in guild.members:
                        try:
                            removed = await self._clean_expired_warnings(member)
                            if removed > 0:
                                log.debug(
                                    f"Cleaned {removed} expired warnings for {member}"
                                )
                        except Exception as e:
                            log.error(
                                f"Error cleaning warnings for {member}: {e}",
                                exc_info=True,
                            )

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in warning cleanup loop: {e}", exc_info=True)

    async def _mute_check_loop(self) -> None:
        """Background task to check and remove expired mutes."""
        await self.bot.wait_until_red_ready()

        while True:
            try:
                await asyncio.sleep(MUTE_CHECK_INTERVAL)
                current_time = self._timestamp()

                for guild in self.bot.guilds:
                    mute_role_id = await self.config.guild(guild).mute_role()
                    if not mute_role_id:
                        continue

                    mute_role = guild.get_role(mute_role_id)
                    if not mute_role:
                        continue

                    for member in guild.members:
                        if mute_role not in member.roles:
                            continue

                        muted_until = await self.config.member(member).muted_until()
                        if not muted_until or current_time < muted_until:
                            continue

                        try:
                            await member.remove_roles(
                                mute_role, reason="Mute duration expired"
                            )
                            await self.config.member(member).muted_until.set(None)
                            log.info(f"Unmuted {member} in {guild} (mute expired)")
                        except Exception as e:
                            log.error(f"Failed to unmute {member}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in mute check loop: {e}", exc_info=True)

    # ========== SETUP COMMANDS ==========

    @commands.group(name="cautionset", aliases=["warnset"])
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def caution_set(self, ctx: commands.Context):
        """Configure the cautions system."""

    @caution_set.command(name="logchannel")
    async def set_log_channel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        """Set the moderation log channel."""
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(f"Log channel set to {channel.mention}")

    @caution_set.command(name="setupmute")
    async def setup_mute_role(self, ctx: commands.Context):
        """Set up the mute role with proper permissions."""
        msg = await ctx.send("Setting up mute role...")

        # Create or get mute role
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            try:
                mute_role = await ctx.guild.create_role(
                    name="Muted",
                    color=discord.Color.dark_gray(),
                    reason="Cautions mute role setup",
                )
            except discord.HTTPException as e:
                return await ctx.send(f"Failed to create mute role: {e}")

        # Position role below bot's highest role
        try:
            await mute_role.edit(position=ctx.guild.me.top_role.position - 1)
        except discord.HTTPException:
            pass  # Role positioning is best-effort

        # Update channel permissions
        success_count = 0
        fail_count = 0

        for channel in ctx.guild.channels:
            try:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(
                        mute_role,
                        send_messages=False,
                        add_reactions=False,
                        create_public_threads=False,
                        create_private_threads=False,
                        send_messages_in_threads=False,
                    )
                elif isinstance(channel, discord.VoiceChannel):
                    await channel.set_permissions(mute_role, speak=False, stream=False)
                elif isinstance(channel, discord.ForumChannel):
                    await channel.set_permissions(
                        mute_role, send_messages=False, create_posts=False
                    )
                success_count += 1
            except discord.HTTPException:
                fail_count += 1

        await self.config.guild(ctx.guild).mute_role.set(mute_role.id)

        result_msg = (
            f"✅ Mute role setup complete!\n"
            f"Role: {mute_role.mention}\n"
            f"Channels updated: {success_count}\n"
        )
        if fail_count > 0:
            result_msg += f"⚠️ Failed to update {fail_count} channels"

        await msg.edit(content=result_msg)

    @caution_set.command(name="expiry")
    async def set_warning_expiry(self, ctx: commands.Context, days: int):
        """Set how many days warnings last (0 for never)."""
        if days < 0:
            return await ctx.send("Days must be 0 or greater.")

        await self.config.guild(ctx.guild).warning_expiry_days.set(days)
        if days == 0:
            await ctx.send("Warnings will never expire.")
        else:
            await ctx.send(f"Warnings will expire after {days} days.")

    @caution_set.group(name="fine")
    async def fine_settings(self, ctx: commands.Context):
        """Configure fine amounts for various actions."""

    @fine_settings.command(name="warning")
    async def set_warning_fine(self, ctx: commands.Context, base: int, multiplier: float = 1.5):
        """Set base warning fine and multiplier for repeat offenses."""
        if base < 0:
            return await ctx.send("Base fine must be 0 or greater.")
        if multiplier < 1.0:
            return await ctx.send("Multiplier must be 1.0 or greater.")

        await self.config.guild(ctx.guild).warning_fine_base.set(base)
        await self.config.guild(ctx.guild).warning_fine_multiplier.set(multiplier)
        await ctx.send(
            f"Warning fine set to {humanize_number(base)} Beri with {multiplier}x multiplier for repeat offenses."
        )

    @fine_settings.command(name="mute")
    async def set_mute_fine(self, ctx: commands.Context, amount: int):
        """Set fine amount for mutes."""
        if amount < 0:
            return await ctx.send("Amount must be 0 or greater.")

        await self.config.guild(ctx.guild).mute_fine.set(amount)
        await ctx.send(f"Mute fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="timeout")
    async def set_timeout_fine(self, ctx: commands.Context, amount: int):
        """Set fine amount for timeouts."""
        if amount < 0:
            return await ctx.send("Amount must be 0 or greater.")

        await self.config.guild(ctx.guild).timeout_fine.set(amount)
        await ctx.send(f"Timeout fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="kick")
    async def set_kick_fine(self, ctx: commands.Context, amount: int):
        """Set fine amount for kicks."""
        if amount < 0:
            return await ctx.send("Amount must be 0 or greater.")

        await self.config.guild(ctx.guild).kick_fine.set(amount)
        await ctx.send(f"Kick fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="ban")
    async def set_ban_fine(self, ctx: commands.Context, amount: int):
        """Set fine amount for bans."""
        if amount < 0:
            return await ctx.send("Amount must be 0 or greater.")

        await self.config.guild(ctx.guild).ban_fine.set(amount)
        await ctx.send(f"Ban fine set to {humanize_number(amount)} Beri.")

    # ========== MODERATION COMMANDS ==========

    @commands.command(name="warn", aliases=["caution", "cwarn"])
    @commands.guild_only()
    @checks.mod_or_permissions(kick_members=True)
    async def warn_member(
        self,
        ctx: commands.Context,
        member: discord.Member,
        points: int = 1,
        *,
        reason: str = "No reason provided",
    ):
        """Warn a member with a specified number of points."""
        if member.bot:
            return await ctx.send("Cannot warn bots.")

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("You cannot warn members with equal or higher roles.")

        if points < 1:
            return await ctx.send("Points must be at least 1.")

        try:
            warning = await self._add_warning(member, ctx.author, reason, points)

            # Log the warning
            case_num = await self._log_action(
                ctx.guild,
                "Warning",
                member,
                ctx.author,
                reason,
                points=points,
                fine_amount=warning["fine_amount"],
            )

            # Check thresholds
            await self._check_and_apply_thresholds(member, ctx.author)

            # Build response
            total_points = await self.config.member(member).total_points()
            response = f"⚠️ {member.mention} has been warned (Case #{case_num})\n"
            response += f"**Reason:** {reason}\n"
            response += f"**Points:** {points}\n"
            response += f"**Total Points:** {total_points}"

            if warning["fine_amount"] > 0:
                response += f"\n**Fine:** {humanize_number(warning['fine_amount'])} Beri"
                if not warning["fine_applied"]:
                    response += " (insufficient balance)"

            await ctx.send(response)

            # Try to DM the member
            try:
                dm_embed = discord.Embed(
                    title=f"Warning in {ctx.guild.name}",
                    description=f"You have been warned by {ctx.author.mention}",
                    color=discord.Color.orange(),
                    timestamp=self._now(),
                )
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Points", value=str(points), inline=True)
                dm_embed.add_field(name="Total Points", value=str(total_points), inline=True)

                if warning["fine_amount"] > 0:
                    dm_embed.add_field(
                        name="Fine",
                        value=f"{humanize_number(warning['fine_amount'])} Beri",
                        inline=True,
                    )

                await member.send(embed=dm_embed)
            except discord.HTTPException:
                pass

        except Exception as e:
            log.error(f"Error issuing warning: {e}", exc_info=True)
            await ctx.send(f"An error occurred while issuing the warning: {e}")

    @commands.command(name="warnings", aliases=["cautions", "mywarnings", "cwarnings"])
    @commands.guild_only()
    async def view_warnings(
        self, ctx: commands.Context, member: Optional[discord.Member] = None
    ):
        """View warnings for yourself or another member."""
        target = member or ctx.author

        # Permission check for viewing others
        if target != ctx.author:
            if not (ctx.author.guild_permissions.kick_members or await ctx.bot.is_owner(ctx.author)):
                return await ctx.send("You need Kick Members permission to view others' warnings.")

        warnings = await self.config.member(target).warnings()
        total_points = await self.config.member(target).total_points()
        total_fines = await self.config.member(target).total_fines_paid()

        if not warnings:
            return await ctx.send(f"{target.mention} has no warnings.")

        # Filter active warnings
        current_time = self._timestamp()
        active_warnings = [w for w in warnings if w["expiry"] > current_time]

        embed = discord.Embed(
            title=f"Warnings for {target.display_name}",
            color=discord.Color.orange(),
            timestamp=self._now(),
        )

        embed.add_field(name="Active Points", value=str(total_points), inline=True)
        embed.add_field(
            name="Total Warnings",
            value=f"{len(active_warnings)}/{len(warnings)}",
            inline=True,
        )
        embed.add_field(
            name="Total Fines",
            value=f"{humanize_number(total_fines)} Beri",
            inline=True,
        )

        # Show recent warnings
        for i, warning in enumerate(active_warnings[:5], 1):
            moderator = ctx.guild.get_member(warning["moderator_id"])
            mod_name = moderator.mention if moderator else "Unknown Moderator"

            value = f"**Points:** {warning['points']}\n"
            value += f"**Reason:** {warning['reason'][:100]}\n"
            value += f"**Moderator:** {mod_name}\n"
            value += f"**Issued:** <t:{int(warning['timestamp'])}:R>\n"
            value += f"**Expires:** <t:{int(warning['expiry'])}:R>"

            if warning["fine_amount"] > 0:
                value += f"\n**Fine:** {humanize_number(warning['fine_amount'])} Beri"

            embed.add_field(name=f"Warning #{i}", value=value, inline=False)

        if len(active_warnings) > 5:
            embed.set_footer(text=f"Showing 5 of {len(active_warnings)} active warnings")

        await ctx.send(embed=embed)

    @commands.command(name="clearwarnings", aliases=["clearwarns", "clearwarn", "cclear"])
    @commands.guild_only()
    @checks.mod_or_permissions(kick_members=True)
    async def clear_warnings(self, ctx: commands.Context, member: discord.Member):
        """Clear all warnings for a member."""
        warnings = await self.config.member(member).warnings()

        if not warnings:
            return await ctx.send(f"{member.mention} has no warnings to clear.")

        # Confirmation
        msg = await ctx.send(
            f"Are you sure you want to clear all {len(warnings)} warnings for {member.mention}?"
        )
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)

        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        try:
            await ctx.bot.wait_for("reaction_add", check=pred, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send("Cancelled.")

        if not pred.result:
            return await ctx.send("Cancelled.")

        # Clear warnings
        await self.config.member(member).warnings.set([])
        await self.config.member(member).total_points.set(0)
        await self.config.member(member).applied_thresholds.set([])

        await self._log_action(
            ctx.guild,
            "Clear Warnings",
            member,
            ctx.author,
            f"Cleared {len(warnings)} warnings",
        )

        await ctx.send(f"✅ Cleared all warnings for {member.mention}")

    @commands.command(name="removewarning", aliases=["removewarn", "delwarn", "delwarning"])
    @commands.guild_only()
    @checks.mod_or_permissions(kick_members=True)
    async def remove_warning(
        self, ctx: commands.Context, member: discord.Member, warning_number: int
    ):
        """Remove a specific warning by its number (use warnings command to see numbers)."""
        warnings = await self.config.member(member).warnings()

        if not warnings:
            return await ctx.send(f"{member.mention} has no warnings.")

        # Get active warnings
        current_time = self._timestamp()
        active_warnings = [w for w in warnings if w["expiry"] > current_time]

        if warning_number < 1 or warning_number > len(active_warnings):
            return await ctx.send(
                f"Invalid warning number. {member.mention} has {len(active_warnings)} active warnings. "
                f"Use `{ctx.clean_prefix}warnings {member.mention}` to see them."
            )

        # Get the warning to remove
        warning_to_remove = active_warnings[warning_number - 1]
        
        # Remove it from the full warnings list
        async with self.config.member(member).warnings() as all_warnings:
            all_warnings[:] = [w for w in all_warnings if w["id"] != warning_to_remove["id"]]

        # Recalculate points and check thresholds
        new_points = await self._recalculate_points(member)
        await self.config.member(member).total_points.set(new_points)

        # Reset applied thresholds if points dropped below any threshold
        applied_thresholds = await self.config.member(member).applied_thresholds()
        new_thresholds = [t for t in applied_thresholds if t <= new_points]
        await self.config.member(member).applied_thresholds.set(new_thresholds)

        # Log the action
        await self._log_action(
            ctx.guild,
            "Remove Warning",
            member,
            ctx.author,
            f"Removed warning #{warning_number}: {warning_to_remove['reason'][:100]}",
            points_removed=warning_to_remove["points"],
            new_total=new_points,
        )

        await ctx.send(
            f"✅ Removed warning #{warning_number} from {member.mention}\n"
            f"**Reason:** {warning_to_remove['reason'][:100]}\n"
            f"**Points removed:** {warning_to_remove['points']}\n"
            f"**New total:** {new_points} points"
        )

    @commands.command(name="cmute", aliases=["cautionmute"])
    @commands.guild_only()
    @checks.mod_or_permissions(kick_members=True)
    async def mute_user(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: int = 30,
        *,
        reason: str = "No reason provided",
    ):
        """Mute a member for a specified duration (in minutes)."""
        if member.bot:
            return await ctx.send("Cannot mute bots.")

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("You cannot mute members with equal or higher roles.")

        try:
            await self._mute_member(member, ctx.author, reason, duration)

            case_num = await self._log_action(
                ctx.guild,
                "Mute",
                member,
                ctx.author,
                reason,
                duration=f"{duration} minutes",
            )

            await ctx.send(
                f"🔇 {member.mention} has been muted for {duration} minutes (Case #{case_num})\n"
                f"**Reason:** {reason}"
            )

        except ValueError as e:
            await ctx.send(str(e))
        except Exception as e:
            log.error(f"Error muting member: {e}", exc_info=True)
            await ctx.send(f"An error occurred: {e}")

    @commands.command(name="cunmute", aliases=["cautionunmute"])
    @commands.guild_only()
    @checks.mod_or_permissions(kick_members=True)
    async def unmute_user(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"
    ):
        """Unmute a member."""
        mute_role_id = await self.config.guild(ctx.guild).mute_role()
        if not mute_role_id:
            return await ctx.send("Mute role not configured.")

        mute_role = ctx.guild.get_role(mute_role_id)
        if not mute_role or mute_role not in member.roles:
            return await ctx.send(f"{member.mention} is not muted.")

        try:
            await member.remove_roles(mute_role, reason=reason)
            await self.config.member(member).muted_until.set(None)

            await self._log_action(ctx.guild, "Unmute", member, ctx.author, reason)

            await ctx.send(f"🔊 {member.mention} has been unmuted.\n**Reason:** {reason}")

        except Exception as e:
            log.error(f"Error unmuting member: {e}", exc_info=True)
            await ctx.send(f"An error occurred: {e}")

    @commands.command(name="cautioncase", aliases=["ccase", "warncase"])
    @commands.guild_only()
    @checks.mod_or_permissions(kick_members=True)
    async def view_case(self, ctx: commands.Context, case_number: int):
        """View details of a specific caution case."""
        modlog = await self.config.guild(ctx.guild).modlog()
        case_data = modlog.get(str(case_number))

        if not case_data:
            return await ctx.send(f"Case #{case_number} not found.")

        embed = discord.Embed(
            title=f"Case #{case_number} | {case_data['action_type']}",
            color=discord.Color.red(),
            timestamp=datetime.fromtimestamp(case_data["timestamp"], tz=timezone.utc),
        )

        embed.add_field(name="Target", value=case_data["target_name"], inline=True)
        embed.add_field(name="Moderator", value=case_data["moderator_name"], inline=True)
        embed.add_field(name="Reason", value=case_data["reason"], inline=False)

        # Add extra fields
        for key, value in case_data.items():
            if key not in [
                "case_num",
                "timestamp",
                "action_type",
                "target_id",
                "target_name",
                "moderator_id",
                "moderator_name",
                "reason",
            ]:
                embed.add_field(name=key.replace("_", " ").title(), value=str(value))

        await ctx.send(embed=embed)

    @commands.command(name="testmute")
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def test_mute(self, ctx: commands.Context):
        """Test if the mute role is properly configured."""
        mute_role_id = await self.config.guild(ctx.guild).mute_role()

        if not mute_role_id:
            return await ctx.send(
                f"❌ No mute role configured. Use `{ctx.clean_prefix}cautionset setupmute` first."
            )

        mute_role = ctx.guild.get_role(mute_role_id)
        if not mute_role:
            return await ctx.send(
                f"❌ Mute role not found. Use `{ctx.clean_prefix}cautionset setupmute` again."
            )

        # Check role position
        bot_position = ctx.guild.me.top_role.position
        mute_position = mute_role.position

        embed = discord.Embed(title="Mute Role Configuration Test", color=discord.Color.blue())

        # Role information
        embed.add_field(name="Role", value=mute_role.mention, inline=True)
        embed.add_field(name="Position", value=f"{mute_position}/{bot_position}", inline=True)

        # Test channels
        text_checked = 0
        text_issues = 0
        voice_checked = 0
        voice_issues = 0

        for channel in ctx.guild.text_channels[:5]:
            text_checked += 1
            perms = channel.permissions_for(mute_role)
            if perms.send_messages:
                text_issues += 1

        for channel in ctx.guild.voice_channels[:5]:
            voice_checked += 1
            perms = channel.permissions_for(mute_role)
            if perms.speak:
                voice_issues += 1

        # Results
        text_status = "✅" if text_issues == 0 else "⚠️"
        voice_status = "✅" if voice_issues == 0 else "⚠️"

        embed.add_field(
            name=f"{text_status} Text Channels",
            value=f"{text_checked - text_issues}/{text_checked} properly configured",
            inline=True,
        )
        embed.add_field(
            name=f"{voice_status} Voice Channels",
            value=f"{voice_checked - voice_issues}/{voice_checked} properly configured",
            inline=True,
        )

        if text_issues == 0 and voice_issues == 0:
            embed.add_field(
                name="Status",
                value="✅ Mute role is properly configured!",
                inline=False,
            )
        else:
            embed.add_field(
                name="Status",
                value=f"⚠️ Issues detected. Run `{ctx.clean_prefix}cautionset setupmute` to fix.",
                inline=False,
            )

        await ctx.send(embed=embed)


async def setup(bot: Red) -> None:
    """Load the BeriCautions cog."""
    cog = BeriCautions(bot)
    await bot.add_cog(cog)
