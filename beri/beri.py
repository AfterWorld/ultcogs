"""
Beri Economy Cog for Red-DiscordBot
Comprehensive balance system with audit logs and full economy management.
Combines Games, Casino, Work, Income, and core BeriCore functionality.
"""

import asyncio
import random
import datetime
import time
import io
import json
from typing import Optional, Dict, Any, List

import discord
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_number, box, pagify
from datetime import datetime as dt_datetime, timezone

from .audit import AuditLog
from .bridge import BeriCoreBridge
from .games import Games
from .casino import Casino
from .work import Work
from .income import Income

# Color scheme
COLORS = {
    "success": discord.Color.green(),
    "error": discord.Color.red(),
    "warning": discord.Color.orange(),
    "info": discord.Color.blurple(),
    "gold": discord.Color.gold(),
}

AUDIT_MAX = 10000


class Beri(BeriCoreBridge, Income, Work, Casino, Games, commands.Cog):
    """
    🏴‍☠️ Beri Economy — the One Piece-themed currency system.
    Comprehensive balance management with audit logs and statistics.
    """

    __version__ = "2.1.0"
    __author__ = "UltPanda"
    __cog_name__ = "BeriCore"  # Register under BeriCore name for API compatibility

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=0xBE71EC0, force_registration=True
        )

        default_guild = {
            "currency_name": "Beri",
            "currency_icon": "🪙",
            "currency_emoji": "💰",
            "audit_channel": None,
            "lb_cache": {},               # {user_id_str: int}
            "transaction_log_channel": 0,
            "leaderboard_update_interval": 300,
            "fine_on_warn": 0,
            "fine_on_mute": 0,
            "fine_on_timeout": 0,
            "income": {
                "message_enabled": True,
                "message_cooldown": 60,
                "message_min": 5,
                "message_max": 25,
                "role_stipends": {},
            },
            "audit": [],
        }

        default_global = {
            "audit_log": [],
        }

        default_member = {
            "balance": 0,
            "last_message_income": None,
            "last_stipend_collect": {},
            "day": 0,
            "earned_today": 0,
            "lifetime_earned": 0,
            "lifetime_spent": 0,
            "total_transactions": 0,
            "first_earned": 0,
            "last_known_level": 0,
        }

        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.config.register_member(**default_member)

        self.audit = AuditLog(bot, self.config)
        self._top_cache = {}

    # ══════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _today() -> int:
        """Get current day as YYYYMMDD integer."""
        return int(time.strftime("%Y%m%d", time.gmtime()))

    @staticmethod
    def _format_timestamp(ts: int) -> str:
        """Format Unix timestamp to readable string."""
        try:
            return dt_datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        except:
            return str(ts)

    async def _get_currency_name(self, guild: discord.Guild) -> str:
        """Get guild's currency name."""
        return await self.config.guild(guild).currency_name()

    async def _get_currency_emoji(self, guild: discord.Guild) -> str:
        """Get guild's currency emoji."""
        return await self.config.guild(guild).currency_emoji()

    async def _get_currency_fmt(self, guild: discord.Guild) -> tuple[str, str]:
        """Get currency name and emoji together."""
        name = await self._get_currency_name(guild)
        emoji = await self._get_currency_emoji(guild)
        return name, emoji

    async def _log_audit(
        self,
        user: discord.abc.User,
        delta: int,
        reason: str,
        actor: Optional[discord.abc.User] = None,
        metadata: Optional[Dict[str, Any]] = None,
        guild: Optional[discord.Guild] = None
    ):
        """Log transaction to audit trail."""
        g = guild or getattr(user, "guild", None)
        if not g:
            return
        
        entry = {
            "ts": int(time.time()),
            "actor_id": int(getattr(actor, "id", 0) or 0),
            "user_id": int(user.id),
            "delta": int(delta),
            "reason": str(reason or "")[:200],
            "metadata": metadata or {},
        }
        
        audit = (await self.config.guild(g).audit()) or []
        audit.append(entry)
        
        if len(audit) > AUDIT_MAX:
            audit = audit[-AUDIT_MAX:]
        
        await self.config.guild(g).audit.set(audit)

    async def _log_transaction(
        self,
        guild: discord.Guild,
        user: discord.abc.User,
        amount: int,
        reason: str,
        actor: Optional[discord.abc.User] = None
    ):
        """Log major transactions to designated channel."""
        channel_id = await self.config.guild(guild).transaction_log_channel()
        if not channel_id:
            return
        
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        
        color = COLORS["success"] if amount > 0 else COLORS["warning"]
        emoji = "➕" if amount > 0 else "➖"
        
        embed = discord.Embed(
            title=f"{emoji} Transaction Log",
            color=color,
            timestamp=dt_datetime.now(timezone.utc)
        )
        
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Amount", value=f"{humanize_number(abs(amount))}", inline=True)
        embed.add_field(name="Type", value="Credit" if amount > 0 else "Debit", inline=True)
        embed.add_field(name="Reason", value=reason[:200], inline=False)
        
        if actor and actor.id != user.id:
            embed.add_field(name="Actor", value=actor.mention, inline=True)
        
        try:
            await channel.send(embed=embed)
        except:
            pass

    # ══════════════════════════════════════════════════════════════════════
    # Public API Methods (for other cogs to call)
    # ══════════════════════════════════════════════════════════════════════

    async def add_beri(
        self,
        user: discord.abc.User,
        amount: int,
        *,
        reason: str = "",
        actor: Optional[discord.abc.User] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Add/subtract Beri and log to audit. Returns new balance."""
        original_amount = amount
        guild = getattr(user, "guild", None)

        # Get current balance
        if isinstance(user, discord.Member):
            bal = await self.config.member(user).balance()
        else:
            bal = await self.config.user(user).balance()
        
        new = max(0, bal + int(amount))
        
        # Set new balance
        if isinstance(user, discord.Member):
            await self.config.member(user).balance.set(new)
        else:
            await self.config.user(user).balance.set(new)

        # Update daily/lifetime stats
        if amount > 0:
            today = self._today()
            if isinstance(user, discord.Member):
                u = await self.config.member(user).all()
            else:
                u = await self.config.user(user).all()
            
            if u["day"] != today:
                if isinstance(user, discord.Member):
                    await self.config.member(user).day.set(today)
                    await self.config.member(user).earned_today.set(0)
                else:
                    await self.config.user(user).day.set(today)
                    await self.config.user(user).earned_today.set(0)
                u["earned_today"] = 0
            
            new_earned_today = int(u.get("earned_today", 0)) + int(amount)
            if isinstance(user, discord.Member):
                await self.config.member(user).earned_today.set(new_earned_today)
            else:
                await self.config.user(user).earned_today.set(new_earned_today)
            
            new_lifetime = int(u.get("lifetime_earned", 0)) + int(amount)
            if isinstance(user, discord.Member):
                await self.config.member(user).lifetime_earned.set(new_lifetime)
            else:
                await self.config.user(user).lifetime_earned.set(new_lifetime)
            
            if not u.get("first_earned"):
                if isinstance(user, discord.Member):
                    await self.config.member(user).first_earned.set(int(time.time()))
                else:
                    await self.config.user(user).first_earned.set(int(time.time()))
        
        elif amount < 0:
            if isinstance(user, discord.Member):
                u = await self.config.member(user).all()
            else:
                u = await self.config.user(user).all()
            new_spent = int(u.get("lifetime_spent", 0)) + abs(int(amount))
            if isinstance(user, discord.Member):
                await self.config.member(user).lifetime_spent.set(new_spent)
            else:
                await self.config.user(user).lifetime_spent.set(new_spent)

        # Increment transaction count
        if isinstance(user, discord.Member):
            u = await self.config.member(user).all()
            await self.config.member(user).total_transactions.set(u.get("total_transactions", 0) + 1)
        else:
            u = await self.config.user(user).all()
            await self.config.user(user).total_transactions.set(u.get("total_transactions", 0) + 1)

        await self._log_audit(user, amount, reason, actor, metadata, guild)
        
        if abs(original_amount) >= 10000 and guild:
            await self._log_transaction(guild, user, amount, reason, actor)

        return new

    async def get_beri(self, user: discord.abc.User) -> int:
        """Get user's current balance."""
        if isinstance(user, discord.Member):
            return await self.config.member(user).balance()
        else:
            return await self.config.user(user).balance()

    async def set_beri(
        self,
        user: discord.abc.User,
        amount: int,
        *,
        reason: str = "manual:set",
        actor: Optional[discord.abc.User] = None
    ) -> int:
        """Set balance directly."""
        current = await self.get_beri(user)
        delta = amount - current
        return await self.add_beri(user, delta, reason=reason, actor=actor)

    async def transfer_beri(
        self,
        from_user: discord.abc.User,
        to_user: discord.abc.User,
        amount: int,
        *,
        reason: str = "transfer",
        tax_rate: float = 0.0
    ) -> tuple[bool, str]:
        """Transfer Beri between users with optional tax."""
        if amount <= 0:
            return False, "Amount must be positive."
        
        sender_bal = await self.get_beri(from_user)
        if amount > sender_bal:
            return False, "Insufficient balance."
        
        tax = int(amount * tax_rate)
        received = amount - tax
        
        await self.add_beri(from_user, -amount, reason=f"{reason}:out", actor=from_user)
        await self.add_beri(to_user, received, reason=f"{reason}:in", actor=from_user)
        
        tax_msg = f" (tax: {humanize_number(tax)})" if tax > 0 else ""
        return True, f"Transferred {humanize_number(received)}{tax_msg}"

    async def get_user_stats(self, user: discord.abc.User) -> Dict[str, Any]:
        """Get comprehensive user statistics."""
        if isinstance(user, discord.Member):
            u = await self.config.member(user).all()
        else:
            u = await self.config.user(user).all()
        today = self._today()
        
        earned_today = u.get("earned_today", 0) if u.get("day") == today else 0
        
        return {
            "balance": u.get("balance", 0),
            "earned_today": earned_today,
            "lifetime_earned": u.get("lifetime_earned", 0),
            "lifetime_spent": u.get("lifetime_spent", 0),
            "total_transactions": u.get("total_transactions", 0),
            "last_known_level": u.get("last_known_level", 0),
            "first_earned": u.get("first_earned", 0),
            "net_earned": u.get("lifetime_earned", 0) - u.get("lifetime_spent", 0),
        }

    async def set_last_level(self, user: discord.abc.User, level: int):
        """Store user's last known level."""
        if isinstance(user, discord.Member):
            await self.config.member(user).last_known_level.set(level)
        else:
            await self.config.user(user).last_known_level.set(level)

    async def get_last_level(self, user: discord.abc.User) -> int:
        """Get user's last known level."""
        if isinstance(user, discord.Member):
            return await self.config.member(user).last_known_level()
        else:
            return await self.config.user(user).last_known_level()

    async def apply_fine(
        self,
        member: discord.Member,
        kind: str,
        *,
        reason: str = "",
        actor: Optional[discord.Member] = None
    ) -> int:
        """Apply configured fine for moderation action."""
        key = {
            "warn": "fine_on_warn",
            "mute": "fine_on_mute",
            "timeout": "fine_on_timeout"
        }.get(kind)
        
        if not key:
            return 0
        
        amt = await self.config.guild(member.guild).get_attr(key)()
        if amt > 0:
            full_reason = f"fine:{kind}:{reason}" if reason else f"fine:{kind}"
            await self.add_beri(member, -amt, reason=full_reason, actor=actor)
        
        return amt

    # ══════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════════════
    # Wallet commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.group(name="beri", invoke_without_command=True)
    @commands.guild_only()
    async def beri_group(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Check your Beri balance (or another user's)."""
        target = member or ctx.author
        name, icon = await self._get_currency_fmt(ctx.guild)

        try:
            balance = await self.get_beri(target)
            stats = await self.get_user_stats(target)
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
        name, icon = await self._get_currency_fmt(ctx.guild)
        new_bal = await self._safe_modify(ctx, ctx.guild, member, amount, reason=reason, actor=ctx.author)
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
        name, icon = await self._get_currency_fmt(ctx.guild)
        new_bal = await self._safe_modify(ctx, ctx.guild, member, -amount, reason=reason, actor=ctx.author)
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
        name, icon = await self._get_currency_fmt(ctx.guild)
        try:
            old_bal = await self.get_beri(member)
            delta = amount - old_bal
            new_bal = await self._modify_balance(ctx.guild, member, delta, reason=reason, actor=ctx.author)
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
        name, icon = await self._get_currency_fmt(ctx.guild)
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
        name, icon = await self._get_currency_fmt(ctx.guild)

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
        """Re-sync leaderboard cache from current balances. Run if LB looks stale."""
        cache = await self._get_cache(ctx.guild)
        if not cache:
            return await ctx.send("Cache is empty — nothing to sync.")
        msg = await ctx.send(f"⏳ Syncing {len(cache)} entries...")
        updated = 0
        for uid_str in list(cache.keys()):
            member = ctx.guild.get_member(int(uid_str))
            if member:
                bal = await self.get_beri(member)
                await self._update_cache(ctx.guild, member, bal)
                updated += 1
        await msg.edit(content=f"✅ Synced **{updated}** balance entries from data.")

    @beriset.command(name="info")
    async def beriset_info(self, ctx: commands.Context):
        """Show current Beri configuration for this server."""
        name = await self.config.guild(ctx.guild).currency_name()
        icon = await self.config.guild(ctx.guild).currency_icon()
        audit_ch_id = await self.config.guild(ctx.guild).audit_channel()
        audit_ch = ctx.guild.get_channel(audit_ch_id) if audit_ch_id else None
        inc = await self.config.guild(ctx.guild).income()
        cache = await self._get_cache(ctx.guild)

        embed = discord.Embed(title="⚙️ Beri Config", color=discord.Color.blurple())
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
        aud = (await self.config.guild(ctx.guild).audit()) or []
        if not aud:
            return await ctx.send("No audit entries yet.")
        
        rows = []
        for e in aud[-limit:]:
            ts = int(e.get("ts", 0)) or int(time.time())
            user = ctx.guild.get_member(e.get("user_id", 0)) or self.bot.get_user(e.get("user_id", 0))
            actor = None
            if e.get("actor_id"):
                actor = ctx.guild.get_member(e["actor_id"]) or self.bot.get_user(e["actor_id"])
            
            user_txt = user.mention if isinstance(user, discord.Member) else (str(user) if user else f"User {e.get('user_id')}")
            actor_txt = actor.mention if isinstance(actor, discord.Member) else ("system" if not actor else str(actor))
            reason = e.get("reason", "").strip() or "—"
            delta = e.get("delta", 0)
            
            rows.append(f"<t:{ts}:F> | {user_txt} Δ{delta:+} by {actor_txt} • {reason}")
        
        for page in pagify("\n".join(rows), delims=["\n"], page_length=1900):
            await ctx.send(page)

    @beriaudit.command(name="user")
    async def beriaudit_user(self, ctx: commands.Context, member: discord.Member, limit: int = 10):
        """Show audit log for a specific user."""
        limit = max(1, min(limit, 25))
        aud = (await self.config.guild(ctx.guild).audit()) or []
        user_entries = [e for e in aud if e.get("user_id") == member.id]
        
        if not user_entries:
            return await ctx.send(f"No audit entries for {member.mention}.")
        
        rows = []
        for e in user_entries[-limit:]:
            ts = int(e.get("ts", 0)) or int(time.time())
            reason = e.get("reason", "").strip() or "—"
            delta = e.get("delta", 0)
            rows.append(f"<t:{ts}:F> | Δ{delta:+} • {reason}")
        
        for page in pagify("\n".join(rows), delims=["\n"], page_length=1900):
            await ctx.send(page)

    @checks.admin_or_permissions(manage_guild=True)
    @beriaudit.command(name="export")
    async def beriaudit_export(self, ctx: commands.Context):
        """Export audit log to JSON."""
        aud = await self.config.guild(ctx.guild).audit()
        b = io.BytesIO(json.dumps(aud, indent=2).encode("utf-8"))
        b.seek(0)
        await ctx.send("📋 Audit log exported:", file=discord.File(b, filename=f"beri_audit_{ctx.guild.id}_{int(time.time())}.json"))

    @checks.admin_or_permissions(manage_guild=True)
    @beriaudit.command(name="clear")
    async def beriaudit_clear(self, ctx: commands.Context):
        """Clear entire audit log."""
        await self.config.guild(ctx.guild).audit.set([])
        await ctx.send("✅ Audit log cleared.")
