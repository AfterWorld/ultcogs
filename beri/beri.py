"""
Beri Economy Cog for Red-DiscordBot
Balance reads/writes route through BeriCore API.
This cog adds: games, casino, work/crime, passive income, and audit log.
"""

import asyncio
import random
import datetime
from typing import Optional

import discord
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_number

from .audit import AuditLog
from .bridge import BeriCoreBridge
from .games import Games
from .casino import Casino
from .work import Work
from .income import Income


class Beri(BeriCoreBridge, Income, Work, Casino, Games, commands.Cog):
    """
    🏴‍☠️ Beri Economy — the One Piece-themed currency system.
    Balance is managed by BeriCore; this cog adds games, income, and audit.
    """

    __version__ = "2.1.0"
    __author__ = "UltPanda"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=0xBE71EC0, force_registration=True
        )

        default_guild = {
            "currency_name": "Beri",
            "currency_icon": "🪙",
            "audit_channel": None,
            "lb_cache": {},               # {user_id_str: int} mirrors BeriCore balances
            "income": {
                "message_enabled": True,
                "message_cooldown": 60,
                "message_min": 5,
                "message_max": 25,
                "role_stipends": {},
            },
        }

        default_global = {
            "audit_log": [],
        }

        default_member = {
            "last_message_income": None,
            "last_stipend_collect": {},
        }

        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.config.register_member(**default_member)

        self.audit = AuditLog(bot, self.config)

    # ══════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════

    async def _currency_fmt(self, guild: discord.Guild) -> tuple[str, str]:
        name = await self.config.guild(guild).currency_name()
        icon = await self.config.guild(guild).currency_icon()
        return name, icon

    # ══════════════════════════════════════════════════════════════════════
    # Wallet commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.group(name="beri", invoke_without_command=True)
    @commands.guild_only()
    async def beri_group(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Check your Beri balance (or another user's)."""
        target = member or ctx.author
        name, icon = await self._currency_fmt(ctx.guild)

        try:
            balance = await self._get_balance(ctx.guild, target)
            stats = await self._get_user_stats(target)
        except RuntimeError as e:
            return await ctx.send(f"❌ {e}")

        embed = discord.Embed(title=f"{icon} {name} Wallet", color=discord.Color.gold())
        embed.set_author(name=target.display_name, icon_url=target.display_avatar.url)
        embed.add_field(name="Balance", value=f"**{humanize_number(balance)}** {icon}", inline=True)
        embed.add_field(
            name="Earned Today",
            value=f"{humanize_number(stats.get('earned_today', 0))} {icon}",
            inline=True,
        )
        embed.add_field(
            name="Lifetime Earned",
            value=f"{humanize_number(stats.get('lifetime_earned', 0))} {icon}",
            inline=True,
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @beri_group.command(name="give")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beri_give(self, ctx, member: discord.Member, amount: int, *, reason: str = "admin:give"):
        """[Admin] Give Beri to a user."""
        if amount <= 0:
            return await ctx.send("Amount must be positive.")
        name, icon = await self._currency_fmt(ctx.guild)
        new_bal = await self._safe_modify(ctx, ctx.guild, member, amount, reason=reason, actor=ctx.author, bypass_cap=True)
        if new_bal is None:
            return
        await ctx.send(f"✅ Gave **{humanize_number(amount)}** {icon} to {member.mention}. New balance: **{humanize_number(new_bal)}** {icon}.")

    @beri_group.command(name="take")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beri_take(self, ctx, member: discord.Member, amount: int, *, reason: str = "admin:take"):
        """[Admin] Remove Beri from a user."""
        if amount <= 0:
            return await ctx.send("Amount must be positive.")
        name, icon = await self._currency_fmt(ctx.guild)
        new_bal = await self._safe_modify(ctx, ctx.guild, member, -amount, reason=reason, actor=ctx.author, bypass_cap=True)
        if new_bal is None:
            return
        await ctx.send(f"✅ Took **{humanize_number(amount)}** {icon} from {member.mention}. New balance: **{humanize_number(new_bal)}** {icon}.")

    @beri_group.command(name="set")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beri_set(self, ctx, member: discord.Member, amount: int, *, reason: str = "admin:set"):
        """[Admin] Set a user's Beri balance to an exact amount."""
        if amount < 0:
            return await ctx.send("Amount cannot be negative.")
        name, icon = await self._currency_fmt(ctx.guild)
        try:
            old_bal = await self._get_balance(ctx.guild, member)
            delta = amount - old_bal
            new_bal = await self._modify_balance(ctx.guild, member, delta, reason=reason, actor=ctx.author, bypass_cap=True)
        except RuntimeError as e:
            return await ctx.send(f"❌ {e}")
        await ctx.send(f"✅ Set {member.mention}'s balance to **{humanize_number(new_bal)}** {icon}.")

    @beri_group.command(name="transfer", aliases=["pay", "send"])
    @commands.guild_only()
    async def beri_transfer(self, ctx, member: discord.Member, amount: int):
        """Send Beri to another user (5% tax)."""
        if member == ctx.author:
            return await ctx.send("❌ You can't send Beri to yourself.")
        if member.bot:
            return await ctx.send("❌ Bots don't accept Beri.")
        if amount <= 0:
            return await ctx.send("❌ Amount must be positive.")
        name, icon = await self._currency_fmt(ctx.guild)
        try:
            success, msg = await self._transfer_balance(ctx.guild, ctx.author, member, amount, reason="user:transfer", tax_rate=0.05)
        except RuntimeError as e:
            return await ctx.send(f"❌ {e}")
        if success:
            received = int(amount * 0.95)
            await ctx.send(f"✅ Sent **{humanize_number(amount)}** {icon} to {member.mention}. They received **{humanize_number(received)}** {icon} after 5% tax.")
        else:
            await ctx.send(f"❌ {msg}")

    @beri_group.command(name="top", aliases=["leaderboard", "lb"])
    @commands.guild_only()
    async def beri_top(self, ctx: commands.Context, page: int = 1):
        """Show the Beri leaderboard for this server."""
        cache = await self._get_cache(ctx.guild)
        name, icon = await self._currency_fmt(ctx.guild)

        if not cache:
            return await ctx.send("No balances recorded yet.")

        sorted_bal = sorted(cache.items(), key=lambda x: x[1], reverse=True)
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
        embed.set_footer(text=f"Page {page}/{total_pages} • {len(sorted_bal)} users • Cached — use {ctx.prefix}beri for live balance")
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════════════════════
    # Admin config
    # ══════════════════════════════════════════════════════════════════════

    @commands.group(name="beriset")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beriset(self, ctx: commands.Context):
        """Configure the Beri economy system."""

    @beriset.command(name="currencyname")
    async def beriset_currencyname(self, ctx, *, name: str):
        """Set the currency name (default: Beri)."""
        await self.config.guild(ctx.guild).currency_name.set(name)
        await ctx.send(f"✅ Currency name set to **{name}**.")

    @beriset.command(name="currencyicon")
    async def beriset_currencyicon(self, ctx, icon: str):
        """Set the currency icon/emoji (default: 🪙)."""
        await self.config.guild(ctx.guild).currency_icon.set(icon)
        await ctx.send(f"✅ Currency icon set to {icon}.")

    @beriset.command(name="auditchannel")
    async def beriset_auditchannel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Set the channel for live audit log posts. Leave blank to disable."""
        if channel:
            await self.config.guild(ctx.guild).audit_channel.set(channel.id)
            await ctx.send(f"✅ Audit log will post to {channel.mention}.")
        else:
            await self.config.guild(ctx.guild).audit_channel.set(None)
            await ctx.send("✅ Audit log channel disabled.")

    @beriset.command(name="synccache")
    async def beriset_synccache(self, ctx: commands.Context):
        """Re-sync leaderboard cache from BeriCore. Run if LB looks stale."""
        core = self._core()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")
        cache = await self._get_cache(ctx.guild)
        if not cache:
            return await ctx.send("Cache is empty — nothing to sync.")
        msg = await ctx.send(f"⏳ Syncing {len(cache)} entries...")
        updated = 0
        for uid_str in list(cache.keys()):
            member = ctx.guild.get_member(int(uid_str))
            if member:
                bal = await core.get_beri(member)
                await self._update_cache(ctx.guild, member, bal)
                updated += 1
        await msg.edit(content=f"✅ Synced **{updated}** balance entries from BeriCore.")

    @beriset.command(name="info")
    async def beriset_info(self, ctx: commands.Context):
        """Show current Beri configuration for this server."""
        name = await self.config.guild(ctx.guild).currency_name()
        icon = await self.config.guild(ctx.guild).currency_icon()
        audit_ch_id = await self.config.guild(ctx.guild).audit_channel()
        audit_ch = ctx.guild.get_channel(audit_ch_id) if audit_ch_id else None
        inc = await self.config.guild(ctx.guild).income()
        cache = await self._get_cache(ctx.guild)
        core_status = "✅ Loaded" if self._core() else "❌ Not loaded"

        embed = discord.Embed(title="⚙️ Beri Config", color=discord.Color.blurple())
        embed.add_field(name="BeriCore", value=core_status, inline=True)
        embed.add_field(name="Currency", value=f"{icon} {name}", inline=True)
        embed.add_field(name="Audit Channel", value=audit_ch.mention if audit_ch else "Not set", inline=True)
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
        embed.add_field(name="Role Stipends", value=f"{len(stipends)} configured" if stipends else "None", inline=True)
        embed.add_field(name="LB Cache", value=f"{len(cache)} users tracked", inline=True)
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
            lines.append(f"`{ts}` **{e['target_name']}** — `{sign}{humanize_number(e['delta'])}` {icon} by **{e['actor_name']}** | `{e['reason']}`")
        embed = discord.Embed(title=f"📋 {name} Audit Log — Last {limit}", description="\n".join(lines), color=discord.Color.blurple())
        await ctx.send(embed=embed)

    @beriaudit.command(name="user")
    async def beriaudit_user(self, ctx, member: discord.Member, limit: int = 10):
        """Show recent transactions for a specific user."""
        limit = max(1, min(limit, 25))
        entries = await self.audit.get_entries(guild_id=ctx.guild.id, user_id=member.id, limit=limit)
        if not entries:
            return await ctx.send(f"No audit entries found for {member.mention}.")
        name, icon = await self._currency_fmt(ctx.guild)
        lines = []
        for e in reversed(entries):
            sign = "+" if e["delta"] >= 0 else ""
            ts = e["ts"][:16].replace("T", " ")
            lines.append(f"`{ts}` `{sign}{humanize_number(e['delta'])}` {icon} by **{e['actor_name']}** | `{e['reason']}`")
        embed = discord.Embed(title=f"📋 {name} Audit — {member.display_name} (last {limit})", description="\n".join(lines), color=discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @beriaudit.command(name="clear")
    @checks.is_owner()
    async def beriaudit_clear(self, ctx: commands.Context):
        """[Bot Owner] Wipe the entire audit log."""
        await self.config.audit_log.set([])
        await ctx.send("✅ Audit log cleared.")
