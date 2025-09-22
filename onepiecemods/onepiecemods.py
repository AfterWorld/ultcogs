# onepiecemods_updated.py - Updated & hardened
# Notes:
# - Keeps reliance on `.data` and `.utils` packages.
# - Fixes: case referenced before definition in impel_down(), safer backup file creation,
#          add robust cooldown tracking for warnings, guard against missing configs,
#          ensure bg task starts, better error guards, minor typing & logging polish.

import io
import json
import logging
import random
import re
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple

import discord
from redbot.core import commands, checks, modlog, Config
from redbot.core.utils.chat_formatting import humanize_list, box, pagify
from redbot.core.utils.predicates import MessagePredicate

# Import message data (kept as-is; these must exist in your package)
from .data.kick_messages import KICK_MESSAGES, KICK_GIFS, KICK_ALIASES
from .data.ban_messages import BAN_MESSAGES, BAN_GIFS, BAN_ALIASES
from .data.mute_messages import MUTE_MESSAGES, MUTE_GIFS, MUTE_ALIASES
from .data.warn_messages import (
    WARN_MESSAGES, WARN_GIFS, WARN_ALIASES, BOUNTY_LEVELS, BOUNTY_DESCRIPTIONS
)
from .data.impel_down import IMPEL_DOWN_LEVELS, IMPEL_DOWN_MESSAGES, IMPEL_DOWN_GIFS

# Import utilities (kept as-is; these must exist in your package)
from .utils.embed_creator import EmbedCreator
from .utils.hierarchy import check_hierarchy, sanitize_reason, format_time_duration
from .utils.config_manager import ConfigManager
from .utils.webhook_logger import WebhookLogger


log = logging.getLogger("red.onepiecemods")


class DurationConverter(commands.Converter):
    """Convert duration strings like 1d2h3m, 1h30m, 45m, or plain minutes '30' to seconds."""

    async def convert(self, ctx: commands.Context, argument: str) -> int:
        pattern = re.compile(r"^(?:(?P<days>\d+)d)?(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?$")
        match = pattern.match(argument.strip())
        if not match:
            # Try plain minutes
            try:
                minutes = int(argument)
                if minutes <= 0:
                    raise ValueError()
                total = minutes * 60
            except ValueError:
                raise commands.BadArgument(
                    "Invalid duration. Use `1d2h3m`, `1h30m`, `45m`, or plain minutes like `30`."
                )
            else:
                return min(total, 7 * 24 * 60 * 60)  # cap 7 days
        days = int(match.group("days") or 0)
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        if days == 0 and hours == 0 and minutes == 0:
            raise commands.BadArgument("Duration must be at least 1 minute.")
        total_seconds = days * 86400 + hours * 3600 + minutes * 60
        max_seconds = 7 * 24 * 60 * 60
        if total_seconds > max_seconds:
            await ctx.send("⚠️ Duration capped at 7 days to match Discord limits.")
            total_seconds = max_seconds
        return total_seconds


class OnePieceMods(commands.Cog):
    """One Piece themed moderation commands 🏴‍☠️"""

    default_guild_settings: Dict[str, Any] = {
        "mute_role": None,
        "log_channel": None,
        "warnings": {},
        "active_punishments": {},
        "mod_history": {},
        "warning_cooldown": 30,
        "auto_escalation": True,
        "max_warning_level": 6,
        "escalation_levels": {  # warning_count : { level, duration(minutes) }
            3: {"level": 1, "duration": 30},
            5: {"level": 3, "duration": 60},
            7: {"level": 5, "duration": 120},
        },
        "audit_log_format": "One Piece Mods: {moderator} ({moderator_id}) | {reason}",
        "backup_enabled": True,
        "serious_mode": False,
        "webhook_url": None,
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=502050299, force_registration=True)
        self.config.register_guild(**self.default_guild_settings)
        self.config.register_member(roles=[])

        self.config_manager = ConfigManager(bot, self.config)
        self.webhook_logger = WebhookLogger(bot, self.config_manager)

        # Start background tasks
        self.bg_task: Optional[asyncio.Task] = asyncio.create_task(self.check_expired_punishments())
        self.init_casetypes_task: Optional[asyncio.Task] = asyncio.create_task(self.register_casetypes())

        # In-memory cooldown map for warnings: (guild_id, mod_id, target_id) -> timestamp
        self._warn_cooldowns: Dict[Tuple[int, int, int], float] = {}

    async def cog_unload(self):
        if self.bg_task:
            self.bg_task.cancel()
        if self.init_casetypes_task:
            self.init_casetypes_task.cancel()

    # ---------- Helper / Embed ----------
    def _minimal_action_embed(self, title: str, description: str) -> discord.Embed:
        e = discord.Embed(title=title, description=description, color=discord.Color.blurple())
        e.timestamp = datetime.now(timezone.utc)
        return e


    def create_modlog_embed(
        self,
        case_num: int,
        action_type: str,
        user: discord.Member,
        moderator: discord.Member,
        reason: Optional[str],
        timestamp: datetime,
        **kwargs: Any,
    ) -> discord.Embed:
        embed = discord.Embed(color=self.get_action_color(action_type))
        embed.title = f"Case #{case_num}"
        embed.add_field(name="Action:", value=action_type, inline=False)
        embed.add_field(name="User:", value=f"{user.mention} ({user.id})", inline=False)
        embed.add_field(name="Moderator:", value=f"{moderator.mention} ({moderator.id})", inline=False)
        embed.add_field(name="Reason:", value=reason or "No reason provided", inline=False)
        relative_time = f"({self.get_relative_time(timestamp)})"
        date_value = f"{timestamp.strftime('%B %d, %Y %I:%M %p')} {relative_time}"
        embed.add_field(name="Date:", value=date_value, inline=False)
        for name, value in kwargs.items():
            if name.lower() not in {"case_num", "action_type", "user", "moderator", "reason", "timestamp"}:
                embed.add_field(name=f"{name}:", value=value, inline=False)
        embed.set_author(name=moderator.display_name, icon_url=moderator.display_avatar.url)
        embed.set_footer(text="One Piece Moderation System", icon_url="https://i.imgur.com/Wr8xdJA.png")
        return embed

    def get_action_color(self, action_type: str) -> discord.Color:
        colors = {
            "ban": discord.Color.from_rgb(204, 0, 0),
            "kick": discord.Color.from_rgb(255, 128, 0),
            "mute": discord.Color.from_rgb(0, 102, 204),
            "warn": discord.Color.from_rgb(255, 215, 0),
            "timeout": discord.Color.from_rgb(102, 0, 153),
            "impeldown": discord.Color.from_rgb(51, 51, 51),
            "unmute": discord.Color.from_rgb(0, 204, 102),
            "unban": discord.Color.from_rgb(46, 204, 113),
            "release": discord.Color.from_rgb(46, 204, 113),
            "impelrelease": discord.Color.from_rgb(46, 204, 113),
            "bounty": discord.Color.from_rgb(255, 215, 0),
        }
        return colors.get(action_type.lower(), discord.Color.light_grey())

    def get_relative_time(self, timestamp: datetime) -> str:
        now = datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        delta = now - timestamp
        if delta.days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                minutes = max(1, delta.seconds // 60)
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        if delta.days == 1:
            return "yesterday"
        return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"

    async def format_audit_reason(self, guild: discord.Guild, moderator: discord.Member, reason: Optional[str]) -> str:
        template = await self.config.guild(guild).audit_log_format()
        return template.format(
            moderator=getattr(moderator, "display_name", "Unknown"),
            moderator_id=getattr(moderator, "id", 0),
            reason=reason or "No reason provided",
        )

    # ---------- Casetypes & Background ----------

    async def register_casetypes(self):
        try:
            await modlog.register_casetypes(
                [
                    {"name": "impeldown", "default_setting": True, "image": "⛓️", "case_str": "Impel Down Imprisonment"},
                    {"name": "impelrelease", "default_setting": True, "image": "🔓", "case_str": "Impel Down Release"},
                    {"name": "bounty", "default_setting": True, "image": "💰", "case_str": "Bounty Increase"},
                ]
            )
        except Exception as e:
            log.warning(f"Could not register casetypes: {e}")

    async def batch_update_punishments(self, guild: discord.Guild, updates: Dict[str, Optional[dict]]):
        async with self.config.guild(guild).active_punishments() as punishments:
            for user_id, update in updates.items():
                if update is None:
                    punishments.pop(str(user_id), None)
                else:
                    punishments[str(user_id)] = update

    async def check_expired_punishments(self):
        await self.bot.wait_until_ready()
        while True:
            try:
                all_guilds = await self.config.all_guilds()
                now_ts = datetime.now().timestamp()
                for guild_id, guild_data in all_guilds.items():
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue
                    active = guild_data.get("active_punishments", {})
                    expired_ops: Dict[str, Optional[dict]] = {}
                    for user_id, punishment in list(active.items()):
                        end_time = punishment.get("end_time")
                        if not end_time:
                            continue
                        if now_ts >= float(end_time):
                            member = guild.get_member(int(user_id))
                            if not member:
                                expired_ops[user_id] = None
                                continue
                            try:
                                await self.release_punishment(
                                    guild, member, "Automatic release after sentence completion"
                                )
                                expired_ops[user_id] = None
                                # Optional webhook note
                                try:
                                    await self.webhook_logger.log_punishment_expired(
                                        guild=guild,
                                        member=member,
                                        punishment_type="Impel Down",
                                        original_duration=format_time_duration(
                                            int((end_time - punishment.get("start_time", end_time)) // 60)
                                        ),
                                        level=punishment.get("level"),
                                    )
                                except Exception:
                                    pass
                            except Exception as e:
                                log.error(f"Auto-release error for {user_id} in {guild_id}: {e}")
                                try:
                                    await self.webhook_logger.log_error(
                                        guild=guild,
                                        error_type="Auto-Release Error",
                                        error_message=str(e),
                                        user=member,
                                    )
                                except Exception:
                                    pass
                    if expired_ops:
                        await self.batch_update_punishments(guild, expired_ops)
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in punishment loop: {e}")
                await asyncio.sleep(60)

    # ---------- Role Save/Restore ----------

    async def save_roles(self, member: discord.Member):
        role_ids = [r.id for r in member.roles if not r.is_default()]
        await self.config.member(member).roles.set(role_ids)

    async def restore_roles(self, guild: discord.Guild, member: discord.Member) -> bool:
        saved_role_ids: List[int] = await self.config.member(member).roles()
        if not saved_role_ids:
            return False
        to_add: List[discord.Role] = []
        for rid in saved_role_ids:
            role = guild.get_role(rid)
            if role and role not in member.roles:
                to_add.append(role)
        if to_add:
            try:
                await member.add_roles(*to_add, reason="Restoring previous roles")
                return True
            except discord.HTTPException:
                return False
        return False

    # ---------- Config helpers ----------

    async def add_warning(self, guild: discord.Guild, user: discord.Member, mod: discord.Member, reason: str) -> int:
        async with self.config.guild(guild).warnings() as warnings:
            uid = str(user.id)
            warnings.setdefault(uid, []).append(
                {"mod_id": getattr(mod, "id", 0), "reason": reason, "timestamp": datetime.now().isoformat()}
            )
            return len(warnings[uid])

    async def get_warnings(self, guild: discord.Guild, user: discord.Member) -> List[dict]:
        warnings = await self.config.guild(guild).warnings()
        return warnings.get(str(user.id), [])

    async def clear_warnings(self, guild: discord.Guild, user: discord.Member) -> bool:
        async with self.config.guild(guild).warnings() as warnings:
            uid = str(user.id)
            if uid in warnings:
                warnings[uid] = []
                return True
        return False

    async def add_punishment(self, guild: discord.Guild, user: discord.Member, level: int, duration_s: int, mod, reason):
        now_ts = datetime.now().timestamp()
        async with self.config.guild(guild).active_punishments() as punishments:
            punishments[str(user.id)] = {
                "level": level,
                "mod_id": getattr(mod, "id", 0),
                "reason": reason,
                "start_time": now_ts,
                "end_time": now_ts + duration_s,
                "active": True,
            }

    async def end_punishment(self, guild: discord.Guild, user: discord.Member) -> Optional[dict]:
        async with self.config.guild(guild).active_punishments() as punishments:
            uid = str(user.id)
            if uid in punishments:
                data = punishments[uid]
                del punishments[uid]
                return data
        return None

    async def get_active_punishment(self, guild: discord.Guild, user: discord.Member) -> Optional[dict]:
        punishments = await self.config.guild(guild).active_punishments()
        return punishments.get(str(user.id))

    async def add_mod_action(self, guild: discord.Guild, action_type: str, mod, user, reason: str, **kwargs):
        async with self.config.guild(guild).mod_history() as history:
            uid = str(user.id)
            history.setdefault(uid, []).append(
                {
                    "action_type": action_type,
                    "mod_id": getattr(mod, "id", 0),
                    "reason": reason,
                    "timestamp": datetime.now().isoformat(),
                    **kwargs,
                }
            )

    async def backup_guild_data(self, guild: discord.Guild) -> Optional[dict]:
        if not await self.config.guild(guild).backup_enabled():
            return None
        return {
            "guild_id": guild.id,
            "timestamp": datetime.now().isoformat(),
            "warnings": await self.config.guild(guild).warnings(),
            "active_punishments": await self.config.guild(guild).active_punishments(),
            "mod_history": await self.config.guild(guild).mod_history(),
        }

    async def release_punishment(self, guild: discord.Guild, member: discord.Member, reason: str) -> bool:
        try:
            punishment = await self.get_active_punishment(guild, member)
            if not punishment:
                return False

            try:
                await member.timeout(None, reason=await self.format_audit_reason(guild, guild.me, f"Released: {reason}"))
            except discord.HTTPException as e:
                if e.status != 403:
                    log.warning(f"Could not remove timeout for {member}: {e}")

            mute_role_id = await self.config.guild(guild).mute_role()
            if mute_role_id:
                mute_role = guild.get_role(mute_role_id)
                if mute_role and mute_role in member.roles:
                    try:
                        await member.remove_roles(
                            mute_role,
                            reason=await self.format_audit_reason(guild, guild.me, f"Released: {reason}"),
                        )
                    except discord.HTTPException as e:
                        log.warning(f"Could not remove mute role from {member}: {e}")

            if int(punishment.get("level", 0)) >= 3:
                for channel in guild.channels:
                    try:
                        if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                            perms = channel.overwrites_for(member)
                            if perms.view_channel is False:
                                await channel.set_permissions(
                                    member,
                                    overwrite=None,
                                    reason=await self.format_audit_reason(
                                        guild, guild.me, f"Released from Impel Down: {reason}"
                                    ),
                                )
                    except discord.HTTPException:
                        pass

            await self.restore_roles(guild, member)
            await self.end_punishment(guild, member)
            return True
        except Exception as e:
            log.error(f"Error releasing punishment: {e}")
            return False

    async def apply_level_restrictions(self, guild: discord.Guild, member: discord.Member, level: int, reason: str) -> bool:
        level_data = IMPEL_DOWN_LEVELS.get(level, {})
        restrictions = level_data.get("restrictions", [])
        ok = True
        if level >= 3:
            for channel in guild.channels:
                try:
                    if "view_channel" in restrictions and isinstance(
                        channel, (discord.TextChannel, discord.VoiceChannel)
                    ):
                        await channel.set_permissions(
                            member,
                            view_channel=False,
                            reason=await self.format_audit_reason(guild, guild.me, f"Impel Down Level {level}"),
                        )
                except discord.HTTPException:
                    ok = False
        return ok

    async def should_escalate(self, guild: discord.Guild, warning_count: int) -> Tuple[Optional[int], Optional[int]]:
        if not await self.config.guild(guild).auto_escalation():
            return None, None
        levels = await self.config.guild(guild).escalation_levels()
        # keys may be stored as str or int depending on Red version; normalize
        key = str(warning_count)
        data = levels.get(key) or levels.get(warning_count)
        if data:
            return int(data.get("level", 0)), int(data.get("duration", 0))
        return None, None

    async def create_history_pages(self, member: discord.Member, history: List[dict]) -> List[discord.Embed]:
        pages: List[discord.Embed] = []
        chunk = 5
        counts: Dict[str, int] = {}
        for entry in history:
            a = entry.get("action_type", "unknown")
            counts[a] = counts.get(a, 0) + 1

        for i in range(0, len(history), chunk):
            part = history[i : i + chunk]
            embed = discord.Embed(
                title=f"Pirate History: {member.name}",
                description=f"Moderation history for {member.mention}",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            if i == 0:
                if counts:
                    summary = "\n".join(f"{k.replace('_',' ').title()}: **{v}**" for k, v in counts.items())
                else:
                    summary = "None"
                embed.add_field(name="Action Summary", value=summary, inline=False)
            for j, action in enumerate(part, 1):
                at = action.get("action_type", "unknown").replace("_", " ").title()
                mod_id = action.get("mod_id", 0)
                mod = member.guild.get_member(int(mod_id)) if mod_id else None
                mod_name = getattr(mod, "name", "Unknown")
                ts = action.get("timestamp", "Unknown")
                try:
                    dt = datetime.fromisoformat(ts)
                    ts_disp = dt.strftime("%Y-%m-%d")
                except Exception:
                    ts_disp = ts
                reason = action.get("reason", "No reason provided")
                if len(reason) > 60:
                    reason = reason[:57] + "..."
                embed.add_field(
                    name=f"{i + j}. {at} - {ts_disp}",
                    value=f"By: {mod_name} • Reason: {reason}",
                    inline=False,
                )
            total_pages = (len(history) + chunk - 1) // chunk
            page_no = (i // chunk) + 1
            embed.set_footer(text=f"Page {page_no}/{total_pages} • Total actions: {len(history)}")
            pages.append(embed)
        return pages

    # ---------- Commands: Group & Setup ----------

    @commands.group(name="onepiecemod", aliases=["opm", "piratemod"])
    @commands.admin_or_permissions(administrator=True)
    async def opm_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                embed=discord.Embed(
                    title="One Piece Moderation",
                    description="Use `[p]onepiecemod help` to see all commands and settings.",
                    color=discord.Color.blue(),
                )
            )

    @opm_group.command(name="setup")
    async def setup_wizard(self, ctx: commands.Context):
        embed = discord.Embed(
            title="⚙️ One Piece Mods Setup Wizard",
            description="Let's configure your server for One Piece moderation!",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="What we'll set up:",
            value="• Sea Prism Stone (mute) role\n• Marine HQ (log) channel\n• Warning escalation settings\n• Other preferences",
            inline=False,
        )
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

        # Step 1: Mute Role
        prompt = discord.Embed(
            title="Step 1: Sea Prism Stone Role",
            description="Create a mute role or use an existing one?",
            color=discord.Color.blue(),
        )
        prompt.add_field(
            name="Options:",
            value="• Type `create`\n• Mention an existing role\n• Type `skip`",
            inline=False,
        )
        await ctx.send(embed=prompt)
        try:
            msg = await self.bot.wait_for(
                "message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60.0
            )
            if msg.content.lower() == "create":
                await ctx.invoke(self.set_mute_role)
            elif msg.content.lower() != "skip" and msg.role_mentions:
                await ctx.invoke(self.set_mute_role, msg.role_mentions[0])
        except asyncio.TimeoutError:
            await ctx.send("⏰ Setup wizard timed out. You can run it again anytime!")
            return

        # Step 2: Log Channel
        prompt = discord.Embed(
            title="Step 2: Marine HQ (Log Channel)",
            description="Where should moderation logs be sent?",
            color=discord.Color.blue(),
        )
        prompt.add_field(name="Options:", value="• Mention a channel\n• Type `here`\n• Type `skip`", inline=False)
        await ctx.send(embed=prompt)
        try:
            msg = await self.bot.wait_for(
                "message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60.0
            )
            if msg.content.lower() == "here":
                await ctx.invoke(self.set_log_channel)
            elif msg.content.lower() != "skip" and msg.channel_mentions:
                await ctx.invoke(self.set_log_channel, msg.channel_mentions[0])
        except asyncio.TimeoutError:
            await ctx.send("⏰ Setup wizard timed out. Configuration saved so far!")
            return

        # Step 3: Auto-escalation
        prompt = discord.Embed(
            title="Step 3: Warning Escalation",
            description="Enable automatic escalation to Impel Down based on warnings?",
            color=discord.Color.blue(),
        )
        prompt.add_field(name="Options:", value="• Type `yes` or `no`", inline=False)
        await ctx.send(embed=prompt)
        try:
            msg = await self.bot.wait_for(
                "message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60.0
            )
            if msg.content.lower() in {"yes", "y", "enable", "true", "on"}:
                await self.config.guild(ctx.guild).auto_escalation.set(True)
                await ctx.send("✅ Auto-escalation enabled!")
            elif msg.content.lower() in {"no", "n", "disable", "false", "off"}:
                await self.config.guild(ctx.guild).auto_escalation.set(False)
                await ctx.send("✅ Auto-escalation disabled!")
        except asyncio.TimeoutError:
            pass

        await ctx.send(
            embed=discord.Embed(
                title="🎉 Setup Complete!",
                description="One Piece Mods is now configured for your server!",
                color=discord.Color.green(),
            ).add_field(
                name="Next steps:",
                value=(
                    f"• Use `{ctx.clean_prefix}piratehelp` to see all commands\n"
                    f"• Customize with `{ctx.clean_prefix}opm config`"
                ),
                inline=False,
            )
        )

    @opm_group.command(name="config")
    async def config_menu(self, ctx: commands.Context):
        gconf = await self.config.guild(ctx.guild).all()
        embed = discord.Embed(
            title="⚙️ One Piece Mods Configuration", description=f"Settings for {ctx.guild.name}", color=discord.Color.blue()
        )
        mute_role = ctx.guild.get_role(gconf.get("mute_role")) if gconf.get("mute_role") else None
        log_channel = ctx.guild.get_channel(gconf.get("log_channel")) if gconf.get("log_channel") else None
        embed.add_field(name="Sea Prism Stone Role", value=mute_role.mention if mute_role else "Not set", inline=True)
        embed.add_field(name="Marine HQ Channel", value=log_channel.mention if log_channel else "Not set", inline=True)
        embed.add_field(
            name="Auto-Escalation", value="✅ Enabled" if gconf.get("auto_escalation", True) else "❌ Disabled", inline=True
        )
        embed.add_field(name="Warning Cooldown", value=f"{gconf.get('warning_cooldown', 30)} seconds", inline=True)
        embed.add_field(name="Max Warning Level", value=str(gconf.get("max_warning_level", 6)), inline=True)
        embed.add_field(
            name="Backup System", value="✅ Enabled" if gconf.get("backup_enabled", True) else "❌ Disabled", inline=True
        )
        embed.add_field(
            name="Modify Settings", value=f"Use `{ctx.clean_prefix}opm set <setting> <value>` to change settings", inline=False
        )
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

    @opm_group.command(name="set")
    async def set_config(self, ctx: commands.Context, setting: str, *, value: str):
        setting = setting.lower().strip()
        try:
            if setting == "warning_cooldown":
                cooldown = int(value)
                if cooldown < 5 or cooldown > 3600:
                    return await ctx.send("❌ Warning cooldown must be between 5 and 3600 seconds!")
                await self.config.guild(ctx.guild).warning_cooldown.set(cooldown)
                await ctx.send(f"✅ Warning cooldown set to {cooldown} seconds!")
            elif setting == "auto_escalation":
                enabled = value.lower() in {"true", "yes", "1", "enable", "on"}
                await self.config.guild(ctx.guild).auto_escalation.set(enabled)
                await ctx.send(f"✅ Auto-escalation {'enabled' if enabled else 'disabled'}!")
            elif setting == "max_warning_level":
                level = int(value)
                if level < 1 or level > 10:
                    return await ctx.send("❌ Max warning level must be between 1 and 10!")
                await self.config.guild(ctx.guild).max_warning_level.set(level)
                await ctx.send(f"✅ Max warning level set to {level}!")
            elif setting == "backup_enabled":
                enabled = value.lower() in {"true", "yes", "1", "enable", "on"}
                await self.config.guild(ctx.guild).backup_enabled.set(enabled)
                await ctx.send(f"✅ Backup system {'enabled' if enabled else 'disabled'}!")
            elif setting == "serious_mode":
                enabled = value.lower() in {"true", "yes", "1", "enable", "on"}
                await self.config.guild(ctx.guild).serious_mode.set(enabled)
                await ctx.send(f"✅ Serious mode {'enabled' if enabled else 'disabled'}! (no GIFs, minimal flavor)")
            else:
                enabled = value.lower() in {"true", "yes", "1", "enable", "on"}
                await self.config.guild(ctx.guild).backup_enabled.set(enabled)
                await ctx.send(f"✅ Backup system {'enabled' if enabled else 'disabled'}!")
            else:
                await ctx.send(f"❌ Unknown setting: `{setting}`")
        except ValueError:
            await ctx.send("❌ Invalid value for that setting!")

    
    @opm_group.command(name="active")
    async def opm_active(self, ctx: commands.Context):
        """List active punishments and remaining time."""
        data = await self.config.guild(ctx.guild).active_punishments()
        if not data:
            return await ctx.send("✅ No active punishments.")
        # Build rows
        rows = []
        now = datetime.now().timestamp()
        for uid, info in data.items():
            try:
                member = ctx.guild.get_member(int(uid))
            except Exception:
                member = None
            end_time = float(info.get("end_time", now))
            remain_s = max(0, int(end_time - now))
            remain_m = remain_s // 60
            rows.append((member.mention if member else f"`{uid}`",
                         f"Level {info.get('level','?')}",
                         format_time_duration(remain_m),
                         info.get('reason','-')))
        # Paginate into embeds
        chunk = 10
        for i in range(0, len(rows), chunk):
            embed = discord.Embed(title="⛓️ Active Punishments", color=discord.Color.dark_grey())
            for who, lvl, remain, reason in rows[i:i+chunk]:
                embed.add_field(name=f"{who} • {lvl}", value=f"Time left: **{remain}**\nReason: {reason}", inline=False)
            embed.set_footer(text=f"Showing {i+1}-{min(i+chunk,len(rows))} of {len(rows)}")
            await ctx.send(embed=embed)

    @opm_group.command(name="backup")
    async def backup_data_cmd(self, ctx: commands.Context):
        try:
            backup = await self.backup_guild_data(ctx.guild)
            if not backup:
                return await ctx.send("❌ Backups are disabled for this server!")
            payload = json.dumps(backup, indent=2).encode("utf-8")
            filename = f"onepiece_backup_{ctx.guild.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file = discord.File(fp=io.BytesIO(payload), filename=filename)
            embed = discord.Embed(
                title="📦 Backup Created",
                description="Your moderation data has been backed up!",
                color=discord.Color.green(),
            )
            embed.add_field(name="Filename", value=filename, inline=False)
            embed.add_field(
                name="Contains",
                value="• All warnings\n• Active punishments\n• Moderation history",
                inline=False,
            )
            await ctx.send(embed=embed, file=file)
        except Exception as e:
            log.error(f"Error creating backup: {e}")
            await ctx.send("❌ Failed to create backup!")

    @opm_group.command(name="setmuterole", aliases=["seaprismrole"])
    async def set_mute_role(self, ctx: commands.Context, role: Optional[discord.Role] = None):
        if role is None:
            try:
                role = await ctx.guild.create_role(
                    name="Sea Prism Stone",
                    color=discord.Color.dark_gray(),
                    reason="Automatic creation of mute role by One Piece Mods",
                )
                # Set channel perms
                for channel in ctx.guild.channels:
                    try:
                        if isinstance(channel, discord.TextChannel):
                            await channel.set_permissions(role, send_messages=False, add_reactions=False)
                        elif isinstance(channel, discord.VoiceChannel):
                            await channel.set_permissions(role, speak=False, connect=True)
                    except discord.HTTPException:
                        pass
            except discord.HTTPException as e:
                return await ctx.send(f"❌ Failed to create mute role: {e}")

        await self.config.guild(ctx.guild).mute_role.set(role.id)
        embed = discord.Embed(
            title="🔗 Sea Prism Stone Role Set",
            description=f"The Sea Prism Stone role has been set to {role.mention}!",
            color=discord.Color.green(),
        )
        embed.add_field(name="Role ID", value=str(role.id), inline=True)
        embed.add_field(name="Members with role", value=str(len(role.members)), inline=True)
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

    @opm_group.command(name="setlogchannel", aliases=["marinehq"])
    async def set_log_channel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        channel = channel or ctx.channel
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        embed = discord.Embed(
            title="🏛️ Marine HQ Set",
            description=f"Marine HQ reports will now be sent to {channel.mention}!",
            color=discord.Color.green(),
        )
        embed.add_field(name="Channel ID", value=str(channel.id), inline=True)
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

    @opm_group.command(name="help")
    async def opm_help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🏴‍☠️ One Piece Moderation - Command Manual",
            description="Here are all the commands you can use in this cog!",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="🛠️ Setup Commands",
            value=(
                f"`{ctx.clean_prefix}opm setup` — Setup wizard\n"
                f"`{ctx.clean_prefix}opm config` — View settings\n"
                f"`{ctx.clean_prefix}opm set <setting> <value>` — Change settings\n"
                f"`{ctx.clean_prefix}opm setmuterole [role]` — Set mute role\n"
                f"`{ctx.clean_prefix}opm setlogchannel [channel]` — Set log channel\n"
                f"`{ctx.clean_prefix}opm backup` — Create data backup"
            ),
            inline=False,
        )
        embed.add_field(
            name="👊 Kick Commands",
            value=(f"`{ctx.clean_prefix}luffykick @user [reason]` — Kick\nAliases: "
                   + ", ".join([ctx.clean_prefix + alias for alias in KICK_ALIASES[:3]])),
            inline=False,
        )
        embed.add_field(
            name="⚔️ Ban Commands",
            value=(f"`{ctx.clean_prefix}shanksban @user [reason]` — Ban\nAliases: "
                   + ", ".join([ctx.clean_prefix + alias for alias in BAN_ALIASES[:3]])),
            inline=False,
        )
        embed.add_field(
            name="🔇 Mute Commands",
            value=(f"`{ctx.clean_prefix}lawroom @user <duration> [reason]` — Mute\nAliases: "
                   + ", ".join([ctx.clean_prefix + alias for alias in MUTE_ALIASES[:3]])),
            inline=False,
        )
        embed.add_field(
            name="⚠️ Warning Commands",
            value=(
                f"`{ctx.clean_prefix}bountyset @user [reason]` — Warn & raise bounty\n"
                f"`{ctx.clean_prefix}bountycheck @user` — Check bounty\n"
                f"`{ctx.clean_prefix}clearbounty @user [reason]` — Clear bounty\n"
                f"Aliases: " + ", ".join([ctx.clean_prefix + alias for alias in WARN_ALIASES[:3]])
            ),
            inline=False,
        )
        embed.add_field(
            name="🏢 Impel Down Commands",
            value=(
                f"`{ctx.clean_prefix}impeldown @user <level> <duration> [reason]` — Imprison\n"
                f"`{ctx.clean_prefix}liberate @user [reason]` — Release\n"
                f"Aliases: `{ctx.clean_prefix}imprison`, `{ctx.clean_prefix}free`, `{ctx.clean_prefix}breakout`"
            ),
            inline=False,
        )
        embed.add_field(
            name="🔍 Utility Commands",
            value=(
                f"`{ctx.clean_prefix}nakama` — Server info\n"
                f"`{ctx.clean_prefix}crewhistory @user` — Mod history\n"
                f"`{ctx.clean_prefix}modstats [days]` — Mod stats\n"
                f"`{ctx.clean_prefix}piratehelp` — This help"
            ),
            inline=False,
        )
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

    # ---------- Moderation Commands ----------

    @commands.command(name="luffykick", aliases=KICK_ALIASES)
    @commands.guild_only()
    @commands.mod_or_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def luffykick(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        reason = sanitize_reason(reason)
        if member.id == ctx.author.id:
            return await ctx.send("🤔 You can't kick yourself, that's not how Devil Fruits work!")
        if not await check_hierarchy(ctx, member, "My Haki isn't strong enough to kick that user!"):
            return

        kick_message = random.choice(KICK_MESSAGES).format(user=member.mention, mod=ctx.author.mention)
        kick_gif = random.choice(KICK_GIFS)
        embed = EmbedCreator.kick_embed(user=member, mod=ctx.author, reason=reason, message=kick_message, gif=kick_gif)

        try:
            audit_reason = await self.format_audit_reason(ctx.guild, ctx.author, reason)
            await member.kick(reason=audit_reason)

            log_channel_id = await self.config.guild(ctx.guild).log_channel()
            log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None

            case = await modlog.create_case(
                bot=self.bot,
                guild=ctx.guild,
                created_at=ctx.message.created_at,
                action_type="kick",
                user=member,
                moderator=ctx.author,
                reason=reason,
            )

            if log_channel:
                log_embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="Kick",
                    user=member,
                    moderator=ctx.author,
                    reason=reason,
                    timestamp=ctx.message.created_at,
                )
                try:
                    await log_channel.send(embed=log_embed)
                except discord.HTTPException as e:
                    log.warning(f"Could not send log to channel {getattr(log_channel,'id','?')}: {e}")

            await self.add_mod_action(ctx.guild, "kick", ctx.author, member, reason)

            try:
                await self.webhook_logger.log_moderation_action(
                    guild=ctx.guild,
                    action_type="kick",
                    moderator=ctx.author,
                    target=member,
                    reason=reason,
                    case_number=getattr(case, "case_number", None),
                )
            except Exception:
                pass

            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Kick", f"Kick executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Ban", f"Ban executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Mute", f"Mute executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Impel Down", f"Impel Down executed on {member.mention}."))
            else:
                serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to kick that member!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Discord API error: {e}")
        except Exception as e:
            log.error(f"Unexpected error in luffykick: {e}")
            await ctx.send("❌ An unexpected error occurred!")

    @commands.command(name="shanksban", aliases=BAN_ALIASES)
    @commands.guild_only()
    @commands.mod_or_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def shanksban(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        reason = sanitize_reason(reason)
        if not await check_hierarchy(ctx, member, "My Haki isn't strong enough to ban this user!"):
            return

        ban_message = random.choice(BAN_MESSAGES).format(user=member.mention, mod=ctx.author.mention)
        ban_gif = random.choice(BAN_GIFS)
        embed = EmbedCreator.ban_embed(user=member, mod=ctx.author, reason=reason, message=ban_message, gif=ban_gif)

        try:
            audit_reason = await self.format_audit_reason(ctx.guild, ctx.author, reason)
            await member.ban(reason=audit_reason, delete_message_days=0)

            log_channel_id = await self.config.guild(ctx.guild).log_channel()
            log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None

            case = await modlog.create_case(
                bot=self.bot,
                guild=ctx.guild,
                created_at=ctx.message.created_at,
                action_type="ban",
                user=member,
                moderator=ctx.author,
                reason=reason,
            )

            if log_channel:
                log_embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="Ban",
                    user=member,
                    moderator=ctx.author,
                    reason=reason,
                    timestamp=ctx.message.created_at,
                )
                try:
                    await log_channel.send(embed=log_embed)
                except discord.HTTPException as e:
                    log.warning(f"Could not send log to channel {getattr(log_channel,'id','?')}: {e}")

            await self.add_mod_action(ctx.guild, "ban", ctx.author, member, reason)

            try:
                await self.webhook_logger.log_moderation_action(
                    guild=ctx.guild,
                    action_type="ban",
                    moderator=ctx.author,
                    target=member,
                    reason=reason,
                    case_number=getattr(case, "case_number", None),
                )
            except Exception:
                pass

            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Kick", f"Kick executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Ban", f"Ban executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Mute", f"Mute executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Impel Down", f"Impel Down executed on {member.mention}."))
            else:
                serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban that member!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Discord API error: {e}")
        except Exception as e:
            log.error(f"Unexpected error in shanksban: {e}")
            await ctx.send("❌ An unexpected error occurred!")

    @commands.command(name="lawroom", aliases=MUTE_ALIASES)
    @commands.guild_only()
    @commands.mod_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True, moderate_members=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lawroom(self, ctx: commands.Context, member: discord.Member, duration: DurationConverter, *, reason: Optional[str] = None):
        reason = sanitize_reason(reason)
        if not await check_hierarchy(ctx, member, "My Haki isn't strong enough to mute this user!"):
            return

        mute_role_id = await self.config.guild(ctx.guild).mute_role()
        if not mute_role_id:
            return await ctx.send(f"❌ No Sea Prism Stone role set! Use `{ctx.clean_prefix}opm setmuterole` first.")
        mute_role = ctx.guild.get_role(mute_role_id)
        if not mute_role:
            return await ctx.send("❌ The Sea Prism Stone role has been deleted. Please set it again.")
        if mute_role in member.roles:
            return await ctx.send(f"🔗 {member.mention} is already affected by Sea Prism Stone!")

        mute_message = random.choice(MUTE_MESSAGES).format(
            user=member.mention, mod=ctx.author.mention, time=format_time_duration(duration // 60)
        )
        mute_gif = random.choice(MUTE_GIFS)
        await self.save_roles(member)

        embed = EmbedCreator.mute_embed(
            user=member, mod=ctx.author, duration=duration // 60, reason=reason, message=mute_message, gif=mute_gif
        )

        try:
            audit_reason = await self.format_audit_reason(ctx.guild, ctx.author, f"Muted: {reason}")
            await member.add_roles(mute_role, reason=audit_reason)

            if ctx.guild.me.guild_permissions.moderate_members:
                until = datetime.now(timezone.utc) + timedelta(seconds=duration)
                try:
                    await member.timeout(until, reason=audit_reason)
                except discord.HTTPException as e:
                    if e.status == 403:
                        await ctx.send("⚠️ Could not apply Discord timeout, but mute role was applied.")
                    else:
                        await ctx.send("⚠️ Timeout failed, but mute role was applied.")

            log_channel_id = await self.config.guild(ctx.guild).log_channel()
            log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None

            case = await modlog.create_case(
                bot=self.bot,
                guild=ctx.guild,
                created_at=ctx.message.created_at,
                action_type="mute",
                user=member,
                moderator=ctx.author,
                reason=reason,
            )

            if log_channel:
                log_embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="Mute",
                    user=member,
                    moderator=ctx.author,
                    reason=reason,
                    timestamp=ctx.message.created_at,
                    Duration=format_time_duration(duration // 60),
                )
                try:
                    await log_channel.send(embed=log_embed)
                except discord.HTTPException as e:
                    log.warning(f"Could not send log to channel {getattr(log_channel,'id','?')}: {e}")

            await self.add_mod_action(ctx.guild, "mute", ctx.author, member, reason, duration=duration // 60)

            try:
                await self.webhook_logger.log_moderation_action(
                    guild=ctx.guild,
                    action_type="mute",
                    moderator=ctx.author,
                    target=member,
                    reason=reason,
                    case_number=getattr(case, "case_number", None),
                    duration=format_time_duration(duration // 60),
                )
            except Exception:
                pass

            await self.add_punishment(ctx.guild, member, level=1, duration_s=duration, mod=ctx.author, reason=reason)
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Kick", f"Kick executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Ban", f"Ban executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Mute", f"Mute executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Impel Down", f"Impel Down executed on {member.mention}."))
            else:
                serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage that member's roles!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Discord API error: {e}")
        except Exception as e:
            log.error(f"Unexpected error in lawroom: {e}")
            await ctx.send("❌ An unexpected error occurred!")

    @commands.command(name="bountyset", aliases=WARN_ALIASES)
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def bountyset(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        if not await check_hierarchy(ctx, member, "My Haki isn't strong enough to warn this user!"):
            return

        # In-memory cooldown that respects guild-configured cooldown seconds
        cooldown = await self.config.guild(ctx.guild).warning_cooldown()
        key = (ctx.guild.id, ctx.author.id, member.id)
        now = datetime.now().timestamp()
        last = self._warn_cooldowns.get(key, 0.0)
        delta = now - last
        if delta < cooldown:
            remain = cooldown - delta
            return await ctx.send(f"⚠️ Please wait {remain:.1f}s before setting another bounty on {member.mention}.")
        self._warn_cooldowns[key] = now

        reason = sanitize_reason(reason)
        warning_count = await self.add_warning(ctx.guild, member, ctx.author, reason)

        max_level = await self.config.guild(ctx.guild).max_warning_level()
        level = min(warning_count, max_level)
        bounty_amt = BOUNTY_LEVELS.get(level, BOUNTY_LEVELS[max(BOUNTY_LEVELS)])
        bounty_desc = BOUNTY_DESCRIPTIONS.get(level, BOUNTY_DESCRIPTIONS[max(BOUNTY_DESCRIPTIONS)])

        warn_message = random.choice(WARN_MESSAGES).format(user=member.mention, mod=ctx.author.mention, level=warning_count)
        warn_gif = random.choice(WARN_GIFS)

        embed = EmbedCreator.warn_embed(
            user=member,
            mod=ctx.author,
            level=warning_count,
            reason=reason,
            message=warn_message,
            gif=warn_gif,
            bounty_level=bounty_amt,
            bounty_description=bounty_desc,
        )

        esc_level, esc_dur = await self.should_escalate(ctx.guild, warning_count)
        if esc_level and esc_dur:
            if warning_count == 3:
                embed.add_field(
                    name="Escalation",
                    value=f"⚠️ Bounty level 3 reached! {member.mention} will be sent to Impel Down Level {esc_level}!",
                    inline=False,
                )
            elif warning_count == 5:
                embed.add_field(
                    name="Escalation",
                    value=f"⚠️⚠️ Bounty level 5 reached! {member.mention} will be sent to Impel Down Level {esc_level}!",
                    inline=False,
                )
            elif warning_count >= 7:
                embed.add_field(
                    name="Escalation",
                    value=f"⚠️⚠️⚠️ ALERT! Bounty level {warning_count}! {member.mention} will be sent to Impel Down Level {esc_level}!",
                    inline=False,
                )

        log_channel_id = await self.config.guild(ctx.guild).log_channel()
        log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None

        case = await modlog.create_case(
            bot=self.bot,
            guild=ctx.guild,
            created_at=ctx.message.created_at,
            action_type="bounty",
            user=member,
            moderator=ctx.author,
            reason=f"Bounty Level {warning_count}: {reason}",
        )

        if log_channel:
            log_embed = self.create_modlog_embed(
                case_num=case.case_number,
                action_type="Bounty",
                user=member,
                moderator=ctx.author,
                reason=reason,
                timestamp=ctx.message.created_at,
                **{"Bounty Level": f"Level {warning_count}", "Bounty Amount": bounty_amt},
            )
            try:
                await log_channel.send(embed=log_embed)
            except discord.HTTPException as e:
                log.warning(f"Could not send log to channel {getattr(log_channel,'id','?')}: {e}")

        await self.add_mod_action(ctx.guild, "warn", ctx.author, member, reason, level=warning_count)

        try:
            await self.webhook_logger.log_moderation_action(
                guild=ctx.guild,
                action_type="warn",
                moderator=ctx.author,
                target=member,
                reason=reason,
                case_number=getattr(case, "case_number", None),
                level=warning_count,
                bounty_amount=bounty_amt,
            )
        except Exception:
            pass

            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

        # Escalation after short delay so the warning shows first
        if esc_level and esc_dur:
            try:
                await self.webhook_logger.log_escalation(
                    guild=ctx.guild,
                    member=member,
                    warning_level=warning_count,
                    escalation_level=esc_level,
                    escalation_duration=f"{esc_dur} minutes",
                    moderator=ctx.author,
                )
            except Exception:
                pass
            self.bot.loop.create_task(
                self.delayed_escalation(ctx, member, esc_level, esc_dur, f"Automatic after warning level {warning_count}: {reason}")
            )

    @commands.command(name="impeldown", aliases=["imprison"])
    @commands.guild_only()
    @commands.mod_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True, moderate_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def impel_down_cmd(self, ctx: commands.Context, member: discord.Member, level: int, duration: DurationConverter, *, reason: Optional[str] = None):
        # DurationConverter returns seconds; impel_down expects minutes
        await self.impel_down(ctx, member, level, duration // 60, reason)

    async def delayed_escalation(self, ctx: commands.Context, member: discord.Member, level: int, duration_m: int, reason: str, delay: int = 2):
        await asyncio.sleep(delay)
        await self.impel_down(ctx, member, level, duration_m, reason)

    async def impel_down(self, ctx: commands.Context, member: discord.Member, level: int, duration_m: int, reason: Optional[str] = None):
        if not isinstance(level, int) or level < 1 or level > 6:
            return await ctx.send("❌ Impel Down levels must be a number from 1 to 6!")
        if not isinstance(duration_m, int) or duration_m < 1:
            return await ctx.send("❌ Duration must be a positive number of minutes!")
        if duration_m > 10080:
            duration_m = 10080
            await ctx.send("⚠️ Duration capped at 7 days (10080 minutes) to match Discord limits.")
        if not await check_hierarchy(ctx, member, "My Haki isn't strong enough to imprison this user!"):
            return
        if not (ctx.me.guild_permissions.manage_roles and ctx.me.guild_permissions.moderate_members):
            missing = []
            if not ctx.me.guild_permissions.manage_roles:
                missing.append("Manage Roles")
            if not ctx.me.guild_permissions.moderate_members:
                missing.append("Moderate Members")
            return await ctx.send(f"❌ I need the following permissions to use Impel Down: {', '.join(missing)}")

        level_data = IMPEL_DOWN_LEVELS.get(level)
        if not level_data:
            return await ctx.send("❌ Invalid Impel Down level!")

        active = await self.get_active_punishment(ctx.guild, member)
        if active and active.get("active"):
            return await ctx.send(
                f"❌ {member.mention} is already imprisoned in Impel Down! Use `{ctx.clean_prefix}liberate` first."
            )

        reason = sanitize_reason(reason)
        impel_message = random.choice(IMPEL_DOWN_MESSAGES.get(level, IMPEL_DOWN_MESSAGES[1])).format(
            user=member.mention, mod=ctx.author.mention, time=duration_m
        )
        impel_gif = random.choice(IMPEL_DOWN_GIFS.get(level, IMPEL_DOWN_GIFS[1]))

        await self.save_roles(member)

        embed = EmbedCreator.impel_down_embed(
            user=member,
            mod=ctx.author,
            level=level,
            duration=duration_m,
            reason=reason,
            message=impel_message,
            gif=impel_gif,
            level_data=level_data,
        )

        # Record active punishment before applying discord actions so auto-release has a record even if later steps fail
        await self.add_punishment(ctx.guild, member, level, duration_m * 60, ctx.author, reason)
        await self.add_mod_action(ctx.guild, "impeldown", ctx.author, member, reason, duration=duration_m, level=level)

        # Apply Discord timeout + role + restrictions
        audit_reason = await self.format_audit_reason(ctx.guild, ctx.author, f"Impel Down Level {level}: {reason}")
        try:
            timeout_until = datetime.now(timezone.utc) + timedelta(minutes=duration_m)
            try:
                await member.timeout(timeout_until, reason=audit_reason)
            except discord.HTTPException as e:
                if e.status == 403:
                    await ctx.send("⚠️ I don't have permission to timeout this member!")
                else:
                    await ctx.send(f"⚠️ Could not apply Discord timeout: {e}")
                try:
                    await self.webhook_logger.log_error(
                        guild=ctx.guild, error_type="Timeout Error", error_message=str(e), command="impeldown", user=ctx.author
                    )
                except Exception:
                    pass

            mute_role_id = await self.config.guild(ctx.guild).mute_role()
            if mute_role_id:
                mute_role = ctx.guild.get_role(mute_role_id)
                if mute_role:
                    try:
                        await member.add_roles(mute_role, reason=audit_reason)
                    except discord.HTTPException as e:
                        await ctx.send(f"⚠️ Could not apply mute role: {e}")
                        try:
                            await self.webhook_logger.log_error(
                                guild=ctx.guild, error_type="Role Error", error_message=str(e), command="impeldown", user=ctx.author
                            )
                        except Exception:
                            pass

            if not await self.apply_level_restrictions(ctx.guild, member, level, reason):
                await ctx.send("⚠️ Warning: Could not apply all restrictions. The punishment may not be fully effective.")

            # Create case AFTER actions, so case number reflects the applied state
            case = await modlog.create_case(
                bot=self.bot,
                guild=ctx.guild,
                created_at=ctx.message.created_at,
                action_type="impeldown",
                user=member,
                moderator=ctx.author,
                reason=f"Impel Down Level {level}: {reason}",
            )

            log_channel_id = await self.config.guild(ctx.guild).log_channel()
            log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None
            if log_channel:
                log_embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="ImpelDown",
                    user=member,
                    moderator=ctx.author,
                    reason=f"Level {level}: {reason}",
                    timestamp=ctx.message.created_at,
                    Duration=f"{duration_m} minutes",
                    Level=f"Level {level}",
                )
                try:
                    await log_channel.send(embed=log_embed)
                except discord.HTTPException as e:
                    log.warning(f"Could not send log to channel {getattr(log_channel,'id','?')}: {e}")

            try:
                await self.webhook_logger.log_moderation_action(
                    guild=ctx.guild,
                    action_type="impeldown",
                    moderator=ctx.author,
                    target=member,
                    reason=reason,
                    case_number=getattr(case, "case_number", None),
                    duration=f"{duration_m} minutes",
                    level=level,
                    level_name=level_data.get("name", f"Level {level}"),
                )
            except Exception:
                pass

            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Kick", f"Kick executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Ban", f"Ban executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Mute", f"Mute executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Impel Down", f"Impel Down executed on {member.mention}."))
            else:
                serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to apply Impel Down restrictions!")
        except Exception as e:
            log.error(f"Unexpected error in impel_down: {e}")
            try:
                await self.webhook_logger.log_error(
                    guild=ctx.guild, error_type="Impel Down Error", error_message=str(e), command="impeldown", user=ctx.author
                )
            except Exception:
                pass
            await ctx.send("❌ An unexpected error occurred!")

    @commands.command(name="liberate", aliases=["free", "breakout"])
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True, moderate_members=True)
    async def release_command(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        reason = sanitize_reason(reason)
        punishment = await self.get_active_punishment(ctx.guild, member)
        if not punishment or not punishment.get("active", False):
            return await ctx.send(f"❌ {member.mention} is not currently imprisoned in Impel Down!")
        try:
            level = punishment.get("level", "Unknown")
            success = await self.release_punishment(ctx.guild, member, f"Released by {ctx.author}: {reason}")
            if not success:
                return await ctx.send("❌ Failed to release the prisoner. The Sea Prism Stone is too strong!")

            embed = EmbedCreator.release_embed(user=member, mod=ctx.author, reason=reason, previous_level=level)

            log_channel_id = await self.config.guild(ctx.guild).log_channel()
            log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None

            case = await modlog.create_case(
                bot=self.bot,
                guild=ctx.guild,
                created_at=ctx.message.created_at,
                action_type="impelrelease",
                user=member,
                moderator=ctx.author,
                reason=reason,
            )

            if log_channel:
                log_embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="ImpelRelease",
                    user=member,
                    moderator=ctx.author,
                    reason=reason,
                    timestamp=ctx.message.created_at,
                    Previous_Level=f"Level {level}",
                )
                try:
                    await log_channel.send(embed=log_embed)
                except discord.HTTPException as e:
                    log.warning(f"Could not send log to channel {getattr(log_channel,'id','?')}: {e}")

            await self.add_mod_action(ctx.guild, "impeldown_release", ctx.author, member, reason, previous_level=level)

            try:
                await self.webhook_logger.log_moderation_action(
                    guild=ctx.guild,
                    action_type="release",
                    moderator=ctx.author,
                    target=member,
                    reason=reason,
                    case_number=getattr(case, "case_number", None),
                    previous_level=f"Level {level}",
                )
            except Exception:
                pass

            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Kick", f"Kick executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Ban", f"Ban executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Mute", f"Mute executed on {member.mention}."))
            else:
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Impel Down", f"Impel Down executed on {member.mention}."))
            else:
                serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to release this member!")
        except Exception as e:
            log.error(f"Unexpected error in release_command: {e}")
            try:
                await self.webhook_logger.log_error(
                    guild=ctx.guild, error_type="Release Error", error_message=str(e), command="liberate", user=ctx.author
                )
            except Exception:
                pass
            await ctx.send("❌ An unexpected error occurred!")

    
    @commands.command(name="release", aliases=["unmute"])
    @commands.guild_only()
    @commands.mod_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True, moderate_members=True)
    async def release_command(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        """Remove Sea Prism Stone (mute) and clear Discord timeout without touching channel-level Impel restrictions.
        If a simple level-1 punishment exists, it will be ended.
        """
        reason = sanitize_reason(reason)
        audit_reason = await self.format_audit_reason(ctx.guild, ctx.author, f"Unmute: {reason}")
        mute_role_id = await self.config.guild(ctx.guild).mute_role()
        had_action = False
        try:
            # Clear timeout if present
            try:
                await member.timeout(None, reason=audit_reason)
                had_action = True
            except discord.HTTPException:
                pass
            # Remove mute role
            if mute_role_id:
                mute_role = ctx.guild.get_role(mute_role_id)
                if mute_role and mute_role in member.roles:
                    try:
                        await member.remove_roles(mute_role, reason=audit_reason)
                        had_action = True
                    except discord.HTTPException:
                        pass
            # If there is an active punishment and it's level 1, end it
            active = await self.get_active_punishment(ctx.guild, member)
            if active:
                level = int(active.get("level", 0))
                if level <= 1:
                    await self.end_punishment(ctx.guild, member)
            # Log mod action
            if had_action:
                case = await modlog.create_case(
                    bot=self.bot,
                    guild=ctx.guild,
                    created_at=ctx.message.created_at,
                    action_type="unmute",
                    user=member,
                    moderator=ctx.author,
                    reason=reason or "Unmuted",
                )
                # Send confirmation
                serious = await self.config.guild(ctx.guild).serious_mode()
                if serious:
                    await ctx.send(embed=self._minimal_action_embed("Unmute", f"Unmuted {member.mention}."))
                else:
                    e = discord.Embed(title="🔓 Released from Sea Prism Stone", color=discord.Color.green())
                    e.description = f"{member.mention} has been unmuted by {ctx.author.mention}."
                    await ctx.send(embed=e)
            else:
                await ctx.send("ℹ️ Nothing to unmute on that member.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to unmute this member!")
        except Exception as e:
            log.error(f"Unexpected error in release_command: {e}")
            await ctx.send("❌ An unexpected error occurred while unmuting.")

    @commands.command(name="clearbounty", aliases=["forgive", "pardon"])
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def clearbounty(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        reason = sanitize_reason(reason)
        warnings = await self.get_warnings(ctx.guild, member)
        if not warnings:
            return await ctx.send(f"💰 {member.mention} doesn't have a bounty to clear!")
        prev = len(warnings)
        await self.clear_warnings(ctx.guild, member)
        embed = discord.Embed(
            title="💚 Bounty Cleared!",
            description=f"Fleet Admiral {ctx.author.mention} has pardoned {member.mention}!",
            color=discord.Color.green(),
        )
        embed.add_field(name="Previous Bounty Level", value=f"Level {prev}", inline=True)
        embed.add_field(name="Reason", value=reason or "No reason provided", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url="https://media.giphy.com/media/xT5LMHxhOfscxPfIfm/giphy.gif")

        case = await modlog.create_case(
            bot=self.bot,
            guild=ctx.guild,
            created_at=ctx.message.created_at,
            action_type="bounty",
            user=member,
            moderator=ctx.author,
            reason=f"Bounty Cleared: {reason}",
        )

        await self.add_mod_action(ctx.guild, "clear_warnings", ctx.author, member, reason, previous_level=prev)

        try:
            await self.webhook_logger.log_moderation_action(
                guild=ctx.guild,
                action_type="clear_warnings",
                moderator=ctx.author,
                target=member,
                reason=reason,
                case_number=getattr(case, "case_number", None),
                previous_level=prev,
            )
        except Exception:
            pass

            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

    # ---------- Extra Utilities ----------

    @opm_group.command(name="active")
    async def list_active_punishments(self, ctx: commands.Context):
        """Show all active Impel Down / mute punishments in this server."""
        punishments = await self.config.guild(ctx.guild).active_punishments()
        if not punishments:
            return await ctx.send("✅ No active punishments in this server.")
        now_ts = datetime.now().timestamp()
        embed = discord.Embed(
            title=f"⛓️ Active Punishments in {ctx.guild.name}",
            color=discord.Color.dark_gray(),
            timestamp=datetime.now(timezone.utc),
        )
        for uid, data in punishments.items():
            try:
                member = ctx.guild.get_member(int(uid)) or f"ID {uid}"
            except Exception:
                member = f"ID {uid}"
            level = data.get("level", "N/A")
            end = data.get("end_time")
            if end:
                remain_s = max(0, int(end - now_ts))
                remain = format_time_duration(remain_s // 60)
            else:
                remain = "Indefinite"
            reason = data.get("reason", "No reason provided")
            embed.add_field(
                name=f"{member} — Level {level}",
                value=f"Remaining: {remain}\nReason: {reason}",
                inline=False,
            )
            serious = await self.config.guild(ctx.guild).serious_mode()
            if serious:
                await ctx.send(embed=self._minimal_action_embed("Warn", f"Warn executed on {member.mention}."))
            else:
            await ctx.send(embed=embed)

    @opm_group.command(name="seriousmode")
    async def toggle_serious_mode(self, ctx: commands.Context, value: Optional[bool] = None):
        """Toggle serious mode (no GIFs / fun messages)."""
        if value is None:
            current = await self.config.guild(ctx.guild).get_raw("serious_mode", default=False)
            return await ctx.send(f"⚙️ Serious Mode is currently {'ON' if current else 'OFF'}.")
        await self.config.guild(ctx.guild).set_raw("serious_mode", value=value)
        await ctx.send(f"✅ Serious Mode {'enabled' if value else 'disabled'}!")

