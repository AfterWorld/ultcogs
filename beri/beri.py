"""
Beri Economy Cog for Red-DiscordBot
A full economy system using Beri as currency.
Runs alongside Red's built-in economy (separate balance).
"""

import asyncio
import random
import datetime
from typing import Optional

import discord
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, humanize_number

from .audit import AuditLog
from .games import Games
from .casino import Casino
from .work import Work
from .income import Income


class Beri(Income, Work, Casino, Games, commands.Cog):
    """
    🏴‍☠️ Beri Economy — the One Piece-themed currency system.
    Runs separately from Red's built-in economy.
    """

    __version__ = "2.0.0"
    __author__ = "UltPanda"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=0xBE71EC0, force_registration=True
        )

        # ── Default guild settings ─────────────────────────────────────────
        default_guild = {
            "starting_balance": 500,
            "currency_name": "Beri",
            "currency_icon": "🪙",
            "audit_channel": None,        # channel id for live audit feed
            "balances": {},               # {user_id_str: int}
            "income": {                   # message + role stipend config
                "message_enabled": True,
                "message_cooldown": 60,
                "message_min": 5,
                "message_max": 25,
                "role_stipends": {},      # {role_id_str: {"amount": int, "interval": "hourly"|"daily"}}
            },
        }

        # ── Default global settings ────────────────────────────────────────
        default_global = {
            "audit_log": [],              # list of audit entry dicts
        }

        # ── Default member settings ────────────────────────────────────────
        default_member = {
            "last_message_income": None,       # ISO timestamp
            "last_stipend_collect": {},         # {role_id_str: ISO timestamp}
        }

        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.config.register_member(**default_member)

        self.audit = AuditLog(bot, self.config)

    # ══════════════════════════════════════════════════════════════════════
    # Internal helpers
    # ══════════════════════════════════════════════════════════════════════

    async def _get_balance(self, guild: discord.Guild, user: discord.Member) -> int:
        balances = await self.config.guild(guild).balances()
        uid = str(user.id)
        if uid not in balances:
            starting = await self.config.guild(guild).starting_balance()
            balances[uid] = starting
            await self.config.guild(guild).balances.set(balances)
        return balances[uid]

    async def _set_balance(self, guild: discord.Guild, user: discord.Member, amount: int):
        balances = await self.config.guild(guild).balances()
        balances[str(user.id)] = max(0, amount)
        await self.config.guild(guild).balances.set(balances)

    async def _modify_balance(
        self,
        guild: discord.Guild,
        user: discord.Member,
        delta: int,
        *,
        reason: str,
        actor: discord.Member | str,
    ) -> int:
        """Add or subtract from a user's balance. Returns the new balance."""
        current = await self._get_balance(guild, user)
        new_bal = max(0, current + delta)
        await self._set_balance(guild, user, new_bal)
        await self.audit.log(
            guild=guild,
            target=user,
            actor=actor,
            delta=delta,
            new_balance=new_bal,
            reason=reason,
        )
        return new_bal

    async def _currency_fmt(self, guild: discord.Guild) -> tuple[str, str]:
        """Return (name, icon) for this guild's currency."""
        name = await self.config.guild(guild).currency_name()
        icon = await self.config.guild(guild).currency_icon()
        return name, icon

    # ══════════════════════════════════════════════════════════════════════
    # Wallet / Balance commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.group(name="beri", invoke_without_command=True)
    @commands.guild_only()
    async def beri_group(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Check your Beri balance (or another user's)."""
        target = member or ctx.author
        balance = await self._get_balance(ctx.guild, target)
        name, icon = await self._currency_fmt(ctx.guild)

        embed = discord.Embed(
            title=f"{icon} {name} Wallet",
            color=discord.Color.gold(),
        )
        embed.set_author(name=target.display_name, icon_url=target.display_avatar.url)
        embed.add_field(name="Balance", value=f"**{humanize_number(balance)}** {icon}", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # ── Admin wallet controls ──────────────────────────────────────────────

    @beri_group.command(name="give")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beri_give(
        self,
        ctx: commands.Context,
        member: discord.Member,
        amount: int,
        *,
        reason: str = "admin:give",
    ):
        """[Admin] Give Beri to a user."""
        if amount <= 0:
            return await ctx.send("Amount must be positive.")
        name, icon = await self._currency_fmt(ctx.guild)
        new_bal = await self._modify_balance(
            ctx.guild, member, amount, reason=reason, actor=ctx.author
        )
        await ctx.send(
            f"✅ Gave **{humanize_number(amount)}** {icon} to {member.mention}. "
            f"New balance: **{humanize_number(new_bal)}** {icon}."
        )

    @beri_group.command(name="take")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beri_take(
        self,
        ctx: commands.Context,
        member: discord.Member,
        amount: int,
        *,
        reason: str = "admin:take",
    ):
        """[Admin] Remove Beri from a user."""
        if amount <= 0:
            return await ctx.send("Amount must be positive.")
        name, icon = await self._currency_fmt(ctx.guild)
        new_bal = await self._modify_balance(
            ctx.guild, member, -amount, reason=reason, actor=ctx.author
        )
        await ctx.send(
            f"✅ Took **{humanize_number(amount)}** {icon} from {member.mention}. "
            f"New balance: **{humanize_number(new_bal)}** {icon}."
        )

    @beri_group.command(name="set")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beri_set(
        self,
        ctx: commands.Context,
        member: discord.Member,
        amount: int,
        *,
        reason: str = "admin:set",
    ):
        """[Admin] Set a user's Beri balance to an exact amount."""
        if amount < 0:
            return await ctx.send("Amount cannot be negative.")
        old_bal = await self._get_balance(ctx.guild, member)
        delta = amount - old_bal
        name, icon = await self._currency_fmt(ctx.guild)
        new_bal = await self._modify_balance(
            ctx.guild, member, delta, reason=reason, actor=ctx.author
        )
        await ctx.send(
            f"✅ Set {member.mention}'s balance to **{humanize_number(new_bal)}** {icon}."
        )

    # ── Leaderboard ────────────────────────────────────────────────────────

    @beri_group.command(name="top", aliases=["leaderboard", "lb"])
    @commands.guild_only()
    async def beri_top(self, ctx: commands.Context, page: int = 1):
        """Show the Beri leaderboard for this server."""
        balances = await self.config.guild(ctx.guild).balances()
        name, icon = await self._currency_fmt(ctx.guild)

        if not balances:
            return await ctx.send("No balances recorded yet.")

        sorted_bal = sorted(balances.items(), key=lambda x: x[1], reverse=True)
        per_page = 10
        total_pages = max(1, (len(sorted_bal) + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        chunk = sorted_bal[start : start + per_page]

        lines = []
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, (uid, bal) in enumerate(chunk, start=start + 1):
            member = ctx.guild.get_member(int(uid))
            display = member.display_name if member else f"<Unknown {uid}>"
            prefix = medals.get(i, f"`{i}.`")
            lines.append(f"{prefix} **{display}** — {humanize_number(bal)} {icon}")

        embed = discord.Embed(
            title=f"{icon} {name} Leaderboard",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"Page {page}/{total_pages} • {len(sorted_bal)} users total")
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════════════════════
    # Admin config
    # ══════════════════════════════════════════════════════════════════════

    @commands.group(name="beriset")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beriset(self, ctx: commands.Context):
        """Configure the Beri economy system."""

    @beriset.command(name="startingbal")
    async def beriset_startingbal(self, ctx: commands.Context, amount: int):
        """Set the starting balance for new users."""
        if amount < 0:
            return await ctx.send("Amount cannot be negative.")
        await self.config.guild(ctx.guild).starting_balance.set(amount)
        await ctx.send(f"✅ Starting balance set to **{humanize_number(amount)}**.")

    @beriset.command(name="currencyname")
    async def beriset_currencyname(self, ctx: commands.Context, *, name: str):
        """Set the currency name (default: Beri)."""
        await self.config.guild(ctx.guild).currency_name.set(name)
        await ctx.send(f"✅ Currency name set to **{name}**.")

    @beriset.command(name="currencyicon")
    async def beriset_currencyicon(self, ctx: commands.Context, icon: str):
        """Set the currency icon/emoji (default: 🪙)."""
        await self.config.guild(ctx.guild).currency_icon.set(icon)
        await ctx.send(f"✅ Currency icon set to {icon}.")

    @beriset.command(name="auditchannel")
    async def beriset_auditchannel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Set the channel for live audit log posts. Leave blank to disable."""
        if channel:
            await self.config.guild(ctx.guild).audit_channel.set(channel.id)
            await ctx.send(f"✅ Audit log will post to {channel.mention}.")
        else:
            await self.config.guild(ctx.guild).audit_channel.set(None)
            await ctx.send("✅ Audit log channel disabled.")

    @beriset.command(name="info")
    async def beriset_info(self, ctx: commands.Context):
        """Show current Beri configuration for this server."""
        start = await self.config.guild(ctx.guild).starting_balance()
        name = await self.config.guild(ctx.guild).currency_name()
        icon = await self.config.guild(ctx.guild).currency_icon()
        audit_ch_id = await self.config.guild(ctx.guild).audit_channel()
        audit_ch = ctx.guild.get_channel(audit_ch_id) if audit_ch_id else None
        inc = await self.config.guild(ctx.guild).income()

        embed = discord.Embed(title="⚙️ Beri Config", color=discord.Color.blurple())
        embed.add_field(name="Currency", value=f"{icon} {name}", inline=True)
        embed.add_field(name="Starting Balance", value=humanize_number(start), inline=True)
        embed.add_field(
            name="Audit Channel",
            value=audit_ch.mention if audit_ch else "Not set",
            inline=True,
        )
        embed.add_field(
            name="Message Income",
            value=(
                f"{'✅' if inc.get('message_enabled', True) else '❌'} "
                f"{inc.get('message_min', 5)}–{inc.get('message_max', 25)} {icon} "
                f"/ {inc.get('message_cooldown', 60)}s"
            ),
            inline=True,
        )
        stipends = inc.get("role_stipends", {})
        embed.add_field(
            name="Role Stipends",
            value=f"{len(stipends)} configured" if stipends else "None",
            inline=True,
        )
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════════════════════
    # Audit log commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.group(name="beriaudit", aliases=["baudit"])
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beriaudit(self, ctx: commands.Context):
        """View the Beri audit log."""

    @beriaudit.command(name="recent")
    async def beriaudit_recent(self, ctx: commands.Context, limit: int = 10):
        """Show the most recent transactions for this server."""
        limit = max(1, min(limit, 25))
        entries = await self.audit.get_entries(guild_id=ctx.guild.id, limit=limit)

        if not entries:
            return await ctx.send("No audit entries found.")

        name, icon = await self._currency_fmt(ctx.guild)
        lines = []
        for e in reversed(entries):
            sign = "+" if e["delta"] >= 0 else ""
            ts = e["ts"][:16].replace("T", " ")
            lines.append(
                f"`{ts}` **{e['target_name']}** — "
                f"`{sign}{humanize_number(e['delta'])}` {icon} "
                f"by **{e['actor_name']}** | `{e['reason']}`"
            )

        embed = discord.Embed(
            title=f"📋 {name} Audit Log — Last {limit}",
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed)

    @beriaudit.command(name="user")
    async def beriaudit_user(self, ctx: commands.Context, member: discord.Member, limit: int = 10):
        """Show recent transactions for a specific user."""
        limit = max(1, min(limit, 25))
        entries = await self.audit.get_entries(
            guild_id=ctx.guild.id, user_id=member.id, limit=limit
        )

        if not entries:
            return await ctx.send(f"No audit entries found for {member.mention}.")

        name, icon = await self._currency_fmt(ctx.guild)
        lines = []
        for e in reversed(entries):
            sign = "+" if e["delta"] >= 0 else ""
            ts = e["ts"][:16].replace("T", " ")
            lines.append(
                f"`{ts}` `{sign}{humanize_number(e['delta'])}` {icon} "
                f"by **{e['actor_name']}** | `{e['reason']}`"
            )

        embed = discord.Embed(
            title=f"📋 {name} Audit — {member.display_name} (last {limit})",
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @beriaudit.command(name="clear")
    @checks.is_owner()
    async def beriaudit_clear(self, ctx: commands.Context):
        """[Bot Owner] Wipe the entire audit log."""
        await self.config.audit_log.set([])
        await ctx.send("✅ Audit log cleared.")
