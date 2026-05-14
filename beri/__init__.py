"""
BeriCog — Economy cog that bridges to a friend's BeriCore cog.

All balance mutations go through _modify_balance(), which always sets
bypass_cap=True so the daily cap is never a concern.

Mixins loaded:
  - casino.py  → blackjack, roulette, dice, horses, video poker
  - games.py   → coinflip, slots
  - work.py    → work, crime, hack, slut, rob
  - income.py  → on_message income, collect (stipends), incomeset admin
  - audit.py   → local audit log (supplemental to BeriCore's own audit)
"""

from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_number
import discord
from typing import Optional, Tuple

from .casino import Casino
from .games import Games
from .work import Work
from .income import Income
from .audit import AuditLog


class BeriCog(Casino, Games, Work, Income, commands.Cog):
    """
    One Piece-themed Beri economy powered by BeriCore.
    Provides games, gambling, activity commands, and passive income.
    """

    __version__ = "1.0.0"

    # ── Default guild config ───────────────────────────────────────────────
    DEFAULT_GUILD = {
        "currency_name": "Beri",
        "currency_icon": "🪙",
        "audit_channel": None,
        "income": {
            "message_enabled": True,
            "message_cooldown": 60,
            "message_min": 5,
            "message_max": 25,
            "role_stipends": {},
        },
    }

    DEFAULT_MEMBER = {
        "last_message_income": None,
        "last_stipend_collect": {},
    }

    DEFAULT_GLOBAL = {
        "audit_log": [],
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=8675309_420_1337,  # unique enough
            force_registration=True,
        )
        self.config.register_guild(**self.DEFAULT_GUILD)
        self.config.register_member(**self.DEFAULT_MEMBER)
        self.config.register_global(**self.DEFAULT_GLOBAL)

        self._audit = AuditLog(bot, self.config)

    # ══════════════════════════════════════════════════════════════════════
    # BeriCore bridge — ALL balance ops flow through here
    # ══════════════════════════════════════════════════════════════════════

    def _bericore(self):
        """Return the BeriCore cog instance, or None if not loaded."""
        return self.bot.get_cog("BeriCore")


    async def _get_balance(self, guild: discord.Guild, member: discord.Member) -> int:
        """Fetch current Beri balance for a member."""
        core = self._bericore()
        if not core:
            raise RuntimeError("BeriCore is not loaded. Ask an admin to load it.")
        return await core.get_beri(member)

    async def _modify_balance(
        self,
        guild: discord.Guild,
        member: discord.Member,
        delta: int,
        *,
        reason: str = "bericog:unknown",
        actor=None,
        bypass_cap: bool = True,   # always True — we don't use the cap
        metadata: Optional[dict] = None,
    ) -> int:
        """
        Add (or subtract) Beri via BeriCore.
        bypass_cap is hardcoded True so the daily cap is never enforced.
        Returns the new balance.
        """
        core = self._bericore()
        if not core:
            raise RuntimeError("BeriCore is not loaded. Ask an admin to load it.")

        new_balance = await core.add_beri(
            member, delta,
            reason=reason,
            actor=actor,
            bypass_cap=True,
            metadata=metadata,
        )

        # Mirror to local audit log as well
        try:
            await self._audit.log(
                guild=guild,
                target=member,
                actor=actor or "System",
                delta=delta,
                new_balance=new_balance,
                reason=reason,
            )
        except Exception:
            pass  # Never let audit failure block a transaction

        return new_balance

    async def _safe_modify(
        self,
        ctx: commands.Context,
        guild: discord.Guild,
        member: discord.Member,
        delta: int,
        *,
        reason: str = "bericog:unknown",
        actor=None,
        bypass_cap: bool = True,
        metadata: Optional[dict] = None,
    ) -> Optional[int]:
        """
        Wrapper around _modify_balance that handles errors gracefully by
        sending a user-facing message and returning None on failure.
        Use this inside command handlers.
        """
        try:
            return await self._modify_balance(
                guild, member, delta,
                reason=reason, actor=actor,
                bypass_cap=True,
                metadata=metadata,
            )
        except RuntimeError as e:
            await ctx.send(f"❌ {e}")
            return None

    async def _currency_fmt(self, guild: discord.Guild) -> Tuple[str, str]:
        """Return (currency_name, currency_icon) for this guild."""
        name = await self.config.guild(guild).currency_name()
        icon = await self.config.guild(guild).currency_icon()
        return name, icon

    # ══════════════════════════════════════════════════════════════════════
    # Core commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.command(name="balance", aliases=["bal", "beri", "wallet"])
    @commands.guild_only()
    async def balance(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Check your (or another user's) Beri balance."""
        target = member or ctx.author
        name, icon = await self._currency_fmt(ctx.guild)

        try:
            core = self._bericore()
            if not core:
                return await ctx.send("❌ BeriCore is not loaded.")
            balance = await self._get_balance(ctx.guild, target)
            stats = await core.get_user_stats(target)
        except RuntimeError as e:
            return await ctx.send(f"❌ {e}")

        embed = discord.Embed(
            title=f"{icon} {target.display_name}'s Wallet",
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="Balance",
            value=f"**{humanize_number(balance)}** {icon}",
            inline=False,
        )
        if stats:
            embed.add_field(name="Earned Today", value=humanize_number(stats.get("earned_today", 0)), inline=True)
            embed.add_field(name="Lifetime Earned", value=humanize_number(stats.get("lifetime_earned", 0)), inline=True)
            embed.add_field(name="Lifetime Spent", value=humanize_number(stats.get("lifetime_spent", 0)), inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="give", aliases=["pay", "transfer"])
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def give(self, ctx: commands.Context, target: discord.Member, amount: int):
        """Transfer Beri to another user (no tax)."""
        name, icon = await self._currency_fmt(ctx.guild)

        if target == ctx.author:
            return await ctx.send("❌ You can't send Beri to yourself.")
        if target.bot:
            return await ctx.send("❌ Bots don't have wallets.")
        if amount <= 0:
            return await ctx.send("❌ Amount must be positive.")

        try:
            balance = await self._get_balance(ctx.guild, ctx.author)
        except RuntimeError as e:
            return await ctx.send(f"❌ {e}")

        if balance < amount:
            return await ctx.send(f"❌ You only have **{humanize_number(balance)}** {icon}.")

        core = self._bericore()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        success, msg = await core.transfer_beri(
            ctx.author, target, amount,
            reason="transfer:give",
            tax_rate=0.0,
        )
        if not success:
            return await ctx.send(f"❌ Transfer failed: {msg}")

        embed = discord.Embed(
            title=f"{icon} Transfer Complete",
            description=f"{ctx.author.mention} sent **{humanize_number(amount)}** {icon} to {target.mention}.",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    @commands.guild_only()
    async def leaderboard(self, ctx: commands.Context):
        """Show the Beri leaderboard (top 10 in the server)."""
        name, icon = await self._currency_fmt(ctx.guild)
        core = self._bericore()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        await ctx.send(f"📊 Use the BeriCore leaderboard command for rankings. (`{ctx.prefix}beri top` or similar)")

    # ══════════════════════════════════════════════════════════════════════
    # Admin commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.group(name="berisettings", aliases=["bericfg"])
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def berisettings(self, ctx: commands.Context):
        """Admin settings for BeriCog."""

    @berisettings.command(name="currencyname")
    async def cfg_currencyname(self, ctx: commands.Context, *, name: str):
        """Set the currency name (default: Beri)."""
        await self.config.guild(ctx.guild).currency_name.set(name)
        await ctx.send(f"✅ Currency name set to **{name}**.")

    @berisettings.command(name="currencyicon")
    async def cfg_currencyicon(self, ctx: commands.Context, icon: str):
        """Set the currency icon/emoji (default: 🪙)."""
        await self.config.guild(ctx.guild).currency_icon.set(icon)
        await ctx.send(f"✅ Currency icon set to {icon}.")

    @berisettings.command(name="auditchannel")
    async def cfg_auditchannel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Set (or clear) the channel where transactions are logged."""
        await self.config.guild(ctx.guild).audit_channel.set(channel.id if channel else None)
        if channel:
            await ctx.send(f"✅ Audit log will post to {channel.mention}.")
        else:
            await ctx.send("✅ Audit channel cleared.")

    @berisettings.command(name="award")
    async def cfg_award(self, ctx: commands.Context, member: discord.Member, amount: int, *, reason: str = "admin award"):
        """Award Beri to a user (bypasses cap)."""
        if amount <= 0:
            return await ctx.send("❌ Amount must be positive.")
        new_bal = await self._safe_modify(
            ctx, ctx.guild, member, amount,
            reason=f"admin:award:{reason}",
            actor=ctx.author,
        )
        if new_bal is not None:
            name, icon = await self._currency_fmt(ctx.guild)
            await ctx.send(f"✅ Awarded **{humanize_number(amount)}** {icon} to {member.mention}. New balance: {humanize_number(new_bal)} {icon}")

    @berisettings.command(name="deduct")
    async def cfg_deduct(self, ctx: commands.Context, member: discord.Member, amount: int, *, reason: str = "admin deduction"):
        """Deduct Beri from a user."""
        if amount <= 0:
            return await ctx.send("❌ Amount must be positive.")
        new_bal = await self._safe_modify(
            ctx, ctx.guild, member, -amount,
            reason=f"admin:deduct:{reason}",
            actor=ctx.author,
        )
        if new_bal is not None:
            name, icon = await self._currency_fmt(ctx.guild)
            await ctx.send(f"✅ Deducted **{humanize_number(amount)}** {icon} from {member.mention}. New balance: {humanize_number(new_bal)} {icon}")

    @berisettings.command(name="info")
    async def cfg_info(self, ctx: commands.Context):
        """Show current BeriCog configuration."""
        name, icon = await self._currency_fmt(ctx.guild)
        core = self._bericore()
        audit_ch_id = await self.config.guild(ctx.guild).audit_channel()
        audit_ch = ctx.guild.get_channel(audit_ch_id) if audit_ch_id else None

        embed = discord.Embed(title="⚙️ BeriCog Config", color=discord.Color.blurple())
        embed.add_field(name="Currency", value=f"{icon} {name}", inline=True)
        embed.add_field(name="BeriCore", value="✅ Loaded" if core else "❌ Not loaded", inline=True)
        embed.add_field(name="Daily Cap", value="🚫 Disabled (bypass_cap=True always)", inline=True)
        embed.add_field(name="Audit Channel", value=audit_ch.mention if audit_ch else "Not set", inline=True)
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════════════════════
    # Audit log viewer
    # ══════════════════════════════════════════════════════════════════════

    @commands.command(name="auditlog", aliases=["txlog"])
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def auditlog(self, ctx: commands.Context, member: Optional[discord.Member] = None, limit: int = 10):
        """View recent Beri transactions. Optionally filter by user."""
        limit = min(max(1, limit), 25)
        entries = await self._audit.get_entries(
            guild_id=ctx.guild.id,
            user_id=member.id if member else None,
            limit=limit,
        )

        if not entries:
            return await ctx.send("📭 No audit entries found.")

        name, icon = await self._currency_fmt(ctx.guild)
        lines = []
        for e in reversed(entries):
            sign = "+" if e["delta"] >= 0 else ""
            lines.append(
                f"`{e['ts'][:16]}` <@{e['target_id']}> "
                f"**{sign}{humanize_number(e['delta'])}** {icon} "
                f"— `{e['reason']}`"
            )

        embed = discord.Embed(
            title=f"{icon} Recent Transactions" + (f" — {member.display_name}" if member else ""),
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed)


async def setup(bot: Red):
    await bot.add_cog(BeriCog(bot))
