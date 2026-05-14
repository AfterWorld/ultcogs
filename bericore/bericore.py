"""
BeriCore — Central balance and stats engine for the Beri economy system.
All balance reads/writes for the Beri cog route through this cog.

Provides:
  - get_beri(member)                          → int
  - add_beri(member, delta, *, reason, ...)   → int  (new balance)
  - transfer_beri(src, dst, amount, *, ...)   → (bool, str)
  - get_user_stats(member)                    → dict

Balances are stored per-guild-member so the same user can have independent
balances in different servers.
"""

import datetime
from typing import Any, Optional, Union

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_number


class BeriCore(commands.Cog):
    """
    🏦 BeriCore — Low-level balance storage and stats for the Beri economy.
    Load this before the Beri cog. Do not unload while Beri is active.
    """

    __version__ = "1.0.0"
    __author__ = "UltPanda"

    # Unique identifier — must never collide with Beri's own config id
    _CONFIG_ID = 0xBE710C0E

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=self._CONFIG_ID, force_registration=True
        )

        # Per-member defaults (scoped to guild)
        default_member = {
            "balance": 0,
            # Rolling daily stats — reset when the date changes
            "earned_today": 0,
            "earned_today_date": None,   # ISO date string "YYYY-MM-DD"
            # Lifetime totals (never reset)
            "lifetime_earned": 0,
            "lifetime_spent": 0,
            # Transaction history (last N entries, kept trimmed)
            "history": [],               # list of {ts, delta, reason, actor}
        }

        # Per-guild defaults (reserved for future global settings)
        default_guild = {
            "history_limit": 50,         # max history entries kept per member
        }

        self.config.register_member(**default_member)
        self.config.register_guild(**default_guild)

    # ══════════════════════════════════════════════════════════════════════
    # Internal helpers
    # ══════════════════════════════════════════════════════════════════════

    def _today(self) -> str:
        return datetime.date.today().isoformat()

    async def _reset_daily_if_needed(self, member: discord.Member):
        """Reset earned_today if the stored date is in the past."""
        today = self._today()
        stored_date = await self.config.member(member).earned_today_date()
        if stored_date != today:
            await self.config.member(member).earned_today.set(0)
            await self.config.member(member).earned_today_date.set(today)

    async def _append_history(
        self,
        member: discord.Member,
        *,
        delta: int,
        new_balance: int,
        reason: str,
        actor: Optional[Union[discord.Member, str]] = None,
        metadata: Optional[dict] = None,
    ):
        """Append a transaction to the member's history, trimming if needed."""
        limit = await self.config.guild(member.guild).history_limit()
        actor_name = (
            actor.display_name
            if isinstance(actor, discord.Member)
            else str(actor or "system")
        )
        entry: dict[str, Any] = {
            "ts": int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp()),
            "delta": delta,
            "new_balance": new_balance,
            "reason": reason,
            "actor_name": actor_name,
        }
        if metadata:
            entry["metadata"] = metadata

        async with self.config.member(member).history() as hist:
            hist.append(entry)
            if len(hist) > limit:
                del hist[: len(hist) - limit]

    # ══════════════════════════════════════════════════════════════════════
    # Public API — called by the Beri cog
    # ══════════════════════════════════════════════════════════════════════

    async def get_beri(self, member: discord.Member) -> int:
        """Return the current Beri balance for a guild member."""
        return await self.config.member(member).balance()

    async def add_beri(
        self,
        member: discord.Member,
        delta: int,
        *,
        reason: str = "unknown",
        actor: Optional[Union[discord.Member, str]] = None,
        metadata: Optional[dict] = None,
        bypass_cap: bool = False,   # accepted for compatibility; BeriCore has no cap
    ) -> int:
        """
        Add (or subtract) ``delta`` Beri from ``member``.

        Balance is clamped to a minimum of 0 — members can never go negative.
        Returns the new balance.
        """
        await self._reset_daily_if_needed(member)

        async with self.config.member(member).all() as data:
            current = data["balance"]
            new_balance = max(0, current + delta)
            actual_delta = new_balance - current  # may differ if clamped to 0

            data["balance"] = new_balance

            # Stat tracking
            if actual_delta > 0:
                data["earned_today"] = data.get("earned_today", 0) + actual_delta
                data["lifetime_earned"] = data.get("lifetime_earned", 0) + actual_delta
            elif actual_delta < 0:
                data["lifetime_spent"] = data.get("lifetime_spent", 0) + abs(actual_delta)

        await self._append_history(
            member,
            delta=actual_delta,
            new_balance=new_balance,
            reason=reason,
            actor=actor,
            metadata=metadata,
        )

        return new_balance

    async def transfer_beri(
        self,
        source: discord.Member,
        destination: discord.Member,
        amount: int,
        *,
        reason: str = "transfer",
        tax_rate: float = 0.0,
    ) -> tuple[bool, str]:
        """
        Move Beri from ``source`` to ``destination`` with an optional tax.

        The tax is deducted from the sender's perspective — the sender loses
        ``amount``, and the receiver gains ``int(amount * (1 - tax_rate))``.

        Returns ``(True, "")`` on success, ``(False, error_message)`` on failure.
        """
        if amount <= 0:
            return False, "Amount must be positive."

        src_balance = await self.get_beri(source)
        if amount > src_balance:
            return False, (
                f"Insufficient funds. You have **{humanize_number(src_balance)}** Beri."
            )

        received = int(amount * (1.0 - tax_rate))

        await self.add_beri(
            source,
            -amount,
            reason=f"{reason}:sent",
            actor=source,
            metadata={"to": destination.id, "amount": amount, "tax_rate": tax_rate},
        )
        await self.add_beri(
            destination,
            received,
            reason=f"{reason}:received",
            actor=source,
            metadata={"from": source.id, "amount": amount, "tax_rate": tax_rate},
        )

        return True, ""

    async def get_user_stats(self, member: discord.Member) -> dict:
        """
        Return a stats dict for the given member:
          {
            "balance":          int,
            "earned_today":     int,
            "lifetime_earned":  int,
            "lifetime_spent":   int,
          }
        """
        await self._reset_daily_if_needed(member)
        data = await self.config.member(member).all()
        return {
            "balance": data.get("balance", 0),
            "earned_today": data.get("earned_today", 0),
            "lifetime_earned": data.get("lifetime_earned", 0),
            "lifetime_spent": data.get("lifetime_spent", 0),
        }

    # ══════════════════════════════════════════════════════════════════════
    # Admin / owner commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.group(name="bericoreinfo", aliases=["bcinfo"])
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def bericoreinfo(self, ctx: commands.Context):
        """BeriCore status and diagnostics."""

    @bericoreinfo.command(name="status")
    async def bcinfo_status(self, ctx: commands.Context):
        """Show BeriCore status and version."""
        embed = discord.Embed(
            title="🏦 BeriCore Status",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Version", value=self.__version__, inline=True)
        embed.add_field(name="Status", value="✅ Loaded", inline=True)
        embed.add_field(
            name="Beri Cog",
            value="✅ Connected" if ctx.bot.get_cog("Beri") else "❌ Not loaded",
            inline=True,
        )
        limit = await self.config.guild(ctx.guild).history_limit()
        embed.add_field(name="History Limit", value=f"{limit} entries/member", inline=True)
        await ctx.send(embed=embed)

    @bericoreinfo.command(name="member")
    async def bcinfo_member(self, ctx: commands.Context, member: discord.Member):
        """Show raw BeriCore data for a specific member."""
        stats = await self.get_user_stats(member)
        history = await self.config.member(member).history()

        embed = discord.Embed(
            title=f"🏦 BeriCore — {member.display_name}",
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="Balance", value=humanize_number(stats["balance"]), inline=True
        )
        embed.add_field(
            name="Earned Today", value=humanize_number(stats["earned_today"]), inline=True
        )
        embed.add_field(
            name="Lifetime Earned",
            value=humanize_number(stats["lifetime_earned"]),
            inline=True,
        )
        embed.add_field(
            name="Lifetime Spent",
            value=humanize_number(stats["lifetime_spent"]),
            inline=True,
        )
        embed.add_field(
            name="History Entries", value=str(len(history)), inline=True
        )

        if history:
            recent = history[-5:]
            lines = []
            for e in reversed(recent):
                sign = "+" if e["delta"] >= 0 else ""
                lines.append(
                    f"`{sign}{e['delta']}` — {e['reason']} "
                    f"<t:{e['ts']}:R>"
                )
            embed.add_field(name="Recent Transactions", value="\n".join(lines), inline=False)

        await ctx.send(embed=embed)

    @bericoreinfo.command(name="setlimit")
    @checks.admin_or_permissions(manage_guild=True)
    async def bcinfo_setlimit(self, ctx: commands.Context, limit: int):
        """Set the per-member transaction history limit (default: 50)."""
        limit = max(10, min(limit, 500))
        await self.config.guild(ctx.guild).history_limit.set(limit)
        await ctx.send(f"✅ History limit set to **{limit}** entries per member.")

    # ══════════════════════════════════════════════════════════════════════
    # Bot owner commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.command(name="bericorewipe")
    @commands.is_owner()
    @commands.guild_only()
    async def bericorewipe(self, ctx: commands.Context, member: discord.Member):
        """[Owner] Completely wipe a member's BeriCore data in this guild."""
        await self.config.member(member).clear()
        await ctx.send(f"✅ Wiped all BeriCore data for {member.mention} in this server.")

    @commands.command(name="bericorewipeguild")
    @commands.is_owner()
    @commands.guild_only()
    async def bericorewipeguild(self, ctx: commands.Context):
        """[Owner] Wipe ALL member data for this guild. Irreversible."""
        await ctx.send(
            "⚠️ This will permanently delete ALL Beri balances and stats for this guild. "
            "Type `CONFIRM` to proceed."
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await ctx.bot.wait_for("message", timeout=30.0, check=check)
        except Exception:
            return await ctx.send("❌ Timed out. Wipe cancelled.")

        if msg.content.strip() != "CONFIRM":
            return await ctx.send("❌ Wipe cancelled.")

        await self.config.clear_all_members(ctx.guild)
        await ctx.send(f"✅ All BeriCore member data wiped for **{ctx.guild.name}**.")
