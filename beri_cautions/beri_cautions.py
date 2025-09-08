# -*- coding: utf-8 -*-
"""
Beri Cautions — point-based cautions with thresholds, mutes, and Beri fines.

Requirements/assumptions:
- Optional Beri economy cog named "BeriCore" exposing:
    await BeriCore.add_beri(member, delta:int, reason:str, actor:discord.Member=None, bypass_cap:bool=False)
- Red-DiscordBot v3+.

Author: You + ChatGPT (fix pass)
Version: 2.3.0
"""
import asyncio
import logging
import time
from typing import Optional, Dict, Any

import discord
from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import humanize_number

log = logging.getLogger("red.cogs.beri_cautions")

EMBED_OK   = discord.Color.blurple()
EMBED_WARN = discord.Color.orange()
EMBED_ERR  = discord.Color.red()

DEFAULTS_GUILD = {
    "warning_expiry_days": 30,
    "mute_role": 0,            # role id
    "log_channel": 0,          # channel id
    # action thresholds: points -> {action: mute/timeout/kick/ban, duration: minutes, reason: str}
    "action_thresholds": {},
    # Beri fines config
    "berifine": {
        "enabled": True,
        "per_point": 1000,
        "min": 0,
        "max": 250000,
        # optional extra fine when crossing certain thresholds: points -> extra
        "thresholds": {}
    },
}

DEFAULTS_MEMBER = {
    "warnings": [],             # list of {points, reason, moderator_id, timestamp, expiry}
    "total_points": 0,
    "muted_until": 0,           # unix ts
    "applied_thresholds": []     # points crossed already (to prevent refire)
}

# ---------- helper utils ----------
def _allowed():
    return discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False)

def _to_int(s: str) -> Optional[int]:
    try:
        return int(s.strip().strip("<>#@&"))
    except Exception:
        return None

def _norm(s: str) -> str:
    return s.strip().lower()

async def _resolve_role(ctx: commands.Context, raw: str) -> Optional[discord.Role]:
    if not raw:
        return None
    # mention/ID
    rid = _to_int(raw)
    if rid:
        r = ctx.guild.get_role(rid)
        if r:
            return r
    # name (case-insensitive exact)
    q = _norm(raw)
    for r in ctx.guild.roles:
        if _norm(r.name) == q:
            return r
    return None

async def _resolve_text_channel(ctx: commands.Context, raw: str) -> Optional[discord.TextChannel]:
    if not raw:
        return None
    # mention/ID
    cid = _to_int(raw)
    if cid:
        ch = ctx.guild.get_channel(cid)
        if isinstance(ch, discord.TextChannel):
            return ch
    # name (case-insensitive exact)
    q = _norm(raw.lstrip("#"))
    for ch in ctx.guild.text_channels:
        if _norm(ch.name) == q:
            return ch
    return None

async def _send(dest, **kw):
    kw.setdefault("allowed_mentions", _allowed())
    try:
        return await dest.send(**kw)
    except Exception as e:
        log.warning("Send failed: %r", e)

# ---------- the cog ----------
class BeriCautions(commands.Cog):
    """Enhanced moderation with point cautions, thresholds, and Beri fines."""

    __version__ = "2.3.0"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=3_487_613_987, force_registration=True)
        self.config.register_guild(**DEFAULTS_GUILD)
        self.config.register_member(**DEFAULTS_MEMBER)
        self._cleanup_task = None
        self._mutecheck_task = None

    async def cog_load(self):
        self._cleanup_task = asyncio.create_task(self._warning_cleanup_loop())
        self._mutecheck_task = asyncio.create_task(self._mute_check_loop())

    async def cog_unload(self):
        for task in (self._cleanup_task, self._mutecheck_task):
            if task:
                task.cancel()

    # ---------- background: expiry of warnings ----------
    async def _warning_cleanup_loop(self):
        await self.bot.wait_until_red_ready()
        while True:
            try:
                for guild in list(self.bot.guilds):
                    gconf = await self.config.guild(guild).all()
                    expiry_days = int(gconf.get("warning_expiry_days", 30))
                    now = int(time.time())
                    allm = await self.config.all_members(guild)
                    for uid, mdata in allm.items():
                        warns = list(mdata.get("warnings", []))
                        if not warns:
                            continue
                        updated = []
                        for w in warns:
                            exp = int(w.get("expiry") or 0)
                            if exp == 0:
                                # normalize with guild expiry window
                                ts = int(w.get("timestamp", now))
                                exp = ts + expiry_days * 86400
                                w["expiry"] = exp
                            if now < exp:
                                updated.append(w)
                        if len(updated) != len(warns):
                            member = guild.get_member(int(uid))
                            mconf = self.config.member_from_ids(guild.id, int(uid))
                            await mconf.warnings.set(updated)
                            await mconf.total_points.set(sum(int(x.get("points", 1)) for x in updated))
                            # log
                            log_chan_id = int(gconf.get("log_channel") or 0)
                            if log_chan_id:
                                ch = guild.get_channel(log_chan_id)
                                if ch and member:
                                    emb = discord.Embed(
                                        title="Warnings Expired",
                                        description=f"Some warnings for {member.mention} expired.",
                                        color=EMBED_OK
                                    )
                                    emb.add_field(name="Current Points", value=str(await mconf.total_points()), inline=True)
                                    await _send(ch, embed=emb)
            except Exception as e:
                log.error("warning_cleanup_loop error: %s", e, exc_info=True)
            await asyncio.sleep(6 * 3600)

    # ---------- background: auto-unmute ----------
    async def _mute_check_loop(self):
        await self.bot.wait_until_red_ready()
        while True:
            try:
                for guild in list(self.bot.guilds):
                    gconf = await self.config.guild(guild).all()
                    mute_role_id = int(gconf.get("mute_role") or 0)
                    mute_role = guild.get_role(mute_role_id) if mute_role_id else None
                    if not mute_role:
                        continue
                    now = int(time.time())
                    allm = await self.config.all_members(guild)
                    for uid, mdata in allm.items():
                        until = int(mdata.get("muted_until") or 0)
                        if not until or now < until:
                            continue
                        member = guild.get_member(int(uid))
                        if not member:
                            continue
                        # remove role and timeout
                        try:
                            if mute_role in member.roles:
                                await member.remove_roles(mute_role, reason="Cautions: auto-unmute")
                        except Exception:
                            pass
                        try:
                            await member.timeout(None, reason="Cautions: auto-unmute")
                        except Exception:
                            pass
                        await self.config.member(member).muted_until.set(0)
                        # log
                        log_chan_id = int(gconf.get("log_channel") or 0)
                        if log_chan_id:
                            ch = guild.get_channel(log_chan_id)
                            if ch:
                                await _send(ch, embed=discord.Embed(description=f"🔊 Auto-unmuted {member.mention}.", color=EMBED_OK))
            except Exception as e:
                log.error("mute_check_loop error: %s", e, exc_info=True)
            await asyncio.sleep(60)

    # ---------- logging ----------
    async def _log_case(self, guild: discord.Guild, action: str, target: discord.Member, moderator: discord.Member, reason: Optional[str]=None, extra: Optional[Dict[str, str]]=None):
        chan_id = int(await self.config.guild(guild).log_channel() or 0)
        if not chan_id:
            return
        ch = guild.get_channel(chan_id)
        if not ch:
            return
        emb = discord.Embed(color=discord.Color.dark_embed())
        emb.title = action
        emb.description = (
            f"**User:** {target.mention} (`{target.id}`)\n"
            f"**Moderator:** {moderator.mention if moderator else guild.me.mention}\n"
            f"**Reason:** {reason or 'No reason provided'}"
        )
        if extra:
            for k, v in extra.items():
                emb.add_field(name=str(k), value=str(v), inline=False)
        emb.set_footer(text=f"{guild.me.display_name}")
        try:
            await _send(ch, embed=emb)
        except Exception:
            pass

    # ---------- Beri integration ----------
    async def _beri_add(self, member: discord.Member, delta: int, *, reason: str, actor: Optional[discord.Member], bypass_cap: bool=False) -> bool:
        core = self.bot.get_cog("BeriCore")
        if not core:
            return False
        try:
            await core.add_beri(member, delta, reason=reason, actor=actor, bypass_cap=bypass_cap)
            return True
        except Exception as e:
            log.warning("BeriCore.add_beri failed: %r", e)
            return False

    async def _apply_fine(self, ctx: commands.Context, member: discord.Member, pts_delta: int, *, crossed_threshold: Optional[int], reason: str) -> int:
        g = await self.config.guild(ctx.guild).berifine()
        if not g.get("enabled", True):
            # still ping audit with zero for visibility (optional)
            await self._beri_add(member, 0, reason="punish:caution:nofine", actor=ctx.author, bypass_cap=True)
            return 0

        per = int(g.get("per_point", 0))
        base = max(0, per * int(pts_delta))
        mn = int(g.get("min", 0))
        mx = int(g.get("max", 0))
        fine = base
        if mx > 0:
            fine = min(fine, mx)
        if mn > 0:
            fine = max(fine, mn)

        if crossed_threshold is not None:
            extra = int((g.get("thresholds") or {}).get(str(int(crossed_threshold)), 0))
            fine += max(0, extra)

        if fine <= 0:
            await self._beri_add(member, 0, reason="punish:caution:zero", actor=ctx.author, bypass_cap=True)
            return 0

        ok = await self._beri_add(member, -fine, reason=f"punish:caution:{reason}", actor=ctx.author)
        return fine if ok else 0

    # ---------- commands ----------
    @commands.command(name="caution")
    @checks.mod_or_permissions(kick_members=True)
    async def caution(self, ctx: commands.Context, member: discord.Member, points_or_reason: str = "1", *, remaining_reason: Optional[str] = None):
        """
        Issue a caution to a member. Defaults to 1 point if no integer is supplied.
        Examples:
          [p]caution @user 2 Being rude
          [p]caution @user Spamming in chat
        """
        # Parse flexible args: if first arg is int -> points, else it's part of reason
        try:
            pts = int(points_or_reason)
            reason = remaining_reason
        except ValueError:
            pts = 1
            reason = (points_or_reason + (" " + remaining_reason if remaining_reason else "")).strip()

        if pts < 1:
            return await _send(ctx, embed=discord.Embed(description="Points must be ≥ 1.", color=EMBED_WARN))

        # Read expiry
        expiry_days = int(await self.config.guild(ctx.guild).warning_expiry_days())
        now = int(time.time())
        expiry_ts = now + expiry_days * 86400
        warn = {
            "points": int(pts),
            "reason": reason or "No reason provided",
            "moderator_id": ctx.author.id,
            "timestamp": now,
            "expiry": expiry_ts
        }

        # Append warning and recompute total
        async with self.config.member(member).warnings() as warnings:
            warnings.append(warn)
        async with self.config.member(member).all() as m:
            m["total_points"] = sum(int(w.get("points", 1)) for w in m.get("warnings", []))
            total_points = int(m["total_points"])

        # Compute threshold crossing (highest single new crossing)
        thresholds = await self.config.guild(ctx.guild).action_thresholds()
        prev_points = total_points - int(pts)
        crossed = None
        crossed_entry = None
        for p_s, data in sorted(thresholds.items(), key=lambda kv: int(kv[0])):
            p = int(p_s)
            if prev_points < p <= total_points:
                crossed = p
                crossed_entry = data

        # Apply Beri fine (includes extra if threshold crossed)
        fine = await self._apply_fine(ctx, member, int(pts), crossed_threshold=crossed, reason=warn["reason"])

        # Confirmation embed
        emb = discord.Embed(title="Caution Issued", color=EMBED_WARN, description=f"{member.mention} received **{humanize_number(pts)}** caution point(s).")
        emb.add_field(name="Reason", value=warn["reason"], inline=False)
        emb.add_field(name="Total Points", value=str(total_points), inline=True)
        if fine > 0:
            emb.add_field(name="Beri Fine", value=f"-{humanize_number(fine)}", inline=True)
        emb.add_field(name="Expires", value=f"<t:{expiry_ts}:R>", inline=False)
        await _send(ctx, embed=emb)

        # Log
        await self._log_case(ctx.guild, "Warning", member, ctx.author, warn["reason"], extra={"Points": str(pts), "Total Points": str(total_points)})

        # Threshold action + stamp applied
        if crossed is not None and crossed_entry:
            async with self.config.member(member).applied_thresholds() as arr:
                if int(crossed) not in arr:
                    arr.append(int(crossed))
                    await self._apply_threshold_action(ctx, member, int(crossed), crossed_entry)

    async def _apply_threshold_action(self, ctx: commands.Context, member: discord.Member, pts: int, entry: Dict[str, Any]):
        action = str(entry.get("action", "mute")).lower()
        reason = entry.get("reason") or f"Exceeded {pts} warning points"
        duration = int(entry.get("duration", 0) or 0)

        if action == "mute":
            mute_role_id = int(await self.config.guild(ctx.guild).mute_role() or 0)
            mute_role = ctx.guild.get_role(mute_role_id) if mute_role_id else None
            if not mute_role or not ctx.guild.me.guild_permissions.manage_roles or mute_role.position >= ctx.guild.me.top_role.position:
                # fallback to timeout
                if duration <= 0:
                    duration = 10
                until = discord.utils.utcnow() + discord.timedelta(minutes=duration)
                try:
                    await member.timeout(until=until, reason=f"[Fallback] {reason}")
                    await self.config.member(member).muted_until.set(int(time.time()) + duration*60)
                    await _send(ctx, embed=discord.Embed(description=f"⏳ {member.mention} timed out for **{duration}m** (mute-role unavailable).", color=EMBED_WARN))
                except Exception as e:
                    await _send(ctx, embed=discord.Embed(description=f"Timeout failed: {e}", color=EMBED_ERR))
                await self._log_case(ctx.guild, "Auto-Timeout", member, ctx.author or ctx.guild.me, reason, extra={"Duration": f"{duration} minutes"})
                return
            # apply role mute
            try:
                await member.add_roles(mute_role, reason=reason)
                if duration > 0:
                    await self.config.member(member).muted_until.set(int(time.time()) + duration*60)
                await _send(ctx, embed=discord.Embed(description=f"🔇 {member.mention} muted" + (f" for **{duration}m**" if duration>0 else "") + ".", color=EMBED_OK))
                await self._log_case(ctx.guild, "Auto-Mute", member, ctx.author or ctx.guild.me, reason, extra={"Duration": f"{duration} minutes" if duration else "—"})
            except Exception as e:
                await _send(ctx, embed=discord.Embed(description=f"Mute failed: {e}", color=EMBED_ERR))
            return

        if action == "timeout":
            if duration <= 0:
                duration = 10
            until = discord.utils.utcnow() + discord.timedelta(minutes=duration)
            try:
                await member.timeout(until=until, reason=reason)
                await self.config.member(member).muted_until.set(int(time.time()) + duration*60)
                await _send(ctx, embed=discord.Embed(description=f"⏳ {member.mention} timed out for **{duration}m**.", color=EMBED_OK))
                await self._log_case(ctx.guild, "Auto-Timeout", member, ctx.author or ctx.guild.me, reason, extra={"Duration": f"{duration} minutes"})
            except Exception as e:
                await _send(ctx, embed=discord.Embed(description=f"Timeout failed: {e}", color=EMBED_ERR))
            return

        if action == "kick":
            try:
                await member.kick(reason=reason)
                await _send(ctx, embed=discord.Embed(description=f"👢 {member.mention} kicked.", color=EMBED_OK))
                await self._log_case(ctx.guild, "Auto-Kick", member, ctx.author or ctx.guild.me, reason)
            except Exception as e:
                await _send(ctx, embed=discord.Embed(description=f"Kick failed: {e}", color=EMBED_ERR))
            return

        if action == "ban":
            try:
                await member.ban(reason=reason, delete_message_days=0)
                await _send(ctx, embed=discord.Embed(description=f"🔨 {member.mention} banned.", color=EMBED_OK))
                await self._log_case(ctx.guild, "Auto-Ban", member, ctx.author or ctx.guild.me, reason)
            except Exception as e:
                await _send(ctx, embed=discord.Embed(description=f"Ban failed: {e}", color=EMBED_ERR))

    # ----- settings panel -----
    @commands.group(name="cautionset", invoke_without_command=True)
    @checks.admin_or_permissions(administrator=True)
    async def cautionset(self, ctx: commands.Context):
        """Caution/Beri settings panel."""
        g = await self.config.guild(ctx.guild).all()
        role = ctx.guild.get_role(int(g.get("mute_role") or 0))
        chan = ctx.guild.get_channel(int(g.get("log_channel") or 0))
        bf = g.get("berifine", {})
        th = g.get("action_thresholds", {})
        desc = (
            f"**Expiry Days:** {g.get('warning_expiry_days',30)}\n"
            f"**Mute Role:** {role.mention if role else '—'}\n"
            f"**Log Channel:** {chan.mention if chan else '—'}\n"
            f"**Beri Fines:** {'On' if bf.get('enabled',True) else 'Off'} | per_point={bf.get('per_point',0)} | range={bf.get('min',0)}–{bf.get('max',0)}\n"
            f"**Beri Fine Thresholds:** {', '.join(f'{k}:{v}' for k,v in (bf.get('thresholds') or {}).items()) or '—'}\n"
            f"**Action Thresholds:** {', '.join(f'{k}:{v.get('action','?')}' for k,v in (th or {}).items()) or '—'}"
        )
        await _send(ctx, embed=discord.Embed(title="Caution Settings", description=desc, color=EMBED_OK))

    @cautionset.command(name="expiry")
    async def cs_expiry(self, ctx: commands.Context, days: int):
        days = max(1, int(days))
        await self.config.guild(ctx.guild).warning_expiry_days.set(days)
        await _send(ctx, embed=discord.Embed(description=f"Expiry set to **{days}** days.", color=EMBED_OK))

    @cautionset.command(name="mute")
    async def cs_mute(self, ctx: commands.Context, *, role_like: str):
        r = await _resolve_role(ctx, role_like)
        if not r:
            return await _send(ctx, embed=discord.Embed(
                description="Could not resolve that role. Use a **mention**, **ID**, or **exact name**.",
                color=EMBED_ERR
            ))
        if not ctx.guild.me.guild_permissions.manage_roles or r.position >= ctx.guild.me.top_role.position:
            return await _send(ctx, embed=discord.Embed(
                description=f"I can’t set {r.mention} as mute role due to role hierarchy or missing permissions.",
                color=EMBED_ERR
            ))
        await self.config.guild(ctx.guild).mute_role.set(int(r.id))
        await _send(ctx, embed=discord.Embed(description=f"Mute role set to {r.mention}.", color=EMBED_OK))

    @cautionset.group(name="log", invoke_without_command=True)
    async def cs_log(self, ctx: commands.Context):
        await _send(ctx, embed=discord.Embed(description="Subcommands: `set <#channel|id|name>`, `disable`", color=EMBED_OK))

    @cs_log.command(name="set")
    async def cs_log_set(self, ctx: commands.Context, *, channel_like: str):
        ch = await _resolve_text_channel(ctx, channel_like)
        if not ch:
            return await _send(ctx, embed=discord.Embed(
                description="Could not resolve that channel. Use a **mention**, **ID**, or **exact name** of a text channel.",
                color=EMBED_ERR
            ))
        await self.config.guild(ctx.guild).log_channel.set(int(ch.id))
        await _send(ctx, embed=discord.Embed(description=f"Log channel set to {ch.mention}.", color=EMBED_OK))

    @cs_log.command(name="disable")
    async def cs_log_disable(self, ctx: commands.Context):
        await self.config.guild(ctx.guild).log_channel.set(0)
        await _send(ctx, embed=discord.Embed(description="Log channel disabled.", color=EMBED_OK))

    @cautionset.group(name="thresholds", invoke_without_command=True)
    async def cs_thresholds(self, ctx: commands.Context):
        th = await self.config.guild(ctx.guild).action_thresholds()
        if not th:
            return await _send(ctx, embed=discord.Embed(description="No thresholds set.", color=EMBED_WARN))
        lines = []
        for k, v in sorted(th.items(), key=lambda kv: int(kv[0])):
            act = v.get("action", "?"); dur = v.get("duration", 0); rsn = v.get("reason", "")
            extra = f" • {dur}m" if (act in {"mute","timeout"} and dur) else ""
            lines.append(f"{k} pts → **{act}**{extra}" + (f" — {rsn}" if rsn else ""))
        await _send(ctx, embed=discord.Embed(title="Action Thresholds", description="\n".join(lines), color=EMBED_OK))

    @cs_thresholds.command(name="set")
    async def cs_thresholds_set(self, ctx: commands.Context, points: int, action: str, duration: Optional[int]=None, *, reason: Optional[str]=None):
        action = action.lower()
        valid = {"mute","timeout","kick","ban"}
        if action not in valid:
            return await _send(ctx, embed=discord.Embed(description="Action must be one of: mute, timeout, kick, ban.", color=EMBED_WARN))
        entry = {"action": action}
        if action in {"mute","timeout"}:
            if duration is None:
                return await _send(ctx, embed=discord.Embed(description="Duration (minutes) is required for mute/timeout.", color=EMBED_WARN))
            entry["duration"] = int(duration)
        if reason:
            entry["reason"] = reason
        else:
            entry["reason"] = f"Exceeded {points} warning points"
        async with self.config.guild(ctx.guild).action_thresholds() as th:
            th[str(int(points))] = entry
        await _send(ctx, embed=discord.Embed(description=f"Threshold **{points}** → **{action}** set.", color=EMBED_OK))

    @cs_thresholds.command(name="remove")
    async def cs_thresholds_remove(self, ctx: commands.Context, points: int):
        async with self.config.guild(ctx.guild).action_thresholds() as th:
            if str(int(points)) in th:
                del th[str(int(points))]
                await _send(ctx, embed=discord.Embed(description=f"Removed threshold **{points}**.", color=EMBED_OK))
            else:
                await _send(ctx, embed=discord.Embed(description=f"No threshold at **{points}**.", color=EMBED_WARN))

    @cautionset.group(name="berifine", invoke_without_command=True)
    async def cs_berifine(self, ctx: commands.Context):
        g = await self.config.guild(ctx.guild).berifine()
        desc = f"**Enabled:** {'On' if g.get('enabled',True) else 'Off'}\n**Per Point:** {g.get('per_point',0)}\n**Range:** {g.get('min',0)}–{g.get('max',0)}\n**Thresholds:** {', '.join(f'{k}:{v}' for k,v in (g.get('thresholds') or {}).items()) or '—'}"
        await _send(ctx, embed=discord.Embed(title="Beri Fine Settings", description=desc, color=EMBED_OK))

    @cs_berifine.command(name="toggle")
    async def cs_berifine_toggle(self, ctx: commands.Context, value: Optional[bool]=None):
        g = await self.config.guild(ctx.guild).berifine()
        val = (not g.get("enabled", True)) if value is None else bool(value)
        g["enabled"] = val
        await self.config.guild(ctx.guild).berifine.set(g)
        await _send(ctx, embed=discord.Embed(description=f"Beri fines **{'enabled' if val else 'disabled'}**.", color=EMBED_OK))

    @cs_berifine.command(name="perpoint")
    async def cs_berifine_perpoint(self, ctx: commands.Context, amount: int):
        g = await self.config.guild(ctx.guild).berifine()
        g["per_point"] = max(0, int(amount))
        await self.config.guild(ctx.guild).berifine.set(g)
        await _send(ctx, embed=discord.Embed(description=f"Per-point fine set to **{humanize_number(g['per_point'])}** Beri.", color=EMBED_OK))

    @cs_berifine.command(name="range")
    async def cs_berifine_range(self, ctx: commands.Context, min_fine: int, max_fine: int):
        mn, mx = int(min_fine), int(max_fine)
        if mn > mx:
            mn, mx = mx, mn
        g = await self.config.guild(ctx.guild).berifine()
        g["min"] = max(0, mn)
        g["max"] = max(0, mx)
        await self.config.guild(ctx.guild).berifine.set(g)
        await _send(ctx, embed=discord.Embed(description=f"Fine range set to **{humanize_number(g['min'])}–{humanize_number(g['max'])}**.", color=EMBED_OK))

    @cs_berifine.command(name="threshold")
    async def cs_berifine_threshold(self, ctx: commands.Context, points: int, amount: int):
        g = await self.config.guild(ctx.guild).berifine()
        tf = dict(g.get("thresholds") or {})
        tf[str(int(points))] = max(0, int(amount))
        g["thresholds"] = tf
        await self.config.guild(ctx.guild).berifine.set(g)
        await _send(ctx, embed=discord.Embed(description=f"Extra fine at **{points} pts** set to **{humanize_number(amount)}**.", color=EMBED_OK))

    @cs_berifine.command(name="clearthreshold")
    async def cs_berifine_clearthreshold(self, ctx: commands.Context, points: int):
        g = await self.config.guild(ctx.guild).berifine()
        tf = dict(g.get("thresholds") or {})
        if str(int(points)) in tf:
            del tf[str(int(points))]
            g["thresholds"] = tf
            await self.config.guild(ctx.guild).berifine.set(g)
            await _send(ctx, embed=discord.Embed(description=f"Removed extra fine at **{points} pts**.", color=EMBED_OK))
        else:
            await _send(ctx, embed=discord.Embed(description=f"No extra fine set at **{points} pts**.", color=EMBED_WARN))

    # ----- utility views (optional future) -----
    # You can add buttons or slash mirrors later.

async def setup(bot):
    await bot.add_cog(BeriCautions(bot))
