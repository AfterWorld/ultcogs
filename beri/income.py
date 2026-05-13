"""
Income system for the Beri economy cog.

Two income streams:
  1. Message income  — earn Beri once per cooldown window just by chatting.
  2. Role stipends   — certain roles pay an hourly or daily flat amount,
                       collected manually with [p]collect or auto-paid by a
                       background task.
"""

import asyncio
import datetime
import random
from typing import Optional

import discord
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import humanize_number


# ── Defaults ────────────────────────────────────────────────────────────────
DEFAULT_MSG_COOLDOWN = 60          # seconds between message income ticks
DEFAULT_MSG_MIN = 5                # min Beri per tick
DEFAULT_MSG_MAX = 25               # max Beri per tick


class Income(commands.Cog):
    """
    Passive income mixin.  Expects the parent class to expose:
      - self.config
      - self._modify_balance(guild, member, delta, reason=, actor=)
      - self._currency_fmt(guild)
    """

    # ── Per-guild income config stored under config.guild(guild).income ──────
    # Structure injected by Beri.__init__ via register_guild:
    #
    # "income": {
    #   "message_enabled": True,
    #   "message_cooldown": 60,
    #   "message_min": 5,
    #   "message_max": 25,
    #   "role_stipends": {},   # {role_id_str: {"amount": int, "interval": "hourly"|"daily"}}
    # }
    #
    # Per-member cooldown tracking: config.member(member).last_message_income  (ISO timestamp)
    # Per-member last-collect:      config.member(member).last_stipend_collect  {role_id_str: ISO}

    # ══════════════════════════════════════════════════════════════════════
    # Message income listener
    # ══════════════════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Award message income on a per-user cooldown."""
        if message.author.bot or not message.guild:
            return

        guild = message.guild
        member = message.author

        cfg = await self.config.guild(guild).income()
        if not cfg.get("message_enabled", True):
            return

        cooldown = cfg.get("message_cooldown", DEFAULT_MSG_COOLDOWN)
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        last_str = await self.config.member(member).last_message_income()
        if last_str:
            last = datetime.datetime.fromisoformat(last_str)
            if (now - last).total_seconds() < cooldown:
                return  # still on cooldown

        # Update timestamp first to prevent race conditions
        await self.config.member(member).last_message_income.set(now.isoformat())

        lo = cfg.get("message_min", DEFAULT_MSG_MIN)
        hi = cfg.get("message_max", DEFAULT_MSG_MAX)
        amount = random.randint(lo, hi)

        await self._modify_balance(
            guild, member, amount,
            reason="income:message",
            actor="System",
        )

    # ══════════════════════════════════════════════════════════════════════
    # Role stipend — manual collect
    # ══════════════════════════════════════════════════════════════════════

    @commands.command(name="collect", aliases=["payday"])
    @commands.guild_only()
    async def collect(self, ctx: commands.Context):
        """Collect your role stipend income."""
        cfg = await self.config.guild(ctx.guild).income()
        stipends: dict = cfg.get("role_stipends", {})

        if not stipends:
            return await ctx.send("❌ No role stipends are configured for this server.")

        name, icon = await self._currency_fmt(ctx.guild)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        last_collect: dict = await self.config.member(ctx.author).last_stipend_collect()

        total = 0
        breakdown = []

        for role in ctx.author.roles:
            rid = str(role.id)
            if rid not in stipends:
                continue

            stipend = stipends[rid]
            amount = stipend["amount"]
            interval = stipend.get("interval", "hourly")
            hours = 1 if interval == "hourly" else 24

            last_str = last_collect.get(rid)
            if last_str:
                last = datetime.datetime.fromisoformat(last_str)
                elapsed = (now - last).total_seconds() / 3600
                if elapsed < hours:
                    remaining = hours - elapsed
                    m, s = divmod(int(remaining * 3600), 60)
                    h, m = divmod(m, 60)
                    time_str = f"{h}h {m}m" if h else f"{m}m {s}s"
                    breakdown.append(f"{role.mention} — ⏳ {time_str} remaining")
                    continue

            last_collect[rid] = now.isoformat()
            total += amount
            breakdown.append(f"{role.mention} — **+{humanize_number(amount)}** {icon} ({interval})")

        if total > 0:
            await self.config.member(ctx.author).last_stipend_collect.set(last_collect)
            new_bal = await self._modify_balance(
                ctx.guild, ctx.author, total,
                reason="income:stipend:collect",
                actor="System",
            )
            embed = discord.Embed(
                title=f"{icon} Stipend Collected!",
                description="\n".join(breakdown),
                color=discord.Color.green(),
            )
            embed.add_field(name="Total Earned", value=f"**{humanize_number(total)}** {icon}", inline=True)
            embed.add_field(name="New Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        else:
            embed = discord.Embed(
                title=f"{icon} Nothing to Collect",
                description="\n".join(breakdown) if breakdown else "You don't have any stipend roles.",
                color=discord.Color.orange(),
            )

        embed.set_footer(text=ctx.author.display_name)
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════════════════════
    # Income admin commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.group(name="incomeset")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def incomeset(self, ctx: commands.Context):
        """Configure Beri income settings."""

    @incomeset.command(name="msgtoggle")
    async def incomeset_msgtoggle(self, ctx: commands.Context):
        """Toggle message-based income on or off."""
        async with self.config.guild(ctx.guild).income() as inc:
            inc["message_enabled"] = not inc.get("message_enabled", True)
            state = inc["message_enabled"]
        await ctx.send(f"✅ Message income is now **{'enabled' if state else 'disabled'}**.")

    @incomeset.command(name="msgcooldown")
    async def incomeset_msgcooldown(self, ctx: commands.Context, seconds: int):
        """Set the message income cooldown in seconds (minimum 10)."""
        seconds = max(10, seconds)
        async with self.config.guild(ctx.guild).income() as inc:
            inc["message_cooldown"] = seconds
        await ctx.send(f"✅ Message income cooldown set to **{seconds}s**.")

    @incomeset.command(name="msgamount")
    async def incomeset_msgamount(self, ctx: commands.Context, min_amt: int, max_amt: int):
        """Set the min and max Beri earned per message income tick."""
        if min_amt < 1 or max_amt < min_amt:
            return await ctx.send("❌ min must be ≥ 1 and max must be ≥ min.")
        async with self.config.guild(ctx.guild).income() as inc:
            inc["message_min"] = min_amt
            inc["message_max"] = max_amt
        name, icon = await self._currency_fmt(ctx.guild)
        await ctx.send(f"✅ Message income set to **{min_amt}–{max_amt}** {icon} per tick.")

    @incomeset.command(name="rolestipend")
    async def incomeset_rolestipend(
        self,
        ctx: commands.Context,
        role: discord.Role,
        amount: int,
        interval: str = "hourly",
    ):
        """
        Set a stipend for a role.

        `interval` must be `hourly` or `daily`.
        Set `amount` to 0 to remove the stipend.
        """
        interval = interval.lower()
        if interval not in ("hourly", "daily"):
            return await ctx.send("❌ Interval must be `hourly` or `daily`.")
        name, icon = await self._currency_fmt(ctx.guild)

        async with self.config.guild(ctx.guild).income() as inc:
            if "role_stipends" not in inc:
                inc["role_stipends"] = {}
            if amount <= 0:
                inc["role_stipends"].pop(str(role.id), None)
                return await ctx.send(f"✅ Removed stipend for {role.mention}.")
            inc["role_stipends"][str(role.id)] = {"amount": amount, "interval": interval}

        await ctx.send(
            f"✅ {role.mention} now earns **{humanize_number(amount)}** {icon} "
            f"per **{interval}** collect."
        )

    @incomeset.command(name="info")
    async def incomeset_info(self, ctx: commands.Context):
        """Show current income configuration."""
        cfg = await self.config.guild(ctx.guild).income()
        name, icon = await self._currency_fmt(ctx.guild)
        stipends = cfg.get("role_stipends", {})

        embed = discord.Embed(title="💰 Income Config", color=discord.Color.blurple())
        embed.add_field(
            name="Message Income",
            value=(
                f"**{'Enabled' if cfg.get('message_enabled', True) else 'Disabled'}**\n"
                f"Cooldown: {cfg.get('message_cooldown', DEFAULT_MSG_COOLDOWN)}s\n"
                f"Amount: {cfg.get('message_min', DEFAULT_MSG_MIN)}–"
                f"{cfg.get('message_max', DEFAULT_MSG_MAX)} {icon}"
            ),
            inline=False,
        )

        if stipends:
            lines = []
            for rid, data in stipends.items():
                role = ctx.guild.get_role(int(rid))
                rname = role.mention if role else f"<Deleted role {rid}>"
                lines.append(f"{rname} — **{humanize_number(data['amount'])}** {icon}/{data['interval']}")
            embed.add_field(name="Role Stipends", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="Role Stipends", value="None configured", inline=False)

        await ctx.send(embed=embed)
