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
    await bot.add_cog(BeriCautions(bot))        while True:
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
                    f"`{ctx.clean_prefix}cautionset showfines` - Show current fine settings\n"
                ),
                inline=False
            )
            await ctx.send(embed=embed)

    @caution_settings.group(name="fines")
    async def fine_settings(self, ctx):
        """Configure Beri fine settings."""
        if ctx.invoked_subcommand is None:
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
                role_mentions = []
                for role_id in exempt_roles:
                    role = ctx.guild.get_role(role_id)
                    if role:
                        role_mentions.append(role.mention)
                embed.add_field(name="Exempt Roles", value="\n".join(role_mentions) or "None", inline=False)
            else:
                embed.add_field(name="Exempt Roles", value="None", inline=False)
            
            await ctx.send(embed=embed)

    @fine_settings.command(name="warningbase")
    async def set_warning_base_fine(self, ctx, amount: int):
        """Set the base fine amount per warning point."""
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        
        await self.config.guild(ctx.guild).warning_fine_base.set(amount)
        await ctx.send(f"Base warning fine set to {humanize_number(amount)} Beri per point.")

    @fine_settings.command(name="warningmultiplier")
    async def set_warning_multiplier(self, ctx, multiplier: float):
        """Set the fine multiplier for repeat offenses."""
        if multiplier < 1.0:
            return await ctx.send("Multiplier must be at least 1.0.")
        
        await self.config.guild(ctx.guild).warning_fine_multiplier.set(multiplier)
        await ctx.send(f"Warning fine multiplier set to {multiplier}x.")

    @fine_settings.command(name="mute")
    async def set_mute_fine(self, ctx, amount: int):
        """Set the additional fine for mutes."""
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        
        await self.config.guild(ctx.guild).mute_fine.set(amount)
        await ctx.send(f"Mute fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="timeout")
    async def set_timeout_fine(self, ctx, amount: int):
        """Set the additional fine for timeouts."""
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        
        await self.config.guild(ctx.guild).timeout_fine.set(amount)
        await ctx.send(f"Timeout fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="kick")
    async def set_kick_fine(self, ctx, amount: int):
        """Set the fine for kicks."""
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        
        await self.config.guild(ctx.guild).kick_fine.set(amount)
        await ctx.send(f"Kick fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="ban")
    async def set_ban_fine(self, ctx, amount: int):
        """Set the fine for bans."""
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        
        await self.config.guild(ctx.guild).ban_fine.set(amount)
        await ctx.send(f"Ban fine set to {humanize_number(amount)} Beri.")

    @fine_settings.command(name="maxfine")
    async def set_max_fine(self, ctx, amount: int):
        """Set the maximum fine per single action."""
        if amount < 0:
            return await ctx.send("Fine amount cannot be negative.")
        
        await self.config.guild(ctx.guild).max_fine_per_action.set(amount)
        await ctx.send(f"Maximum fine per action set to {humanize_number(amount)} Beri.")

    @caution_settings.command(name="exemptfines")
    async def exempt_role_from_fines(self, ctx, role: discord.Role):
        """Add or remove a role from fine exemption."""
        async with self.config.guild(ctx.guild).fine_exempt_roles() as exempt_roles:
            if role.id in exempt_roles:
                exempt_roles.remove(role.id)
                await ctx.send(f"{role.mention} is no longer exempt from fines.")
            else:
                exempt_roles.append(role.id)
                await ctx.send(f"{role.mention} is now exempt from fines.")

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
        
    @caution_settings.command(name="mute")
    @checks.admin_or_permissions(administrator=True)
    async def set_mute_role(self, ctx, role: discord.Role = None):
        """Set the mute role for the caution system."""
        # If no role provided, show current setting
        if role is None:
            mute_role_id = await self.config.guild(ctx.guild).mute_role()
            if not mute_role_id:
                return await ctx.send("No mute role is currently set. Use this command with a role mention or name to set one.")
                
            mute_role = ctx.guild.get_role(mute_role_id)
            if not mute_role:
                return await ctx.send("The configured mute role no longer exists. Please set a new one.")
                
            return await ctx.send(f"Current mute role: {mute_role.mention} (ID: {mute_role.id})")
        
        # Check if bot has required permissions
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I need the 'Manage Roles' permission to apply the mute role.")
        
        # Check role hierarchy - bot needs to be able to manage this role
        if role.position >= ctx.guild.me.top_role.position:
            return await ctx.send(f"I cannot manage the role {role.mention} because it's position is higher than or equal to my highest role.")
        
        await self.config.guild(ctx.guild).mute_role.set(role.id)
        await ctx.send(f"Mute role set to {role.mention}.")

    @commands.command(name="caution")
    @checks.mod_or_permissions(kick_members=True)
    async def warn_member(self, ctx, member: discord.Member, points_or_reason: str = "1", *, remaining_reason: Optional[str] = None):
        """
        Issue a caution/warning to a member with optional point value.
        Default is 1 point if not specified. Includes Beri fine.
        
        Examples:
        [p]caution @user 2 Breaking rule #3
        [p]caution @user Spamming in chat
        """
        # Check if BeriCore is available
        core = self._core()
        beri_available = core is not None
        
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
        
        # Calculate fine if Beri is available
        fine_amount = 0
        fine_applied = True
        if beri_available:
            fine_amount = await self._calculate_warning_fine(member, points)
            fine_applied = await self._apply_beri_fine(member, fine_amount, f"warning:{points}pt", ctx.author)
        
        # Get warning expiry days first
        expiry_days = await self.config.guild(ctx.guild).warning_expiry_days()
        warning = {
            "points": points,
            "reason": reason or "No reason provided",
            "moderator_id": ctx.author.id,
            "timestamp": datetime.utcnow().timestamp(),
            "expiry": (datetime.utcnow() + timedelta(days=expiry_days)).timestamp(),
            "fine_amount": fine_amount,
            "fine_applied": fine_applied
        }
        
        # Get member config and update warnings
        member_config = self.config.member(member)
        async with member_config.warnings() as warnings:
            warnings.append(warning)
        
        # Update total points and warning count
        async with member_config.all() as member_data:
            member_data["total_points"] = sum(w.get("points", 1) for w in member_data["warnings"])
            member_data["warning_count"] = member_data.get("warning_count", 0) + 1
            total_points = member_data["total_points"]
        
        # Create warning embed
        embed = discord.Embed(title=f"Warning Issued", color=0xff9900)
        embed.add_field(name="Member", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        embed.add_field(name="Points", value=str(points))
        embed.add_field(name="Total Points", value=str(total_points))
        embed.add_field(name="Reason", value=warning["reason"], inline=False)
        embed.add_field(name="Expires", value=f"<t:{int(warning['expiry'])}:R>", inline=False)
        
        # Add Beri fine information if applicable
        if beri_available and fine_amount > 0:
            if fine_applied:
                embed.add_field(name="Fine Applied", value=f"{humanize_number(fine_amount)} Beri", inline=True)
            else:
                embed.add_field(name="Fine (Partial/Failed)", value=f"{humanize_number(fine_amount)} Beri", inline=True)
        elif beri_available:
            exempt_status = "Exempt from fines" if await self._is_fine_exempt(member) else "No fine (0 Beri balance)"
            embed.add_field(name="Fine Status", value=exempt_status, inline=True)
        
        embed.set_footer(text=datetime.utcnow().strftime("%m/%d/%Y %I:%M %p"))
        
        # Send warning in channel and log
        await self.safe_send_message(ctx.channel, f"{member.mention} has been cautioned.", embed=embed)
        
        # Create extra fields for logging
        extra_fields = [
            {"name": "Points", "value": str(points)},
            {"name": "Total Points", "value": str(total_points)}
        ]
        
        if beri_available and fine_amount > 0:
            extra_fields.append({"name": "Beri Fine", "value": f"{humanize_number(fine_amount)} ({'Applied' if fine_applied else 'Failed/Partial'})"})
        
        # Log the warning
        await self.log_action(ctx.guild, "Warning", member, ctx.author, warning["reason"], extra_fields=extra_fields)
        
        # Dispatch custom event for other cogs (like BeriBridgePunish)
        self.bot.dispatch("caution_issued", ctx.guild, ctx.author, member, warning["reason"])
        
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
        
        # Calculate and apply additional fine for the action
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
                fine_applied = await self._apply_beri_fine(member, fine_amount, f"threshold:{action}", self.bot.user)
        
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
                    
                    message = f"{member.mention} has been muted for {duration} minutes due to: {reason}"
                    if fine_amount > 0:
                        message += f"\nAdditional fine: {humanize_number(fine_amount)} Beri {'(Applied)' if fine_applied else '(Failed/Partial)'}"
                    await self.safe_send_message(ctx.channel, message)
                except discord.Forbidden:
                    await self.safe_send_message(ctx.channel, "I don't have permission to manage roles for this member.")
                    return
                except Exception as e:
                    await self.safe_send_message(ctx.channel, f"Error applying mute: {str(e)}")
                    return
                
                # Log the mute action
                extra_fields = [{"name": "Duration", "value": f"{duration} minutes"}]
                if fine_amount > 0:
                    extra_fields.append({"name": "Additional Fine", "value": f"{humanize_number(fine_amount)} Beri"})
                await self.log_action(ctx.guild, "Auto-Mute", member, self.bot.user, reason, extra_fields=extra_fields)
            
            elif action == "timeout":
                until = datetime.utcnow() + timedelta(minutes=duration)
                await member.timeout(until=until, reason=reason)
                
                message = f"{member.mention} has been timed out for {duration} minutes due to: {reason}"
                if fine_amount > 0:
                    message += f"\nAdditional fine: {humanize_number(fine_amount)} Beri {'(Applied)' if fine_applied else '(Failed/Partial)'}"
                await self.safe_send_message(ctx.channel, message)
                
                extra_fields = [{"name": "Duration", "value": f"{duration} minutes"}]
                if fine_amount > 0:
                    extra_fields.append({"name": "Additional Fine", "value": f"{humanize_number(fine_amount)} Beri"})
                await self.log_action(ctx.guild, "Auto-Timeout", member, self.bot.user, reason, extra_fields=extra_fields)
            
            elif action == "kick":
                await member.kick(reason=reason)
                
                message = f"{member.mention} has been kicked due to: {reason}"
                if fine_amount > 0:
                    message += f"\nFine applied: {humanize_number(fine_amount)} Beri {'(Applied)' if fine_applied else '(Failed/Partial)'}"
                await self.safe_send_message(ctx.channel, message)
                
                extra_fields = []
                if fine_amount > 0:
                    extra_fields.append({"name": "Fine", "value": f"{humanize_number(fine_amount)} Beri"})
                await self.log_action(ctx.guild, "Auto-Kick", member, self.bot.user, reason, extra_fields=extra_fields)
            
            elif action == "ban":
                await member.ban(reason=reason)
                
                message = f"{member.mention} has been banned due to: {reason}"
                if fine_amount > 0:
                    message += f"\nFine applied: {humanize_number(fine_amount)} Beri {'(Applied)' if fine_applied else '(Failed/Partial)'}"
                await self.safe_send_message(ctx.channel, message)
                
                extra_fields = []
                if fine_amount > 0:
                    extra_fields.append({"name": "Fine", "value": f"{humanize_number(fine_amount)} Beri"})
                await self.log_action(ctx.guild, "Auto-Ban", member, self.bot.user, reason, extra_fields=extra_fields)
                
        except Exception as e:
            await self.safe_send_message(ctx.channel, f"Failed to apply automatic {action}: {str(e)}")
            log.error(f"Error in apply_threshold_action: {e}", exc_info=True)

    @commands.command(name="quiet")
    @checks.mod_or_permissions(manage_roles=True)
    async def mute_member(self, ctx, member: discord.Member, duration: int = 30, *, reason: Optional[str] = None):
        """
        Mute a member for the specified duration (in minutes).
        Includes additional Beri fine.
        
        Examples:
        [p]quiet @user 60 Excessive spam
        [p]quiet @user 30
        """
        try:
            # Ensure member isn't a mod/admin by checking permissions
            if member.guild_permissions.kick_members or member.guild_permissions.administrator:
                return await ctx.send(f"Cannot mute {member.mention} as they have moderator/admin permissions.")
                
            # Check for role hierarchy - cannot mute someone with a higher role than the bot
            if member.top_role >= ctx.guild.me.top_role:
                return await ctx.send(f"Cannot mute {member.mention} as their highest role is above or equal to mine.")
            
            # Get mute role
            mute_role_id = await self.config.guild(ctx.guild).mute_role()
            if not mute_role_id:
                return await ctx.send(f"Mute role not set up. Please use {ctx.clean_prefix}setupmute first.")
            
            mute_role = ctx.guild.get_role(mute_role_id)
            if not mute_role:
                return await ctx.send(f"Mute role not found. Please use {ctx.clean_prefix}setupmute to create a new one.")
            
            # Apply Beri fine for mute
            core = self._core()
            fine_amount = 0
            fine_applied = True
            if core:
                guild_config = await self.config.guild(ctx.guild).all()
                fine_amount = guild_config.get("mute_fine", 5000)
                if fine_amount > 0:
                    fine_applied = await self._apply_beri_fine(member, fine_amount, "manual_mute", ctx.author)
            
            # Check if already muted
            if mute_role in member.roles:
                # Update duration if already muted
                muted_until = datetime.utcnow() + timedelta(minutes=duration)
                await self.config.member(member).muted_until.set(muted_until.timestamp())
                message = f"{member.mention} was already muted. Updated mute duration to end {duration} minutes from now."
                if fine_amount > 0:
                    message += f"\nAdditional fine: {humanize_number(fine_amount)} Beri {'(Applied)' if fine_applied else '(Failed/Partial)'}"
                await ctx.send(message)
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
                    
                # Set muted_until time
                muted_until = datetime.utcnow() + timedelta(minutes=duration)
                await self.config.member(member).muted_until.set(muted_until.timestamp())
                
                # Confirm the mute
                message = f"{member.mention} has been muted for {duration} minutes. Reason: {reason or 'No reason provided'}"
                if fine_amount > 0:
                    message += f"\nFine applied: {humanize_number(fine_amount)} Beri {'(Applied)' if fine_applied else '(Failed/Partial)'}"
                await ctx.send(message)
                    
                # Log action
                extra_fields = [{"name": "Duration", "value": f"{duration} minutes"}]
                if fine_amount > 0:
                    extra_fields.append({"name": "Fine", "value": f"{humanize_number(fine_amount)} Beri"})
                await self.log_action(ctx.guild, "Mute", member, ctx.author, reason, extra_fields=extra_fields)
                    
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
                return await ctx.send(f"No mute role has been configured. Please run {ctx.clean_prefix}setupmute first.")
                
            mute_role = ctx.guild.get_role(mute_role_id)
            if not mute_role:
                return await ctx.send(f"Mute role not found. The role may have been deleted. Please run {ctx.clean_prefix}setupmute again.")
                
            # Get bot's position to check hierarchy
            bot_position = ctx.guild.me.top_role.position
            mute_position = mute_role.position
            
            # Check role position
            if mute_position < bot_position - 1:
                await ctx.send(f"Warning: Mute role position ({mute_position}) is not directly below bot's highest role ({bot_position})")
            else:
                await ctx.send(f"Mute role position ({mute_position}) looks good relative to bot's highest role ({bot_position})")
                
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
                await ctx.send(f"Issues found in {text_channels_with_issues}/{text_channels_checked} text channels - mute role can still send messages")
            else:
                await ctx.send(f"Text channel permissions look good for {text_channels_checked} channels checked")
                
            if voice_channels_with_issues > 0:
                await ctx.send(f"Issues found in {voice_channels_with_issues}/{voice_channels_checked} voice channels - mute role can still speak")
            else:
                await ctx.send(f"Voice channel permissions look good for {voice_channels_checked} channels checked")
                
            # Overall assessment
            if text_channels_with_issues == 0 and voice_channels_with_issues == 0:
                await ctx.send("Mute role appears to be correctly configured!")
            else:
                await ctx.send(f"Mute role has issues - please run {ctx.clean_prefix}setupmute again to fix permissions")
                
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
                
                await ctx.send(f"Some errors occurred while setting permissions:\n{error_report}")
            
            await status_msg.edit(content=f"Mute role setup complete! The role {mute_role.mention} has been configured.")
            
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
        List all active warnings for a member with Beri fine information.
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
        total_fines = await self.config.member(member).total_fines_paid()
        
        if not warnings:
            return await ctx.send(f"{member.mention} has no active warnings.")
        
        # Create embed
        embed = discord.Embed(title=f"Warnings for {member.display_name}", color=0xff9900)
        embed.add_field(name="Total Points", value=str(total_points))
        embed.add_field(name="Total Fines Paid", value=f"{humanize_number(total_fines)} Beri")
        
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
            value += f"**Expires:** {expiry_time}\n"
            
            # Add fine information if present
            fine_amount = warning.get("fine_amount", 0)
            if fine_amount > 0:
                fine_applied = warning.get("fine_applied", False)
                value += f"**Fine:** {humanize_number(fine_amount)} Beri {'(Applied)' if fine_applied else '(Failed/Partial)'}"
            
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
        
        # Create extra fields for logging
        extra_fields = [
            {"name": "Warning Points", "value": str(removed_warning.get("points", 1))},
            {"name": "Warning Reason", "value": removed_warning.get("reason", "No reason provided")},
            {"name": "New Total Points", "value": str(total_points)}
        ]
        
        # Add fine information if present
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
    async def fine_info(self, ctx, member: Optional[discord.Member] = None):
        """Show fine information for a member."""
        if member is None:
            member = ctx.author
        
        # Check permissions if checking someone else
        if member != ctx.author and not ctx.author.guild_permissions.kick_members:
            return await ctx.send("You don't have permission to view other members' fine information.")
        
        core = self._core()
        if not core:
            return await ctx.send("BeriCore is not loaded - fine information unavailable.")
        
        # Get member data
        member_data = await self.config.member(member).all()
        total_fines = member_data.get("total_fines_paid", 0)
        warning_count = member_data.get("warning_count", 0)
        current_balance = await core.get_beri(member)
        
        # Check if exempt
        is_exempt = await self._is_fine_exempt(member)
        
        # Get guild fine settings
        guild_config = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(title=f"Fine Information for {member.display_name}", color=0x00aeef)
        embed.add_field(name="Current Beri Balance", value=f"{humanize_number(current_balance)} Beri", inline=True)
        embed.add_field(name="Total Fines Paid", value=f"{humanize_number(total_fines)} Beri", inline=True)
        embed.add_field(name="Warning Count", value=str(warning_count), inline=True)
        embed.add_field(name="Fine Exempt", value="Yes" if is_exempt else "No", inline=True)
        
        # Calculate next warning fine
        if not is_exempt:
            next_fine = await self._calculate_warning_fine(member, 1)
            embed.add_field(name="Next Warning Fine (1pt)", value=f"{humanize_number(next_fine)} Beri", inline=True)
        
        # Show fine rates
        fine_info = f"**Warning Base:** {humanize_number(guild_config.get('warning_fine_base', 1000))} Beri\n"
        fine_info += f"**Escalation Multiplier:** {guild_config.get('warning_fine_multiplier', 1.5)}x\n"
        fine_info += f"**Mute Fine:** {humanize_number(guild_config.get('mute_fine', 5000))} Beri\n"
        fine_info += f"**Timeout Fine:** {humanize_number(guild_config.get('timeout_fine', 3000))} Beri\n"
        fine_info += f"**Kick Fine:** {humanize_number(guild_config.get('kick_fine', 10000))} Beri\n"
        fine_info += f"**Ban Fine:** {humanize_number(guild_config.get('ban_fine', 25000))} Beri"
        
        embed.add_field(name="Current Fine Rates", value=fine_info, inline=False)
        
        await ctx.send(embed=embed)

    async def log_action(self, guild, action, target, moderator, reason=None, extra_fields=None):
        """Log moderation actions to the log channel in a case-based format."""
        log_channel_id = await self.config.guild(guild).log_channel()
        if not log_channel_id:
            return
        
        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        # Get current case number
        case_num = await self.config.guild(guild).case_count()
        if case_num is None:
            case_num = 1
        else:
            case_num += 1
        
        # Save the incremented case number
        await self.config.guild(guild).case_count.set(case_num)
        
        # Create embed in the style shown in the example
        embed = discord.Embed(color=0x2f3136)  # Dark Discord UI color
        
        # Use the bot's actual name and avatar for the author field
        embed.set_author(name=f"{guild.me.display_name}", icon_url=guild.me.display_avatar.url)
        
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
        
        # Add the footer instead of sending a separate message
        current_time = datetime.now(timezone.utc).strftime('%I:%M %p')
        bot_name = guild.me.display_name
        embed.set_footer(text=f"{bot_name} Support • Today at {current_time}")
        
        # Create buttons for additional actions
        view = discord.ui.View()
        
        # Button to view all cautions for this user
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="View All Cautions",
            custom_id=f"cautions_view_{target.id}",
        ))
        
        # Button to clear cautions for this user
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Clear All Cautions",
            custom_id=f"cautions_clear_{target.id}",
        ))
        
        # Send the case message with buttons
        try:
            case_message = await log_channel.send(embed=embed, view=view)
        except discord.HTTPException as e:
            # Log error and try without view
            log.error(f"Error sending embed with buttons: {e}")
            try:
                case_message = await log_channel.send(embed=embed)
            except discord.HTTPException as e2:
                log.error(f"Error sending embed without buttons: {e2}")
                case_message = None
        
        # Add entry to the modlog database
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
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                    "message_id": case_message.id
                }
            )
        
        return case_message  # Return message for potential use by caller
        
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions for moderation actions."""
        if not interaction.data or not interaction.data.get("custom_id"):
            return
            
        custom_id = interaction.data["custom_id"]
        
        # Handle cautions view button
        if custom_id.startswith("cautions_view_"):
            # Extract user ID from custom_id
            try:
                user_id = int(custom_id.split("_")[-1])
                member = interaction.guild.get_member(user_id)
                
                if not member:
                    await interaction.response.send_message("Member not found or has left the server.", ephemeral=True)
                    return
                    
                # Check if the interacting user has permissions
                if not interaction.user.guild_permissions.kick_members:
                    await interaction.response.send_message("You don't have permission to view warnings.", ephemeral=True)
                    return
                    
                # Get warnings for the member
                warnings = await self.config.member(member).warnings()
                total_points = await self.config.member(member).total_points()
                total_fines = await self.config.member(member).total_fines_paid()
                
                if not warnings:
                    await interaction.response.send_message(f"{member.mention} has no active warnings.", ephemeral=True)
                    return
                    
                # Create embed with warnings
                embed = discord.Embed(title=f"Warnings for {member.display_name}", color=0xff9900)
                embed.add_field(name="Total Points", value=str(total_points))
                embed.add_field(name="Total Fines Paid", value=f"{humanize_number(total_fines)} Beri")
                
                # List all warnings (limit to prevent embed size issues)
                for i, warning in enumerate(warnings[:10], start=1):  # Show max 10 warnings
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
                    
                    # Add fine info if present
                    fine_amount = warning.get("fine_amount", 0)
                    if fine_amount > 0:
                        fine_applied = warning.get("fine_applied", False)
                        value += f"**Fine:** {humanize_number(fine_amount)} Beri {'✓' if fine_applied else '✗'}"
                    
                    embed.add_field(name=f"Warning #{i}", value=value, inline=False)
                
                if len(warnings) > 10:
                    embed.add_field(name="Note", value=f"Showing 10 of {len(warnings)} warnings. Use the cautions command to see all.", inline=False)
                    
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                await interaction.response.send_message(f"Error processing request: {str(e)}", ephemeral=True)
                
        # Handle cautions clear button
        elif custom_id.startswith("cautions_clear_"):
            # Extract user ID from custom_id
            try:
                user_id = int(custom_id.split("_")[-1])
                member = interaction.guild.get_member(user_id)
                
                if not member:
                    await interaction.response.send_message("Member not found or has left the server.", ephemeral=True)
                    return
                    
                # Check if the interacting user has permissions
                if not interaction.user.guild_permissions.kick_members:
                    await interaction.response.send_message("You don't have permission to clear warnings.", ephemeral=True)
                    return
                    
                # Check if there are warnings to clear
                warnings = await self.config.member(member).warnings()
                
                if not warnings:
                    await interaction.response.send_message(f"{member.mention} has no warnings to clear.", ephemeral=True)
                    return
                    
                # Clear warnings
                await self.config.member(member).warnings.set([])
                await self.config.member(member).total_points.set(0)
                await self.config.member(member).applied_thresholds.set([])
                
                # Log the action
                await self.log_action(
                    interaction.guild, 
                    "Clear Warnings", 
                    member, 
                    interaction.user, 
                    "Cleared via button interaction"
                )
                
                await interaction.response.send_message(f"All warnings for {member.mention} have been cleared.", ephemeral=True)
                
            except Exception as e:
                await interaction.response.send_message(f"Error processing request: {str(e)}", ephemeral=True)

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
v g
