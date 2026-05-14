"""
Beri Economy Cog for Red-DiscordBot
Routes all balance operations through BeriCore (bot.get_cog("BeriCore")).
No caps, no shop, no boosters — just a clean economy layer with
audit logging, games, activity commands, and passive income.
"""

import io
import json
import time
from typing import Optional

import discord
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_number, pagify

from .audit import AuditLog
from .casino import Casino
from .games import Games
from .income import Income
from .work import Work


class Beri(Income, Work, Casino, Games, commands.Cog):
    """
    🏴‍☠️ Beri — One Piece-themed economy layer on top of BeriCore.
    Provides gambling, activity commands, passive income, and audit logs.
    Requires BeriCore to be loaded.
    """

    __version__ = "3.0.0"
    __author__ = "UltPanda"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0xBE71000, force_registration=True)

        default_guild = {
            "currency_name": "Beri",
            "currency_icon": "🪙",
            "audit_channel": None,
            "lb_cache": {},   # {user_id_str: balance}
            "income": {
                "message_enabled": True,
                "message_cooldown": 60,
                "message_min": 5,
                "message_max": 25,
                "role_stipends": {},
            },
            "audit": [],
        }

        default_member = {
            "last_message_income": None,
            "last_stipend_collect": {},
        }

        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

        self.audit = AuditLog(bot, self.config)

    # ══════════════════════════════════════════════════════════════════════
    # BeriCore accessor
    # ══════════════════════════════════════════════════════════════════════

    def _core(self):
        """Return the loaded BeriCore cog, or None."""
        return self.bot.get_cog("BeriCore")

    # ══════════════════════════════════════════════════════════════════════
    # Shared helpers used by mixin classes
    # ══════════════════════════════════════════════════════════════════════

    async def _currency_fmt(self, guild: discord.Guild) -> tuple[str, str]:
        """Return (currency_name, currency_icon) for this guild."""
        name = await self.config.guild(guild).currency_name()
        icon = await self.config.guild(guild).currency_icon()
        return name, icon

    async def _update_lb_cache(self, guild: discord.Guild, user: discord.Member, balance: int):
        """Mirror a balance into the per-guild leaderboard cache."""
        async with self.config.guild(guild).lb_cache() as cache:
            cache[str(user.id)] = balance

    # ══════════════════════════════════════════════════════════════════════
    # Wallet commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.group(name="beri", invoke_without_command=True)
    @commands.guild_only()
    async def beri_group(
        self, ctx: commands.Context, member: Optional[discord.Member] = None
    ):
        """Check your Beri balance (or another user's)."""
        core = self._core()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        target = member or ctx.author
        name, icon = await self._currency_fmt(ctx.guild)

        balance = await core.get_beri(target)
        stats = await core.get_user_stats(target)

        # Keep the LB cache fresh on balance checks
        await self._update_lb_cache(ctx.guild, target if isinstance(target, discord.Member) else ctx.author, balance)

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
    async def beri_give(
        self, ctx, member: discord.Member, amount: int, *, reason: str = "admin:give"
    ):
        """[Admin] Give Beri to a user."""
        if amount <= 0:
            return await ctx.send("❌ Amount must be positive.")

        core = self._core()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        name, icon = await self._currency_fmt(ctx.guild)
        new_bal = await core.add_beri(member, amount, reason=reason, actor=ctx.author)
        await self._update_lb_cache(ctx.guild, member, new_bal)
        await self.audit.log(
            guild=ctx.guild, target=member, actor=ctx.author,
            delta=amount, new_balance=new_bal, reason=reason,
        )
        await ctx.send(
            f"✅ Gave **{humanize_number(amount)}** {icon} to {member.mention}. "
            f"New balance: **{humanize_number(new_bal)}** {icon}."
        )

    @beri_group.command(name="take")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beri_take(
        self, ctx, member: discord.Member, amount: int, *, reason: str = "admin:take"
    ):
        """[Admin] Remove Beri from a user."""
        if amount <= 0:
            return await ctx.send("❌ Amount must be positive.")

        core = self._core()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        name, icon = await self._currency_fmt(ctx.guild)
        new_bal = await core.add_beri(member, -amount, reason=reason, actor=ctx.author)
        await self._update_lb_cache(ctx.guild, member, new_bal)
        await self.audit.log(
            guild=ctx.guild, target=member, actor=ctx.author,
            delta=-amount, new_balance=new_bal, reason=reason,
        )
        await ctx.send(
            f"✅ Took **{humanize_number(amount)}** {icon} from {member.mention}. "
            f"New balance: **{humanize_number(new_bal)}** {icon}."
        )

    @beri_group.command(name="set")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beri_set(
        self, ctx, member: discord.Member, amount: int, *, reason: str = "admin:set"
    ):
        """[Admin] Set a user's Beri balance to an exact amount."""
        if amount < 0:
            return await ctx.send("❌ Amount cannot be negative.")

        core = self._core()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        name, icon = await self._currency_fmt(ctx.guild)
        old_bal = await core.get_beri(member)
        delta = amount - old_bal
        new_bal = await core.add_beri(member, delta, reason=reason, actor=ctx.author)
        await self._update_lb_cache(ctx.guild, member, new_bal)
        await self.audit.log(
            guild=ctx.guild, target=member, actor=ctx.author,
            delta=delta, new_balance=new_bal, reason=reason,
        )
        await ctx.send(
            f"✅ Set {member.mention}'s balance to **{humanize_number(new_bal)}** {icon}."
        )

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

        core = self._core()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        name, icon = await self._currency_fmt(ctx.guild)
        success, msg = await core.transfer_beri(
            ctx.author, member, amount, reason="user:transfer", tax_rate=0.05
        )

        if success:
            received = int(amount * 0.95)
            # Refresh LB cache for both users
            from_bal = await core.get_beri(ctx.author)
            to_bal = await core.get_beri(member)
            await self._update_lb_cache(ctx.guild, ctx.author, from_bal)
            await self._update_lb_cache(ctx.guild, member, to_bal)
            await ctx.send(
                f"✅ Sent **{humanize_number(amount)}** {icon} to {member.mention}. "
                f"They received **{humanize_number(received)}** {icon} after 5% tax."
            )
        else:
            await ctx.send(f"❌ {msg}")

    @beri_group.command(name="top", aliases=["leaderboard", "lb"])
    @commands.guild_only()
    async def beri_top(self, ctx: commands.Context, page: int = 1):
        """Show the Beri leaderboard for this server."""
        cache = await self.config.guild(ctx.guild).lb_cache()
        name, icon = await self._currency_fmt(ctx.guild)

        if not cache:
            return await ctx.send("No balances recorded yet. Use `[p]beri` to update the cache.")

        sorted_bal = sorted(cache.items(), key=lambda x: x[1], reverse=True)
        per_page = 10
        total_pages = max(1, (len(sorted_bal) + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        chunk = sorted_bal[start : start + per_page]

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = []
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
        embed.set_footer(
            text=f"Page {page}/{total_pages} • {len(sorted_bal)} users tracked • "
                 f"Use {ctx.prefix}beri to refresh your entry"
        )
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════════════════════
    # Config commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.group(name="beriset")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beriset(self, ctx: commands.Context):
        """Configure the Beri cog."""

    @beriset.command(name="currencyname")
    async def beriset_currencyname(self, ctx, *, name: str):
        """Set the display name for the currency (default: Beri)."""
        await self.config.guild(ctx.guild).currency_name.set(name)
        await ctx.send(f"✅ Currency name set to **{name}**.")

    @beriset.command(name="currencyicon")
    async def beriset_currencyicon(self, ctx, icon: str):
        """Set the currency icon/emoji (default: 🪙)."""
        await self.config.guild(ctx.guild).currency_icon.set(icon)
        await ctx.send(f"✅ Currency icon set to {icon}.")

    @beriset.command(name="auditchannel")
    async def beriset_auditchannel(
        self, ctx, channel: Optional[discord.TextChannel] = None
    ):
        """Set the channel for live audit log posts. Leave blank to disable."""
        if channel:
            await self.config.guild(ctx.guild).audit_channel.set(channel.id)
            await ctx.send(f"✅ Audit log will post to {channel.mention}.")
        else:
            await self.config.guild(ctx.guild).audit_channel.set(None)
            await ctx.send("✅ Audit log channel disabled.")

    @beriset.command(name="synccache")
    async def beriset_synccache(self, ctx: commands.Context):
        """Re-sync the leaderboard cache from live BeriCore balances."""
        core = self._core()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        cache = await self.config.guild(ctx.guild).lb_cache()
        if not cache:
            return await ctx.send("Cache is empty — nothing to sync.")

        msg = await ctx.send(f"⏳ Syncing {len(cache)} entries...")
        updated = 0
        for uid_str in list(cache.keys()):
            member = ctx.guild.get_member(int(uid_str))
            if member:
                bal = await core.get_beri(member)
                await self._update_lb_cache(ctx.guild, member, bal)
                updated += 1
        await msg.edit(content=f"✅ Synced **{updated}** entries.")

    @beriset.command(name="info")
    async def beriset_info(self, ctx: commands.Context):
        """Show current Beri configuration for this server."""
        core = self._core()
        name = await self.config.guild(ctx.guild).currency_name()
        icon = await self.config.guild(ctx.guild).currency_icon()
        audit_ch_id = await self.config.guild(ctx.guild).audit_channel()
        audit_ch = ctx.guild.get_channel(audit_ch_id) if audit_ch_id else None
        inc = await self.config.guild(ctx.guild).income()
        cache = await self.config.guild(ctx.guild).lb_cache()

        embed = discord.Embed(title="⚙️ Beri Config", color=discord.Color.blurple())
        embed.add_field(name="Currency", value=f"{icon} {name}", inline=True)
        embed.add_field(
            name="BeriCore",
            value="✅ Loaded" if core else "❌ Not loaded",
            inline=True,
        )
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
                f"/ {inc.get('message_cooldown', 60)}s cooldown"
            ),
            inline=True,
        )
        stipends = inc.get("role_stipends", {})
        embed.add_field(
            name="Role Stipends",
            value=f"{len(stipends)} configured" if stipends else "None",
            inline=True,
        )
        embed.add_field(name="LB Cache", value=f"{len(cache)} users tracked", inline=True)
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════════════════════
    # Audit log commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.group(name="beriaudit", aliases=["baudit"])
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def beriaudit(self, ctx: commands.Context):
        """View the Beri local audit log."""

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
            user_id = e.get("user_id") or e.get("target_id", 0)
            member = ctx.guild.get_member(user_id) or self.bot.get_user(user_id)
            user_txt = member.mention if isinstance(member, discord.Member) else f"User {user_id}"
            actor_txt = e.get("actor_name", "System")
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
        user_entries = [
            e for e in aud
            if e.get("target_id") == member.id or e.get("user_id") == member.id
        ]

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

    @beriaudit.command(name="export")
    async def beriaudit_export(self, ctx: commands.Context):
        """Export the local audit log to JSON."""
        aud = await self.config.guild(ctx.guild).audit()
        b = io.BytesIO(json.dumps(aud, indent=2).encode("utf-8"))
        b.seek(0)
        await ctx.send(
            "📋 Audit log exported:",
            file=discord.File(b, filename=f"beri_audit_{ctx.guild.id}_{int(time.time())}.json"),
        )

    @beriaudit.command(name="clear")
    async def beriaudit_clear(self, ctx: commands.Context):
        """Clear the local audit log."""
        await self.config.guild(ctx.guild).audit.set([])
        await ctx.send("✅ Audit log cleared.")
