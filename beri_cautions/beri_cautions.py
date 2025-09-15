# -*- coding: utf-8 -*-
"""
Beri Cautions
Enhanced moderation cog with point-based warnings, Beri economy fines, background tasks,
rate-limited messaging, modlog, action thresholds, AND hardened staff protections.

Adds:
- Staff-on-staff protection (perm- and role-based) with settings
- Role hierarchy guard (no equal-or-higher caution)
- Configurable max points per caution (cap)
- Threshold auto-actions skip protected staff
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, List, Dict, Tuple
from collections import deque

import discord
from redbot.core import Config, commands, checks
from redbot.core.bot import Red
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.chat_formatting import pagify, box, humanize_number

log = logging.getLogger("red.cogs.beri_cautions")

# ------------------------------
# Defaults
# ------------------------------
DEFAULT_WARNING_EXPIRY_DAYS = 30
DEFAULT_ACTION_THRESHOLDS = {
    "3": {"action": "mute", "duration": 30, "reason": "Exceeded 3 warning points"},
    "5": {"action": "timeout", "duration": 60, "reason": "Exceeded 5 warning points"},
    "10": {"action": "kick", "reason": "Exceeded 10 warning points"},
}

DEFAULT_GUILD = {
    "log_channel": None,
    "mute_role": None,
    "warning_expiry_days": DEFAULT_WARNING_EXPIRY_DAYS,
    "action_thresholds": DEFAULT_ACTION_THRESHOLDS,
    "case_count": 0,
    "modlog": {},
    # Beri integration
    "warning_fine_base": 1000,
    "warning_fine_multiplier": 1.5,
    "mute_fine": 5000,
    "timeout_fine": 3000,
    "kick_fine": 10000,
    "ban_fine": 25000,
    "fine_exempt_roles": [],
    "max_fine_per_action": 50000,
    # NEW: staff safety
    "staff_protection_enabled": True,
    "protected_role_ids": [],
    "max_points_per_caution": 10,
}

DEFAULT_MEMBER = {
    "warnings": [],
    "total_points": 0,
    "muted_until": None,
    "applied_thresholds": [],
    "total_fines_paid": 0,
    "warning_count": 0,
}

# ------------------------------
# Helpers
# ------------------------------
def role_rank(member: discord.Member) -> int:
    """Return a sortable rank for top role; owner treated as astronomical."""
    if member.guild.owner_id == member.id:
        return 10**9
    return member.top_role.position if member.top_role else 0


class BeriCautions(commands.Cog):
    """Enhanced moderation cog with Beri fines and staff protection."""

    __author__ = "UltPanda + ChatGPT"
    __version__ = "2.0.0-staff-protect"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=3487613988, force_registration=True)
        self.config.register_guild(**DEFAULT_GUILD)
        self.config.register_member(**DEFAULT_MEMBER)

        # Rate limiting protection
        self.rate_limit = {
            "message_queue": {},            # channel_id -> queue
            "command_cooldown": {},         # not used but preserved
            "global_cooldown": deque(maxlen=10),
        }

        # Background tasks
        self.warning_cleanup_task = self.bot.loop.create_task(self.warning_cleanup_loop())
        self.mute_check_task = self.bot.loop.create_task(self.mute_check_loop())

    def cog_unload(self):
        self.warning_cleanup_task.cancel()
        self.mute_check_task.cancel()

    # ------------------------------
    # Beri Core bridge
    # ------------------------------
    def _core(self):
        """Get BeriCore instance if present."""
        return self.bot.get_cog("BeriCore")

    async def _is_fine_exempt(self, member: discord.Member) -> bool:
        exempt_roles = await self.config.guild(member.guild).fine_exempt_roles()
        member_role_ids = {r.id for r in member.roles}
        return any(role_id in member_role_ids for role_id in exempt_roles)

    async def _calculate_warning_fine(self, member: discord.Member, points: int) -> int:
        """Escalating fine with caps based on history."""
        g = await self.config.guild(member.guild).all()
        m = await self.config.member(member).all()
        base = int(g.get("warning_fine_base", 1000))
        mult = float(g.get("warning_fine_multiplier", 1.5))
        maxfine = int(g.get("max_fine_per_action", 50000))
        fine = base * max(points, 1)
        warning_count = int(m.get("warning_count", 0))
        if warning_count > 0:
            fine = int(fine * (mult ** min(warning_count, 5)))
        return min(fine, maxfine)

    async def _apply_beri_fine(self, member: discord.Member, amount: int, reason: str, moderator: discord.Member) -> bool:
        """Attempt to deduct Beri; allow partial; update totals."""
        core = self._core()
        if not core:
            return False
        if await self._is_fine_exempt(member):
            return True
        try:
            current = await core.get_beri(member)
            if current >= amount:
                await core.add_beri(member, -amount, reason=f"fine:{reason}", actor=moderator, bypass_cap=True)
                async with self.config.member(member).all() as data:
                    data["total_fines_paid"] = data.get("total_fines_paid", 0) + amount
                return True
            else:
                if current > 0:
                    await core.add_beri(member, -current, reason=f"partial_fine:{reason}", actor=moderator, bypass_cap=True)
                    async with self.config.member(member).all() as data:
                        data["total_fines_paid"] = data.get("total_fines_paid", 0) + current
                return False
        except Exception as e:
            log.error(f"Error applying Beri fine: {e}", exc_info=True)
            return False

    # ------------------------------
    # Staff protection helpers
    # ------------------------------
    def _has_staff_perms(self, member: discord.Member) -> bool:
        p = member.guild_permissions
        return any([
            p.administrator,
            p.manage_guild,
            p.manage_messages,
            p.kick_members,
            p.ban_members,
            p.moderate_members,
        ])

    async def _is_protected_staff(self, member: discord.Member) -> bool:
        g = await self.config.guild(member.guild).all()
        if not g.get("staff_protection_enabled", True):
            return False
        if self._has_staff_perms(member):
            return True
        protected_ids = set(g.get("protected_role_ids", []))
        return any(r.id in protected_ids for r in member.roles)

    async def _cap_points(self, guild: discord.Guild, points: int) -> Tuple[int, Optional[int]]:
        g = await self.config.guild(guild).all()
        cap = max(1, int(g.get("max_points_per_caution", 10)))
        if points > cap:
            return cap, cap
        return points, None

    # ------------------------------
    # Background tasks
    # ------------------------------
    async def warning_cleanup_loop(self):
        """Periodically remove expired warnings and recalc totals; log expiries."""
        await self.bot.wait_until_ready()
        while True:
            try:
                all_guilds = await self.config.all_guilds()
                for gid, gdata in all_guilds.items():
                    guild = self.bot.get_guild(gid)
                    if not guild:
                        continue
                    expiry_days = int(gdata.get("warning_expiry_days", DEFAULT_WARNING_EXPIRY_DAYS))
                    current_time = datetime.utcnow().timestamp()

                    all_members = await self.config.all_members(guild)
                    for member_id, mdata in all_members.items():
                        warnings = list(mdata.get("warnings", []))
                        if not warnings:
                            continue
                        updated = []
                        for w in warnings:
                            issue_time = w.get("timestamp", 0)
                            expiry_time = issue_time + (expiry_days * 86400)
                            if current_time < expiry_time:
                                updated.append(w)

                        if len(updated) != len(warnings):
                            member_config = self.config.member_from_ids(gid, int(member_id))
                            await member_config.warnings.set(updated)
                            total_points = sum(max(1, int(w.get("points", 1))) for w in updated)
                            await member_config.total_points.set(total_points)

                            log_channel_id = gdata.get("log_channel")
                            if log_channel_id:
                                ch = guild.get_channel(log_channel_id)
                                member = guild.get_member(int(member_id)) if guild else None
                                if ch and member:
                                    embed = discord.Embed(
                                        title="Warnings Expired",
                                        description=f"Some warnings for {member.mention} have expired.",
                                        color=0x00FF00,
                                    )
                                    embed.add_field(name="Current Points", value=str(total_points))
                                    embed.set_footer(text=datetime.utcnow().strftime("%m/%d/%Y %I:%M %p"))
                                    await self.safe_send_message(ch, embed=embed)
            except Exception as e:
                log.error(f"Error in warning expiry check: {e}", exc_info=True)
            await asyncio.sleep(21600)  # every 6h

    async def mute_check_loop(self):
        """Auto-unmute when time passes; restore roles and log."""
        await self.bot.wait_until_ready()
        while True:
            try:
                for guild in self.bot.guilds:
                    g = await self.config.guild(guild).all()
                    mute_role_id = g.get("mute_role")
                    if not mute_role_id:
                        continue
                    mute_role = guild.get_role(mute_role_id)
                    if not mute_role:
                        continue

                    all_members = await self.config.all_members(guild)
                    current_time = datetime.utcnow().timestamp()
                    for member_id, mdata in all_members.items():
                        muted_until = mdata.get("muted_until")
                        if not muted_until:
                            continue
                        if current_time > muted_until:
                            member = guild.get_member(int(member_id))
                            if not member:
                                continue
                            if mute_role in member.roles:
                                try:
                                    await member.remove_roles(mute_role, reason="Temporary mute expired")
                                except Exception:
                                    pass
                                await self.log_action(
                                    guild, "Auto-Unmute", member, self.bot.user, "Temporary mute duration expired"
                                )
                                await self.config.member(member).muted_until.clear()
            except Exception as e:
                log.error(f"Error in mute check task: {e}", exc_info=True)
            await asyncio.sleep(60)  # every minute

    # ------------------------------
    # Rate-limited messaging
    # ------------------------------
    async def safe_send_message(self, channel, content=None, *, embed=None, file=None):
        if not channel:
            return None
        cid = str(channel.id)
        if cid not in self.rate_limit["message_queue"]:
            self.rate_limit["message_queue"][cid] = {"queue": [], "last_send": 0.0, "processing": False}

        self.rate_limit["message_queue"][cid]["queue"].append({"content": content, "embed": embed, "file": file})
        if not self.rate_limit["message_queue"][cid]["processing"]:
            self.rate_limit["message_queue"][cid]["processing"] = True
            return await self.process_message_queue(channel)
        return None

    async def process_message_queue(self, channel):
        cid = str(channel.id)
        qd = self.rate_limit["message_queue"][cid]
        try:
            while qd["queue"]:
                msg = qd["queue"][0]
                # Gentle 1 msg/sec pacing
                try:
                    await channel.send(content=msg["content"], embed=msg["embed"], file=msg["file"])
                except discord.HTTPException as e:
                    if getattr(e, "status", None) == 429:
                        retry_after = getattr(e, "retry_after", 5)
                        log.info(f"Rate limit hit, waiting {retry_after} sec")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        log.error(f"Error sending message: {e}")
                qd["queue"].pop(0)
                await asyncio.sleep(1.0)
        except Exception as e:
            log.error(f"Error processing queue: {e}", exc_info=True)
        finally:
            qd["processing"] = False

    # ------------------------------
    # Modlog
    # ------------------------------
    async def _next_case(self, guild: discord.Guild) -> int:
        async with self.config.guild(guild).case_count() as n:
            n = int(n or 0) + 1
            await self.config.guild(guild).case_count.set(n)
            return n

    async def log_action(
        self,
        guild: discord.Guild,
        action: str,
        target: discord.Member,
        moderator: Union[discord.Member, discord.User],
        reason: Optional[str] = None,
        *,
        extra_fields: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[discord.Message]:
        """Send and store a modlog entry; returns the message if sent."""
        log_channel_id = await self.config.guild(guild).log_channel()
        log_channel = guild.get_channel(log_channel_id) if log_channel_id else None

        case_num = await self._next_case(guild)
        embed = discord.Embed(color=discord.Color.blurple())
        embed.set_author(name=f"{target} â€¢ {target.id}", icon_url=getattr(target.display_avatar, "url", discord.Embed.Empty))
        embed.title = f"Case #{case_num}"
        embed.description = (
            f"**Action:** {action}\n"
            f"**User:** {target.mention} ( {target.id} )\n"
            f"**Moderator:** {getattr(moderator, 'mention', str(moderator))}\n"
            f"**Reason:** {reason or 'No reason provided'}\n"
            f"**Date:** {datetime.now(timezone.utc).strftime('%b %d, %Y %I:%M %p')} (just now)"
        )
        if extra_fields:
            for f in extra_fields:
                if f and f.get("name") and f.get("value"):
                    embed.description += f"\n**{f['name']}:** {f['value']}"
        embed.set_footer(text=f"{guild.me.display_name} Support â€¢ Today at {datetime.now(timezone.utc).strftime('%I:%M %p')}")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.primary, label="View All Cautions", custom_id=f"cautions_view_{target.id}"))
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.danger, label="Clear All Cautions", custom_id=f"cautions_clear_{target.id}"))

        msg = None
        if log_channel:
            try:
                msg = await log_channel.send(embed=embed, view=view)
            except discord.HTTPException as e:
                log.error(f"Error sending modlog with view: {e}")
                try:
                    msg = await log_channel.send(embed=embed)
                except Exception as e2:
                    log.error(f"Error sending modlog fallback: {e2}")
                    msg = None

        # Persist
        try:
            await self.config.guild(guild).modlog.set_raw(
                str(case_num),
                value={
                    "case_num": case_num,
                    "action": action,
                    "user_id": target.id,
                    "user_name": str(target),
                    "moderator_id": getattr(moderator, "id", 0),
                    "moderator_name": str(moderator),
                    "reason": reason or "No reason provided",
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                    "message_id": msg.id if msg else None,
                },
            )
        except Exception as e:
            log.error(f"Failed to write modlog entry: {e}")
        return msg

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle the demo buttons; safe no-op if not ours."""
        try:
            cid = interaction.data.get("custom_id") if interaction.data else None
            if not cid or not (cid.startswith("cautions_view_") or cid.startswith("cautions_clear_")):
                return
            await interaction.response.send_message("Action requires moderator confirmation.", ephemeral=True)
        except Exception:
            pass

    # ------------------------------
    # Settings commands
    # ------------------------------
    @commands.group(name="cautionset", invoke_without_command=True)
    @checks.admin_or_permissions(administrator=True)
    async def caution_settings(self, ctx: commands.Context):
        """Configure the warning system settings."""
        if ctx.invoked_subcommand is None:
            g = await self.config.guild(ctx.guild).all()
            roles = [ctx.guild.get_role(rid) for rid in g.get("protected_role_ids", [])]
            roles_txt = ", ".join(r.mention for r in roles if r) or "None"

            embed = discord.Embed(
                title="Caution System Settings",
                description="Use these commands to configure the warning system.",
                color=discord.Color.blue(),
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
                inline=False,
            )
            embed.add_field(
                name="Beri Economy Settings",
                value=(
                    f"`{ctx.clean_prefix}cautionset fines` - Configure fine amounts\n"
                    f"`{ctx.clean_prefix}cautionset exemptfines <role>` - Exempt role from fines\n"
                    f"`{ctx.clean_prefix}cautionset showfines` - Show current fine settings\n"
                ),
                inline=False,
            )
            embed.add_field(
                name="Staff Protection",
                value=(
                    f"Enabled: **{'Yes' if g.get('staff_protection_enabled', True) else 'No'}**\n"
                    f"Max Points/Caution: **{g.get('max_points_per_caution', 10)}**\n"
                    f"Protected Roles: {roles_txt}\n"
                    f"Use `{ctx.clean_prefix}cautionset staffprotect` to configure."
                ),
                inline=False,
            )
            await ctx.send(embed=embed)

    @caution_settings.group(name="fines")
    async def fine_settings(self, ctx: commands.Context):
        """Configure Beri fine settings."""
        if ctx.invoked_subcommand is None:
            g = await self.config.guild(ctx.guild).all()
            embed = discord.Embed(title="Current Fine Settings", color=discord.Color.blue())
            embed.add_field(name="Warning Base Fine", value=f"{humanize_number(g.get('warning_fine_base', 1000))} Beri", inline=True)
            embed.add_field(name="Warning Multiplier", value=f"{g.get('warning_fine_multiplier', 1.5)}x", inline=True)
            embed.add_field(name="Mute Fine", value=f"{humanize_number(g.get('mute_fine', 5000))} Beri", inline=True)
            embed.add_field(name="Timeout Fine", value=f"{humanize_number(g.get('timeout_fine', 3000))} Beri", inline=True)
            embed.add_field(name="Kick Fine", value=f"{humanize_number(g.get('kick_fine', 10000))} Beri", inline=True)
            embed.add_field(name="Ban Fine", value=f"{humanize_number(g.get('ban_fine', 25000))} Beri", inline=True)
            embed.add_field(name="Max Fine Per Action", value=f"{humanize_number(g.get('max_fine_per_action', 50000))} Beri", inline=True)

            exempt_roles = g.get("fine_exempt_roles", [])
            if exempt_roles:
                role_mentions = []
                for rid in exempt_roles:
                    r = ctx.guild.get_role(rid)
                    if r:
                        role_mentions.append(r.mention)
                embed.add_field(name="Exempt Roles", value="\n".join(role_mentions) or "None", inline=False)
            else:
                embed.add_field(name="Exempt Roles", value="None", inline=False)
            await ctx.send(embed=embed)

    @caution_settings.command(name="showfines")
    async def show_fines(self, ctx: commands.Context):
        return await self.fine_settings.callback(self, ctx)  # reuse

    @fine_settings.command(name="warningbase")
    async def set_warning_base_fine(self, ctx: commands.Context, amount: int):
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        await self.config.guild(ctx.guild).warning_fine_base.set(amount)
        await ctx.send(f"Base warning fine set to {humanize_number(amount)} Beri per point.")

    @fine_settings.command(name="warningmultiplier")
    async def set_warning_multiplier(self, ctx: commands.Context, multiplier: float):
        if multiplier < 1.0:
            return await ctx.send("Multiplier must be at least 1.0.")
        await self.config.guild(ctx.guild).warning_fine_multiplier.set(multiplier)
        await ctx.send(f"Warning fine multiplier set to {multiplier}x.")

    @fine_settings.command(name="mute")
    async def set_mute_fine(self, ctx: commands.Context, amount: int):
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        await self.config.guild(ctx.guild).mute_fine.set(amount)
        await ctx.send(f"Mute fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="timeout")
    async def set_timeout_fine(self, ctx: commands.Context, amount: int):
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        await self.config.guild(ctx.guild).timeout_fine.set(amount)
        await ctx.send(f"Timeout fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="kick")
    async def set_kick_fine(self, ctx: commands.Context, amount: int):
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        await self.config.guild(ctx.guild).kick_fine.set(amount)
        await ctx.send(f"Kick fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="ban")
    async def set_ban_fine(self, ctx: commands.Context, amount: int):
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        await self.config.guild(ctx.guild).ban_fine.set(amount)
        await ctx.send(f"Ban fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="maxfine")
    async def set_max_fine(self, ctx: commands.Context, amount: int):
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        await self.config.guild(ctx.guild).max_fine_per_action.set(amount)
        await ctx.send(f"Maximum fine per action set to {humanize_number(amount)} Beri.")

    @caution_settings.command(name="exemptfines")
    async def exempt_role_from_fines(self, ctx: commands.Context, role: discord.Role):
        async with self.config.guild(ctx.guild).fine_exempt_roles() as ex:
            if role.id in ex:
                ex.remove(role.id)
                await ctx.send(f"{role.mention} is no longer exempt from fines.")
            else:
                ex.append(role.id)
                await ctx.send(f"{role.mention} is now exempt from fines.")

    @caution_settings.command(name="expiry")
    async def set_warning_expiry(self, ctx: commands.Context, days: int):
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
        *, reason: Optional[str] = None
    ):
        valid_actions = ["mute", "timeout", "kick", "ban"]
        if action.lower() not in valid_actions:
            return await ctx.send(f"Invalid action. Choose from: {', '.join(valid_actions)}")
        if action.lower() in ["mute", "timeout"] and duration is None:
            return await ctx.send(f"Duration (in minutes) is required for {action} action.")

        async with self.config.guild(ctx.guild).action_thresholds() as thresholds:
            entry = {"action": action.lower()}
            if duration:
                entry["duration"] = duration
            entry["reason"] = reason or f"Exceeded {points} warning points"
            thresholds[str(points)] = entry

        c = f"When a member reaches {points} warning points, they will be {action.lower()}ed"
        if duration:
            c += f" for {duration} minutes"
        c += f" with reason: {entry['reason']}"
        await ctx.send(c)

    @caution_settings.command(name="removethreshold")
    async def remove_action_threshold(self, ctx: commands.Context, points: int):
        async with self.config.guild(ctx.guild).action_thresholds() as thresholds:
            if str(points) in thresholds:
                del thresholds[str(points)]
                await ctx.send(f"Removed action threshold for {points} warning points.")
            else:
                await ctx.send(f"No action threshold set for {points} warning points.")

    @caution_settings.command(name="showthresholds")
    async def show_action_thresholds(self, ctx: commands.Context):
        thresholds = await self.config.guild(ctx.guild).action_thresholds()
        if not thresholds:
            return await ctx.send("No action thresholds are configured.")
        embed = discord.Embed(title="Warning Action Thresholds", color=0x00FF00)
        for points, data in sorted(thresholds.items(), key=lambda x: int(x[0])):
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
    async def set_log_channel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        if channel is None:
            channel = ctx.channel
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(f"Log channel set to {channel.mention}")

    @caution_settings.command(name="mute")
    @checks.admin_or_permissions(administrator=True)
    async def set_mute_role(self, ctx: commands.Context, role: discord.Role = None):
        if role is None:
            mute_role_id = await self.config.guild(ctx.guild).mute_role()
            if not mute_role_id:
                return await ctx.send("No mute role is currently set. Provide a role to set one.")
            mute_role = ctx.guild.get_role(mute_role_id)
            if not mute_role:
                return await ctx.send("The configured mute role no longer exists. Please set a new one.")
            return await ctx.send(f"Current mute role: {mute_role.mention} (ID: {mute_role.id})")

        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I need the 'Manage Roles' permission to apply the mute role.")
        if role.position >= ctx.guild.me.top_role.position:
            return await ctx.send(f"I cannot manage the role {role.mention} because its position is too high.")
        await self.config.guild(ctx.guild).mute_role.set(role.id)
        await ctx.send(f"Mute role set to {role.mention}.")

    # --- Staff protection settings subgroup ---
    @caution_settings.group(name="staffprotect", invoke_without_command=True)
    @checks.admin_or_permissions(administrator=True)
    async def staff_protect_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            g = await self.config.guild(ctx.guild).all()
            roles = [ctx.guild.get_role(rid) for rid in g.get("protected_role_ids", [])]
            roles_txt = ", ".join(r.mention for r in roles if r) or "None"
            embed = discord.Embed(title="Staff Protection Settings", color=discord.Color.blue())
            embed.add_field(name="Enabled", value="Yes" if g.get("staff_protection_enabled", True) else "No", inline=True)
            embed.add_field(name="Max Points per Caution", value=str(g.get("max_points_per_caution", 10)), inline=True)
            embed.add_field(name="Protected Roles", value=roles_txt, inline=False)
            await ctx.send(embed=embed)

    @staff_protect_group.command(name="toggle")
    @checks.admin_or_permissions(administrator=True)
    async def staff_protect_toggle(self, ctx: commands.Context, enabled: bool):
        await self.config.guild(ctx.guild).staff_protection_enabled.set(enabled)
        await ctx.send(f"Staff protection is now {'enabled' if enabled else 'disabled'}.")

    @staff_protect_group.command(name="addrole")
    @checks.admin_or_permissions(administrator=True)
    async def staff_protect_addrole(self, ctx: commands.Context, role: discord.Role):
        async with self.config.guild(ctx.guild).protected_role_ids() as ids:
            if role.id in ids:
                return await ctx.send(f"{role.mention} is already protected.")
            ids.append(role.id)
        await ctx.send(f"Added {role.mention} to protected staff roles.")

    @staff_protect_group.command(name="removerole")
    @checks.admin_or_permissions(administrator=True)
    async def staff_protect_removerole(self, ctx: commands.Context, role: discord.Role):
        async with self.config.guild(ctx.guild).protected_role_ids() as ids:
            if role.id not in ids:
                return await ctx.send(f"{role.mention} wasnâ€™t protected.")
            ids.remove(role.id)
        await ctx.send(f"Removed {role.mention} from protected staff roles.")

    @staff_protect_group.command(name="setcap")
    @checks.admin_or_permissions(administrator=True)
    async def staff_protect_setcap(self, ctx: commands.Context, max_points: int):
        max_points = max(1, int(max_points))
        await self.config.guild(ctx.guild).max_points_per_caution.set(max_points)
        await ctx.send(f"Max points per caution set to **{max_points}**.")

    # ------------------------------
    # Core commands
    # ------------------------------
    @commands.command(name="caution")
    @checks.mod_or_permissions(kick_members=True)
    async def warn_member(self, ctx: commands.Context, member: discord.Member, points_or_reason: str = "1", *, remaining_reason: Optional[str] = None):
        """
        Issue a caution/warning to a member with optional point value.
        Default is 1 point if not specified. Includes Beri fine.
        [p]caution @user 2 Breaking rule #3
        [p]caution @user Spamming in chat
        """
        core = self._core()
        beri_available = core is not None

        # parse points
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
        if member.bot:
            return await ctx.send("Bots cannot be cautioned.")
        if member.id == ctx.author.id:
            return await ctx.send("You cannot caution yourself.")
        if member.id == ctx.guild.owner_id and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("You cannot caution the server owner.")

        # Staff safety
        if await self._is_protected_staff(member):
            return await ctx.send(f"{member.mention} is protected staff. Use escalation paths, not cautions.")
        # Role hierarchy
        if ctx.author.id != ctx.guild.owner_id and role_rank(ctx.author) <= role_rank(member):
            return await ctx.send("You canâ€™t caution someone with an equal or higher top role.")

        # Cap points
        new_points, cap = await self._cap_points(ctx.guild, int(points))
        if cap is not None and points != new_points:
            await ctx.send(f"Point value capped at **{cap}** (was {points}).")
        points = new_points

        # Fines
        fine_amount = 0
        fine_applied = True
        if beri_available:
            fine_amount = await self._calculate_warning_fine(member, points)
            fine_applied = await self._apply_beri_fine(member, fine_amount, f"warning:{points}pt", ctx.author)

        # Build warning record
        expiry_days = await self.config.guild(ctx.guild).warning_expiry_days()
        warning = {
            "points": points,
            "reason": reason or "No reason provided",
            "moderator_id": ctx.author.id,
            "timestamp": datetime.utcnow().timestamp(),
            "expiry": (datetime.utcnow() + timedelta(days=expiry_days)).timestamp(),
            "fine_amount": fine_amount,
            "fine_applied": fine_applied,
        }

        # Persist
        member_config = self.config.member(member)
        async with member_config.warnings() as warnings:
            warnings.append(warning)
        async with member_config.all() as m:
            m["total_points"] = sum(max(1, int(w.get("points", 1))) for w in m["warnings"])
            m["warning_count"] = m.get("warning_count", 0) + 1
            total_points = m["total_points"]

        # Notify
        embed = discord.Embed(title="Warning Issued", color=0xFF9900)
        embed.add_field(name="Member", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        embed.add_field(name="Points", value=str(points))
        embed.add_field(name="Total Points", value=str(total_points))
        embed.add_field(name="Reason", value=warning["reason"], inline=False)
        embed.add_field(name="Expires", value=f"<t:{int(warning['expiry'])}:R>", inline=False)
        if beri_available and fine_amount > 0:
            if fine_applied:
                embed.add_field(name="Fine Applied", value=f"{humanize_number(fine_amount)} Beri", inline=True)
            else:
                embed.add_field(name="Fine (Partial/Failed)", value=f"{humanize_number(fine_amount)} Beri", inline=True)
        elif beri_available:
            exempt_status = "Exempt from fines" if await self._is_fine_exempt(member) else "No fine (0 Beri balance)"
            embed.add_field(name="Fine Status", value=exempt_status, inline=True)

        await self.safe_send_message(ctx.channel, f"{member.mention} has been cautioned.", embed=embed)

        extra = [{"name": "Points", "value": str(points)}, {"name": "Total Points", "value": str(total_points)}]
        if beri_available and fine_amount > 0:
            extra.append({"name": "Beri Fine", "value": f"{humanize_number(fine_amount)} ({'Applied' if fine_applied else 'Failed/Partial'})"})
        await self.log_action(ctx.guild, "Warning", member, ctx.author, warning["reason"], extra_fields=extra)

        # Dispatch and threshold check
        self.bot.dispatch("caution_issued", ctx.guild, ctx.author, member, warning["reason"])
        await self.check_action_thresholds(ctx, member, total_points)

    @commands.command(name="cautionpoints")
    @checks.mod_or_permissions(kick_members=True)
    async def caution_points(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Show a member's current caution points."""
        member = member or ctx.author
        data = await self.config.member(member).all()
        points = int(data.get("total_points", 0))
        await ctx.send(f"{member.mention} has **{humanize_number(points)}** caution points.")

    # ------------------------------
    # Threshold handling
    # ------------------------------
    async def check_action_thresholds(self, ctx: commands.Context, member: discord.Member, total_points: int):
        thresholds = await self.config.guild(ctx.guild).action_thresholds()
        matching = []
        for t_points, action_data in thresholds.items():
            try:
                if int(t_points) <= total_points:
                    matching.append((int(t_points), action_data))
            except Exception:
                continue
        if not matching:
            return
        matching.sort(key=lambda x: x[0], reverse=True)
        top_points, action_data = matching[0]

        applied = await self.config.member(member).applied_thresholds()
        if top_points in applied:
            return
        applied.append(top_points)
        await self.config.member(member).applied_thresholds.set(applied)
        await self.apply_threshold_action(ctx, member, action_data)

    async def apply_threshold_action(self, ctx: commands.Context, member: discord.Member, action_data: Dict[str, Union[str, int]]):
        """Apply automatic moderation based on threshold; staff are protected."""
        if await self._is_protected_staff(member):
            await self.safe_send_message(ctx.channel, f"Threshold met, but {member.mention} is protected staff. No auto-action.")
            return

        action = action_data["action"]
        reason = action_data.get("reason", "Warning threshold exceeded")
        duration = action_data.get("duration")

        # Apply additional fine
        core = self._core()
        fine_amount = 0
        fine_applied = True
        if core:
            g = await self.config.guild(ctx.guild).all()
            if action == "mute":
                fine_amount = g.get("mute_fine", 5000)
            elif action == "timeout":
                fine_amount = g.get("timeout_fine", 3000)
            elif action == "kick":
                fine_amount = g.get("kick_fine", 10000)
            elif action == "ban":
                fine_amount = g.get("ban_fine", 25000)
            if fine_amount > 0:
                fine_applied = await self._apply_beri_fine(member, fine_amount, f"threshold:{action}", self.bot.user)

        try:
            if action == "mute":
                mute_role_id = await self.config.guild(ctx.guild).mute_role()
                if not mute_role_id:
                    await self.safe_send_message(ctx.channel, f"Mute role not found. Set one with {ctx.clean_prefix}cautionset mute @role")
                    return
                mute_role = ctx.guild.get_role(mute_role_id)
                if not mute_role:
                    await self.safe_send_message(ctx.channel, f"Mute role not found. Set one with {ctx.clean_prefix}cautionset mute @role")
                    return
                if duration:
                    muted_until = datetime.utcnow() + timedelta(minutes=int(duration))
                    await self.config.member(member).muted_until.set(muted_until.timestamp())
                try:
                    await member.add_roles(mute_role, reason=reason)
                except discord.Forbidden:
                    return await self.safe_send_message(ctx.channel, "I don't have permission to manage roles for this member.")
                msg = f"{member.mention} has been muted"
                if duration:
                    msg += f" for {duration} minutes"
                msg += f" due to: {reason}"
                if fine_amount > 0:
                    msg += f"\nAdditional fine: {humanize_number(fine_amount)} Beri {'(Applied)' if fine_applied else '(Failed/Partial)'}"
                await self.safe_send_message(ctx.channel, msg)
                extra = [{"name": "Duration", "value": f"{duration} minutes"}] if duration else []
                if fine_amount > 0:
                    extra.append({"name": "Additional Fine", "value": f"{humanize_number(fine_amount)} Beri"})
                await self.log_action(ctx.guild, "Auto-Mute", member, self.bot.user, reason, extra_fields=extra)

            elif action == "timeout":
                until = datetime.utcnow() + timedelta(minutes=int(duration or 1))
                await member.timeout(until=until, reason=reason)
                msg = f"{member.mention} has been timed out for {duration} minutes due to: {reason}"
                if fine_amount > 0:
                    msg += f"\nAdditional fine: {humanize_number(fine_amount)} Beri {'(Applied)' if fine_applied else '(Failed/Partial)'}"
                await self.safe_send_message(ctx.channel, msg)
                extra = [{"name": "Duration", "value": f"{duration} minutes"}]
                if fine_amount > 0:
                    extra.append({"name": "Additional Fine", "value": f"{humanize_number(fine_amount)} Beri"})
                await self.log_action(ctx.guild, "Auto-Timeout", member, self.bot.user, reason, extra_fields=extra)

            elif action == "kick":
                await member.kick(reason=reason)
                msg = f"{member.mention} has been kicked due to: {reason}"
                if fine_amount > 0:
                    msg += f"\nFine applied: {humanize_number(fine_amount)} Beri {'(Applied)' if fine_applied else '(Failed/Partial)'}"
                await self.safe_send_message(ctx.channel, msg)
                extra = [{"name": "Fine", "value": f"{humanize_number(fine_amount)} Beri"}] if fine_amount > 0 else []
                await self.log_action(ctx.guild, "Auto-Kick", member, self.bot.user, reason, extra_fields=extra)

            elif action == "ban":
                await member.ban(reason=reason)
                msg = f"{member.mention} has been banned due to: {reason}"
                if fine_amount > 0:
                    msg += f"\nFine applied: {humanize_number(fine_amount)} Beri {'(Applied)' if fine_applied else '(Failed/Partial)'}"
                await self.safe_send_message(ctx.channel, msg)
                extra = [{"name": "Fine", "value": f"{humanize_number(fine_amount)} Beri"}] if fine_amount > 0 else []
                await self.log_action(ctx.guild, "Auto-Ban", member, self.bot.user, reason, extra_fields=extra)

            else:
                await self.safe_send_message(ctx.channel, f"Unknown automatic action: `{action}`")
        except Exception as e:
            await self.safe_send_message(ctx.channel, f"Failed to apply automatic {action}: {str(e)}")
            log.error(f"Error in apply_threshold_action: {e}", exc_info=True)

    # ------------------------------
    # End class
    # ------------------------------

async def setup(bot: Red) -> None:
    await bot.add_cog(BeriCautions(bot))
