
# -*- coding: utf-8 -*-
import asyncio
import time
from typing import Optional, Dict, Any

import discord
from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import humanize_number

EMBED_OK   = discord.Color.blurple()
EMBED_WARN = discord.Color.orange()
EMBED_ERR  = discord.Color.red()

DEFAULTS_GUILD = {
    "expiry_days": 30,
    "mute_role": 0,              # role id
    "log_channel": 0,            # channel id
    "thresholds": {              # points -> action
        # "3": {"kind":"mute","minutes":30,"reason":"Exceeded 3 points"},
        # "5": {"kind":"timeout","minutes":60,"reason":"Exceeded 5 points"},
    },
    "berifine": {
        "enabled": True,
        "per_point": 1000,
        "min": 0,
        "max": 250000,
        "thresholds": {          # extra fine when crossing a threshold
            # "3": 2500,
            # "5": 5000
        }
    }
}

DEFAULTS_MEMBER = {
    "points": 0,
    "history": [],               # list of {time, points, reason, mod_id}
    "applied_thresholds": [],    # list[int points] to avoid re-firing
    "muted_until": 0,            # ts
}

def _no_ping_send(dest, **kw):
    kw.setdefault("allowed_mentions", discord.AllowedMentions.none())
    return dest.send(**kw)

class BeriCautions(commands.Cog):
    """Cautions with Beri fines, thresholds, and auto actions."""

    __version__ = "2.1.0"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=820_515_001, force_registration=True)
        self.config.register_guild(**DEFAULTS_GUILD)
        self.config.register_member(**DEFAULTS_MEMBER)
        self._bg = None

    async def cog_load(self):
        self._bg = asyncio.create_task(self._ticker())

    async def cog_unload(self):
        if self._bg:
            self._bg.cancel()

    # ---------- background: expire mutes ----------
    async def _ticker(self):
        await self.bot.wait_until_red_ready()
        while True:
            try:
                for guild in list(self.bot.guilds):
                    now = int(time.time())
                    allm = await self.config.all_members(guild)
                    mute_role_id = await self.config.guild(guild).mute_role()
                    mute_role = guild.get_role(int(mute_role_id)) if mute_role_id else None
                    for uid, data in allm.items():
                        until = int(data.get("muted_until", 0) or 0)
                        if until and now >= until:
                            m = guild.get_member(int(uid))
                            if not m:
                                continue
                            # remove role + clear timeout
                            if mute_role and mute_role in m.roles:
                                try: await m.remove_roles(mute_role, reason="Cautions: auto-unmute")
                                except Exception: pass
                            try: await m.timeout(None, reason="Cautions: auto-unmute")
                            except Exception: pass
                            await self.config.member(m).muted_until.set(0)
                            # zero-delta audit ping
                            core = self.bot.get_cog("BeriCore")
                            if core:
                                try: await core.add_beri(m, 0, reason="punish:unmute:auto", actor=None, bypass_cap=True)
                                except Exception: pass
                await asyncio.sleep(45)
            except Exception:
                await asyncio.sleep(60)

    # ---------- helpers ----------
    async def _log(self, guild: discord.Guild, embed: discord.Embed):
        chan_id = await self.config.guild(guild).log_channel()
        if not chan_id:
            return
        ch = guild.get_channel(int(chan_id))
        if ch:
            try: await _no_ping_send(ch, embed=embed)
            except Exception: pass

    async def _apply_fine(self, ctx: commands.Context, member: discord.Member, pts_delta: int, *, crossed_threshold: Optional[int]=None, reason: str="caution"):
        g = await self.config.guild(ctx.guild).berifine()
        if not g.get("enabled", True):
            # still ping audit for visibility
            core = self.bot.get_cog("BeriCore")
            if core:
                try: await core.add_beri(member, 0, reason="punish:caution:nofine", actor=ctx.author, bypass_cap=True)
                except Exception: pass
            return 0

        base = max(0, int(g.get("per_point", 0)) * int(pts_delta))
        mn = int(g.get("min", 0)); mx = int(g.get("max", 0))
        fine = base
        if mx > 0: fine = min(fine, mx)
        if mn > 0: fine = max(fine, mn)

        # threshold kicker
        if crossed_threshold is not None:
            extra = int((g.get("thresholds") or {}).get(str(int(crossed_threshold)), 0))
            fine += max(0, extra)

        if fine <= 0:
            core = self.bot.get_cog("BeriCore")
            if core:
                try: await core.add_beri(member, 0, reason="punish:caution:zero", actor=ctx.author, bypass_cap=True)
                except Exception: pass
            return 0

        core = self.bot.get_cog("BeriCore")
        if not core:
            return 0
        try:
            await core.add_beri(member, -fine, reason=f"punish:caution:{reason}", actor=ctx.author)
            return fine
        except Exception:
            return 0

    async def _apply_threshold_action(self, ctx: commands.Context, member: discord.Member, pts: int, entry: Dict[str, Any]):
        """Apply a configured action at a threshold; defensive with fallbacks."""
        kind = str(entry.get("kind", "mute")).lower()
        minutes = int(entry.get("minutes", 0) or 0)
        rsn = entry.get("reason") or f"Exceeded {pts} caution points"

        mute_role_id = await self.config.guild(ctx.guild).mute_role()
        mute_role = ctx.guild.get_role(int(mute_role_id)) if mute_role_id else None

        # MUTE
        if kind == "mute":
            # If cannot use role, fallback to timeout
            if not mute_role or not ctx.guild.me.guild_permissions.manage_roles or (mute_role.position >= ctx.guild.me.top_role.position):
                if minutes <= 0: minutes = 10
                try:
                    until = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
                except AttributeError:
                    # fallback for older discord.py
                    from datetime import datetime, timedelta, timezone
                    until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
                try:
                    await member.timeout(until=until, reason=f"[Fallback] {rsn}")
                    await self.config.member(member).muted_until.set(int(time.time()) + minutes*60)
                    emb = discord.Embed(description=f"⏳ {member.mention} timed out for **{minutes}m** (mute-role unavailable).", color=EMBED_WARN)
                    await _no_ping_send(ctx, embed=emb)
                except Exception as e:
                    await _no_ping_send(ctx, embed=discord.Embed(description=f"Timeout failed: {e}", color=EMBED_ERR))
                return
            # Apply role
            try:
                await member.add_roles(mute_role, reason=rsn)
                if minutes > 0:
                    await self.config.member(member).muted_until.set(int(time.time()) + minutes*60)
                emb = discord.Embed(description=f"🔇 {member.mention} muted" + (f" for **{minutes}m**" if minutes>0 else "") + f".", color=EMBED_OK)
                await _no_ping_send(ctx, embed=emb)
            except Exception as e:
                await _no_ping_send(ctx, embed=discord.Embed(description=f"Mute failed: {e}", color=EMBED_ERR))
            return

        # TIMEOUT
        if kind == "timeout":
            if minutes <= 0: minutes = 10
            try:
                until = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
            except AttributeError:
                from datetime import datetime, timedelta, timezone
                until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
            try:
                await member.timeout(until=until, reason=rsn)
                await self.config.member(member).muted_until.set(int(time.time()) + minutes*60)
                await _no_ping_send(ctx, embed=discord.Embed(description=f"⏳ {member.mention} timed out for **{minutes}m**.", color=EMBED_OK))
            except Exception as e:
                await _no_ping_send(ctx, embed=discord.Embed(description=f"Timeout failed: {e}", color=EMBED_ERR))
            return

        # KICK
        if kind == "kick":
            try:
                await member.kick(reason=rsn)
                await _no_ping_send(ctx, embed=discord.Embed(description=f"👢 {member.mention} kicked.", color=EMBED_OK))
            except Exception as e:
                await _no_ping_send(ctx, embed=discord.Embed(description=f"Kick failed: {e}", color=EMBED_ERR))
            return

        # BAN
        if kind == "ban":
            try:
                await member.ban(reason=rsn, delete_message_days=0)
                await _no_ping_send(ctx, embed=discord.Embed(description=f"🔨 {member.mention} banned.", color=EMBED_OK))
            except Exception as e:
                await _no_ping_send(ctx, embed=discord.Embed(description=f"Ban failed: {e}", color=EMBED_ERR))
            return

    # ---------- commands: core ----------
    @commands.command(name="caution")
    @checks.mod_or_permissions(kick_members=True)
    async def caution(self, ctx: commands.Context, member: discord.Member, points: int=1, *, reason: str="No reason provided"):
        """Issue a caution to a member (adds points, applies fines, checks thresholds)."""
        if points < 1:
            return await _no_ping_send(ctx, embed=discord.Embed(description="Points must be ≥ 1.", color=EMBED_WARN))

        # update member state
        async with self.config.member(member).all() as u:
            old_pts = int(u.get("points", 0))
            u["points"] = old_pts + int(points)
            (u.setdefault("history", [])).append({"time": int(time.time()), "points": int(points), "reason": reason, "mod_id": ctx.author.id})
            new_pts = int(u["points"])
            applied = set(int(x) for x in (u.get("applied_thresholds", []) or []))

        # find threshold crossing (highest only)
        thresholds = await self.config.guild(ctx.guild).thresholds()
        crossed = None
        entry = None
        for p_s, data in sorted(thresholds.items(), key=lambda kv: int(kv[0])):
            p = int(p_s)
            if old_pts < p <= new_pts and p not in applied:
                crossed = p
                entry = data
        # fine
        fine = await self._apply_fine(ctx, member, points, crossed_threshold=crossed, reason=reason)

        # visuals
        emb = discord.Embed(title="Caution Issued", color=EMBED_WARN, description=f"{member.mention} received **{humanize_number(points)}** caution point(s).")
        emb.add_field(name="Reason", value=reason, inline=False)
        emb.add_field(name="Total Points", value=str(new_pts), inline=True)
        if fine > 0:
            emb.add_field(name="Beri Fine", value=f"-{humanize_number(fine)}", inline=True)
        await _no_ping_send(ctx, embed=emb)

        # log channel
        log_e = discord.Embed(title="Caution", color=EMBED_WARN, description=f"**User:** {member} (`{member.id}`)\n**Mod:** {ctx.author} (`{ctx.author.id}`)\n**Points:** {points}\n**Reason:** {reason}\n**Total:** {new_pts}")
        await self._log(ctx.guild, log_e)

        # threshold action
        if crossed is not None and entry:
            # stamp applied
            async with self.config.member(member).applied_thresholds() as arr:
                arr.append(int(crossed))
            await self._apply_threshold_action(ctx, member, int(crossed), entry)
            # audit ping
            core = self.bot.get_cog("BeriCore")
            if core:
                try: await core.add_beri(member, 0, reason=f"punish:threshold:{int(crossed)}", actor=ctx.author, bypass_cap=True)
                except Exception: pass

    @commands.command(name="cautions")
    async def cautions(self, ctx: commands.Context, member: Optional[discord.Member]=None):
        """Show a member's current cautions and total points."""
        member = member or ctx.author
        u = await self.config.member(member).all()
        pts = int(u.get("points", 0))
        hist = u.get("history", [])
        if not hist:
            return await _no_ping_send(ctx, embed=discord.Embed(description=f"{member.mention} has no active cautions.", color=EMBED_OK))
        lines = []
        for i, w in enumerate(reversed(hist[-10:]), 1):
            ts = w.get("time", 0)
            lines.append(f"#{i} — +{w.get('points',1)} pts • {w.get('reason','No reason')} • <t:{ts}:R>")
        emb = discord.Embed(title=f"Cautions for {member}", description="\n".join(lines), color=EMBED_OK)
        emb.add_field(name="Total Points", value=str(pts), inline=True)
        await _no_ping_send(ctx, embed=emb)

    # ---------- commands: settings ----------
    @commands.group(name="cautionset", invoke_without_command=True)
    @checks.admin_or_permissions(administrator=True)
    async def cautionset(self, ctx: commands.Context):
        """Settings panel for cautions."""
        g = await self.config.guild(ctx.guild).all()
        role = ctx.guild.get_role(int(g.get("mute_role", 0) or 0))
        chan = ctx.guild.get_channel(int(g.get("log_channel", 0) or 0))
        bf = g.get("berifine", {})
        th = g.get("thresholds", {})
        desc = (
            f"**Expiry Days:** {g.get('expiry_days',30)}\n"
            f"**Mute Role:** {role.mention if role else '—'}\n"
            f"**Log Channel:** {chan.mention if chan else '—'}\n"
            f"**Beri Fines:** {'On' if bf.get('enabled',True) else 'Off'} | per_point={bf.get('per_point',0)} | range={bf.get('min',0)}–{bf.get('max',0)}\n"
            f"**Beri Fine Thresholds:** {', '.join(f'{k}:{v}' for k,v in (bf.get('thresholds') or {}).items()) or '—'}\n"
            f"**Action Thresholds:** {', '.join(f'{k}:{v.get('kind','?')}' for k,v in (th or {}).items()) or '—'}"
        )
        await _no_ping_send(ctx, embed=discord.Embed(title="Caution Settings", description=desc, color=EMBED_OK))

    # expiry
    @cautionset.command(name="expiry")
    async def cautionset_expiry(self, ctx: commands.Context, days: int):
        days = max(1, int(days))
        await self.config.guild(ctx.guild).expiry_days.set(days)
        await _no_ping_send(ctx, embed=discord.Embed(description=f"Expiry set to **{days}** days.", color=EMBED_OK))

    # mute role
    @cautionset.command(name="mute")
    async def cautionset_mute(self, ctx: commands.Context, role: discord.Role):
        await self.config.guild(ctx.guild).mute_role.set(int(role.id))
        await _no_ping_send(ctx, embed=discord.Embed(description=f"Mute role set to {role.mention}.", color=EMBED_OK))

    # log channel
    @cautionset.group(name="log", invoke_without_command=True)
    async def cautionset_log(self, ctx: commands.Context):
        await _no_ping_send(ctx, embed=discord.Embed(description="Subcommands: `set <#channel>`, `disable`", color=EMBED_OK))

    @cautionset_log.command(name="set")
    async def cautionset_log_set(self, ctx: commands.Context, channel: discord.TextChannel):
        await self.config.guild(ctx.guild).log_channel.set(int(channel.id))
        await _no_ping_send(ctx, embed=discord.Embed(description=f"Log channel set to {channel.mention}.", color=EMBED_OK))

    @cautionset_log.command(name="disable")
    async def cautionset_log_disable(self, ctx: commands.Context):
        await self.config.guild(ctx.guild).log_channel.set(0)
        await _no_ping_send(ctx, embed=discord.Embed(description="Log channel disabled.", color=EMBED_OK))

    # thresholds (actions)
    @cautionset.group(name="thresholds", invoke_without_command=True)
    async def cautionset_thresholds(self, ctx: commands.Context):
        th = await self.config.guild(ctx.guild).thresholds()
        if not th:
            return await _no_ping_send(ctx, embed=discord.Embed(description="No thresholds set.", color=EMBED_WARN))
        lines = []
        for k, v in sorted(th.items(), key=lambda kv: int(kv[0])):
            kind = v.get("kind","?"); mins = v.get("minutes",0); rsn = v.get("reason","")
            extra = f" • {mins}m" if mins else ""
            lines.append(f"{k} pts → **{kind}**{extra}" + (f" — {rsn}" if rsn else ""))
        await _no_ping_send(ctx, embed=discord.Embed(title="Action Thresholds", description="\n".join(lines), color=EMBED_OK))

    @cautionset_thresholds.command(name="set")
    async def cautionset_thresholds_set(self, ctx: commands.Context, points: int, kind: str, minutes: Optional[int]=None, *, reason: Optional[str]=None):
        kind = kind.lower()
        if kind not in {"mute","timeout","kick","ban"}:
            return await _no_ping_send(ctx, embed=discord.Embed(description="Kind must be one of: mute, timeout, kick, ban.", color=EMBED_WARN))
        entry = {"kind": kind}
        if minutes is not None:
            entry["minutes"] = int(minutes)
        if reason:
            entry["reason"] = reason
        async with self.config.guild(ctx.guild).thresholds() as th:
            th[str(int(points))] = entry
        await _no_ping_send(ctx, embed=discord.Embed(description=f"Threshold **{points}** → **{kind}** set.", color=EMBED_OK))

    @cautionset_thresholds.command(name="remove")
    async def cautionset_thresholds_remove(self, ctx: commands.Context, points: int):
        async with self.config.guild(ctx.guild).thresholds() as th:
            if str(int(points)) in th:
                del th[str(int(points))]
                await _no_ping_send(ctx, embed=discord.Embed(description=f"Removed threshold **{points}**.", color=EMBED_OK))
            else:
                await _no_ping_send(ctx, embed=discord.Embed(description=f"No threshold at **{points}**.", color=EMBED_WARN))

    # berifine
    @cautionset.group(name="berifine", invoke_without_command=True)
    async def cautionset_berifine(self, ctx: commands.Context):
        g = await self.config.guild(ctx.guild).berifine()
        desc = f"**Enabled:** {'On' if g.get('enabled',True) else 'Off'}\n**Per Point:** {g.get('per_point',0)}\n**Range:** {g.get('min',0)}–{g.get('max',0)}\n**Thresholds:** {', '.join(f'{k}:{v}' for k,v in (g.get('thresholds') or {}).items()) or '—'}"
        await _no_ping_send(ctx, embed=discord.Embed(title="Beri Fine Settings", description=desc, color=EMBED_OK))

    @cautionset_berifine.command(name="toggle")
    async def cautionset_berifine_toggle(self, ctx: commands.Context, value: Optional[bool]=None):
        g = await self.config.guild(ctx.guild).berifine()
        val = (not g.get("enabled", True)) if value is None else bool(value)
        g["enabled"] = val
        await self.config.guild(ctx.guild).berifine.set(g)
        await _no_ping_send(ctx, embed=discord.Embed(description=f"Beri fines **{'enabled' if val else 'disabled'}**.", color=EMBED_OK))

    @cautionset_berifine.command(name="perpoint")
    async def cautionset_berifine_perpoint(self, ctx: commands.Context, amount: int):
        g = await self.config.guild(ctx.guild).berifine()
        g["per_point"] = max(0, int(amount))
        await self.config.guild(ctx.guild).berifine.set(g)
        await _no_ping_send(ctx, embed=discord.Embed(description=f"Per-point fine set to **{humanize_number(g['per_point'])}** Beri.", color=EMBED_OK))

    @cautionset_berifine.command(name="range")
    async def cautionset_berifine_range(self, ctx: commands.Context, min_fine: int, max_fine: int):
        mn, mx = int(min_fine), int(max_fine)
        if mn > mx: mn, mx = mx, mn
        g = await self.config.guild(ctx.guild).berifine()
        g["min"] = max(0, mn)
        g["max"] = max(0, mx)
        await self.config.guild(ctx.guild).berifine.set(g)
        await _no_ping_send(ctx, embed=discord.Embed(description=f"Fine range set to **{humanize_number(g['min'])}–{humanize_number(g['max'])}**.", color=EMBED_OK))

    @cautionset_berifine.command(name="threshold")
    async def cautionset_berifine_threshold(self, ctx: commands.Context, points: int, amount: int):
        g = await self.config.guild(ctx.guild).berifine()
        tf = dict(g.get("thresholds") or {})
        tf[str(int(points))] = max(0, int(amount))
        g["thresholds"] = tf
        await self.config.guild(ctx.guild).berifine.set(g)
        await _no_ping_send(ctx, embed=discord.Embed(description=f"Extra fine at **{points} pts** set to **{humanize_number(amount)}**.", color=EMBED_OK))

    @cautionset_berifine.command(name="clearthreshold")
    async def cautionset_berifine_clearthreshold(self, ctx: commands.Context, points: int):
        g = await self.config.guild(ctx.guild).berifine()
        tf = dict(g.get("thresholds") or {})
        if str(int(points)) in tf:
            del tf[str(int(points))]
            g["thresholds"] = tf
            await self.config.guild(ctx.guild).berifine.set(g)
            await _no_ping_send(ctx, embed=discord.Embed(description=f"Removed extra fine at **{points} pts**.", color=EMBED_OK))
        else:
            await _no_ping_send(ctx, embed=discord.Embed(description=f"No extra fine set at **{points} pts**.", color=EMBED_WARN))

async def setup(bot):
    await bot.add_cog(BeriCautions(bot))
