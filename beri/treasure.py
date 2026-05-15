"""
Treasure Maps and Den Den Mushi Lottery for the Beri economy cog.

Treasure Maps:
  - [p]buymap <tier>     — buy a map (East Blue / Grand Line / New World)
  - [p]usemap            — dig up your map for a loot roll
  - [p]mymaps            — check how many maps you own per tier

Den Den Mushi Lottery:
  - [p]buyticket [qty]   — buy 1–10 lottery tickets (configurable price)
  - [p]lotteryinfo       — show current pot, ticket count, and next draw
  - [p]lotterydraw       — (Admin) force an early draw
  - [p]lotteryset ...    — (Admin) configure ticket price / schedule
"""

import asyncio
import datetime
import random
from typing import Optional

import discord
from redbot.core import commands, checks
from discord.ext import tasks
from redbot.core.utils.chat_formatting import humanize_number

# ══════════════════════════════════════════════════════════════════════════════
# Map data
# ══════════════════════════════════════════════════════════════════════════════

MAP_TIERS = {
    "eastblue": {
        "label": "🗺️ East Blue Map",
        "cost": 500,
        "loot_min": 200,
        "loot_max": 1_200,
        "jackpot_chance": 0.03,
        "jackpot_mult": 5,
        "flavour": [
            "You unroll the faded chart and follow the X into a cove…",
            "A rusted shovel and a moonlit beach — the map leads true…",
            "The coconut trees part to reveal a small buried chest…",
        ],
    },
    "grandline": {
        "label": "🧭 Grand Line Map",
        "cost": 2_000,
        "loot_min": 1_000,
        "loot_max": 5_000,
        "jackpot_chance": 0.05,
        "jackpot_mult": 8,
        "flavour": [
            "The Log Pose spins wildly before pointing dead ahead…",
            "Giant sea kings circle as you dive to the wreck below…",
            "A Sea Train tunnel hides the vault no one expected…",
        ],
    },
    "newworld": {
        "label": "🔱 New World Map",
        "cost": 8_000,
        "loot_min": 4_000,
        "loot_max": 20_000,
        "jackpot_chance": 0.08,
        "jackpot_mult": 12,
        "flavour": [
            "Volcanic rock crumbles to reveal a chest fused with Seastone…",
            "The Emperor's old hideout — untouched for decades. Until now.",
            "You crack the Poneglyph seal and find a chamber stuffed with gold…",
        ],
    },
}

TIER_ALIASES = {
    "east": "eastblue", "eastblue": "eastblue", "east blue": "eastblue", "eb": "eastblue",
    "grand": "grandline", "grandline": "grandline", "grand line": "grandline", "gl": "grandline",
    "new": "newworld", "newworld": "newworld", "new world": "newworld", "nw": "newworld",
}

# ══════════════════════════════════════════════════════════════════════════════
# Lottery defaults
# ══════════════════════════════════════════════════════════════════════════════

LOTTERY_DEFAULTS = {
    "ticket_price": 250,
    "schedule": "daily",       # "daily" or "weekly"
    "last_draw": None,          # ISO timestamp
    "pot": 0,
    "tickets": {},              # {str(user_id): int count}
    "channel": None,            # channel id to announce results
    "house_cut": 0.10,          # 10 % goes to the house (sink)
}


# ══════════════════════════════════════════════════════════════════════════════
# Mixin class
# ══════════════════════════════════════════════════════════════════════════════

class Treasure(commands.Cog):
    """
    Treasure Maps & Den Den Mushi Lottery mixin.

    Expects parent (BeriCog) to expose:
      self.config
      self._get_balance(guild, member)
      self._modify_balance(guild, member, delta, *, reason, actor, metadata=None)
      self._safe_modify(ctx, guild, member, delta, *, reason, actor, metadata=None)
      self._currency_fmt(guild)
    """

    # ── Config keys this mixin owns ───────────────────────────────────────
    # Registered in BeriCog.__init__ via register_guild / register_member.
    #
    # guild:  "maps"    → { "eastblue": int, "grandline": int, "newworld": int }
    #         "lottery" → LOTTERY_DEFAULTS dict
    # member: "maps"    → { "eastblue": int, "grandline": int, "newworld": int }

    # ─────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────

    async def _maps_of(self, member: discord.Member) -> dict:
        return await self.config.member(member).maps()

    async def _lottery_cfg(self, guild: discord.Guild) -> dict:
        return await self.config.guild(guild).lottery()

    def _next_draw_dt(self, last_draw_iso: Optional[str], schedule: str) -> datetime.datetime:
        """Return the next scheduled draw datetime (UTC)."""
        if last_draw_iso:
            last = datetime.datetime.fromisoformat(last_draw_iso)
        else:
            last = datetime.datetime.now(tz=datetime.timezone.utc)
        delta = datetime.timedelta(days=1 if schedule == "daily" else 7)
        return last + delta

    def _fmt_timedelta(self, td: datetime.timedelta) -> str:
        total = int(td.total_seconds())
        if total <= 0:
            return "any moment now"
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        parts = []
        if h: parts.append(f"{h}h")
        if m: parts.append(f"{m}m")
        if s or not parts: parts.append(f"{s}s")
        return " ".join(parts)

    # ─────────────────────────────────────────────────────────────────────
    # Lottery auto-draw background task
    # ─────────────────────────────────────────────────────────────────────

    def cog_load(self):
        self._lottery_loop.start()
        self._lottery_update_loop.start()

    def cog_unload(self):
        self._lottery_loop.cancel()
        self._lottery_update_loop.cancel()

    @tasks.loop(minutes=5)
    async def _lottery_loop(self):
        """Check every 5 minutes if any guild's lottery is due."""
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        for guild in self.bot.guilds:
            try:
                cfg = await self._lottery_cfg(guild)
                if not cfg.get("tickets"):
                    continue
                next_draw = self._next_draw_dt(cfg.get("last_draw"), cfg.get("schedule", "daily"))
                if now >= next_draw:
                    await self._run_lottery(guild)
            except Exception:
                pass  # never let one guild crash the loop

    @_lottery_loop.before_loop
    async def _before_lottery_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=60)
    async def _lottery_update_loop(self):
        """Hourly announcement of current pot / tickets to the configured channel."""
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        for guild in self.bot.guilds:
            try:
                cfg = await self._lottery_cfg(guild)
                pot = cfg.get("pot", 0)
                tickets: dict = cfg.get("tickets", {})
                if not pot:
                    continue

                ch_id = cfg.get("channel")
                channel = guild.get_channel(ch_id) if ch_id else guild.system_channel
                if not channel:
                    continue

                name, icon = await self._currency_fmt(guild)
                total_tickets = sum(tickets.values())
                schedule = cfg.get("schedule", "daily")
                next_draw = self._next_draw_dt(cfg.get("last_draw"), schedule)
                remaining = next_draw - now

                embed = discord.Embed(
                    title="📞 Den Den Mushi Lottery — Update",
                    color=discord.Color.gold(),
                )
                embed.add_field(name="🏆 Current Pot", value=f"**{humanize_number(pot)}** {icon}", inline=False)
                embed.add_field(name="🎟️ Total Tickets", value=str(total_tickets), inline=True)
                embed.add_field(name="💸 Ticket Price", value=f"{humanize_number(cfg.get('ticket_price', LOTTERY_DEFAULTS['ticket_price']))} {icon}", inline=True)
                embed.add_field(name="⏰ Next Draw In", value=self._fmt_timedelta(remaining), inline=True)
                embed.set_footer(text="Buy tickets with the buyticket command.")
                try:
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    pass
            except Exception:
                pass

    @_lottery_update_loop.before_loop
    async def _before_lottery_update_loop(self):
        await self.bot.wait_until_ready()

    # ─────────────────────────────────────────────────────────────────────
    # Core lottery draw logic
    # ─────────────────────────────────────────────────────────────────────

    async def _run_lottery(self, guild: discord.Guild, forced_by=None, announce_channel: Optional[discord.TextChannel] = None):
        """
        Pick a winner, pay out, reset the pot and ticket pool.
        Returns the winner Member or None if no tickets.
        """
        async with self.config.guild(guild).lottery() as cfg:
            tickets: dict = cfg.get("tickets", {})
            pot: int = cfg.get("pot", 0)

            if not tickets or pot == 0:
                return None

            # Build weighted pool
            pool = []
            for uid, count in tickets.items():
                pool.extend([int(uid)] * count)

            winner_id = random.choice(pool)
            winner = guild.get_member(winner_id)

            house_cut = cfg.get("house_cut", 0.10)
            payout = int(pot * (1 - house_cut))

            # Reset
            cfg["tickets"] = {}
            cfg["pot"] = 0
            cfg["last_draw"] = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()

        name, icon = await self._currency_fmt(guild)
        total_tickets = len(pool)

        if winner:
            try:
                await self._modify_balance(
                    guild, winner, payout,
                    reason="lottery:win",
                    actor="Den Den Mushi",
                    metadata={"pot": pot, "tickets": total_tickets},
                )
            except RuntimeError:
                pass

        # Announce
        if announce_channel is not None:
            channel = announce_channel
        else:
            cfg_fresh = await self._lottery_cfg(guild)
            ch_id = cfg_fresh.get("channel")
            channel = guild.get_channel(ch_id) if ch_id else None
            if not channel:
                # Fallback: system channel
                channel = guild.system_channel

        if channel:
            embed = discord.Embed(
                title="📞 Den Den Mushi Lottery — DRAW!",
                color=discord.Color.gold(),
            )
            if winner:
                embed.description = (
                    f"🎉 {winner.mention} wins the pot of **{humanize_number(payout)}** {icon}!\n"
                    f"*(House kept {int(house_cut*100)}% — {humanize_number(pot - payout)} {icon})*"
                )
                embed.add_field(name="Winner", value=winner.display_name, inline=True)
                embed.add_field(name="Winning Ticket", value=f"{tickets.get(str(winner_id), '?')} ticket(s) held", inline=True)
            else:
                embed.description = "No tickets were sold. No winner this round."
            embed.add_field(name="Total Tickets", value=str(total_tickets), inline=True)
            embed.add_field(name="Total Pot", value=f"{humanize_number(pot)} {icon}", inline=True)
            if forced_by:
                embed.set_footer(text=f"Draw forced by {forced_by}")
            else:
                embed.set_footer(text="Automatically drawn by the Den Den Mushi.")
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass

        return winner

    # ══════════════════════════════════════════════════════════════════════
    # Treasure Map commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.command(name="buymap", aliases=["mapbuy"])
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def buymap(self, ctx: commands.Context, *, tier: str = "eastblue"):
        """
        Buy a treasure map.

        Tiers: `eastblue` (500), `grandline` (2,000), `newworld` (8,000)
        Aliases: `east`, `grand`, `new`, `eb`, `gl`, `nw`
        """
        tier_key = TIER_ALIASES.get(tier.lower().replace(" ", ""))
        if not tier_key:
            lines = "\n".join(
                f"`{k}` — {v['label']} — **{humanize_number(v['cost'])}** {{}}"
                for k, v in MAP_TIERS.items()
            )
            name, icon = await self._currency_fmt(ctx.guild)
            return await ctx.send(
                f"❌ Unknown tier. Available maps:\n" +
                lines.format(icon)
            )

        tier_data = MAP_TIERS[tier_key]
        cost = tier_data["cost"]
        name, icon = await self._currency_fmt(ctx.guild)

        balance = await self._get_balance(ctx.guild, ctx.author)
        if balance < cost:
            return await ctx.send(
                f"❌ You need **{humanize_number(cost)}** {icon} for a {tier_data['label']}. "
                f"You have **{humanize_number(balance)}** {icon}."
            )

        new_bal = await self._safe_modify(
            ctx, ctx.guild, ctx.author, -cost,
            reason=f"treasure:buymap:{tier_key}",
            actor=ctx.author,
        )
        if new_bal is None:
            return

        async with self.config.member(ctx.author).maps() as maps:
            maps[tier_key] = maps.get(tier_key, 0) + 1

        embed = discord.Embed(
            title=f"{tier_data['label']} Purchased!",
            description=f"Rolled up and tucked into your coat. Use `{ctx.prefix}usemap` to dig it up.",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Cost", value=f"**-{humanize_number(cost)}** {icon}", inline=True)
        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=ctx.author.display_name)
        await ctx.send(embed=embed)

    @commands.command(name="usemap", aliases=["digmap", "openmap"])
    @commands.guild_only()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def usemap(self, ctx: commands.Context, *, tier: str = ""):
        """
        Use one of your treasure maps for a loot roll.
        If you own multiple tiers, specify which: `eastblue`, `grandline`, `newworld`.
        Defaults to your highest tier map.
        """
        name, icon = await self._currency_fmt(ctx.guild)
        maps: dict = await self._maps_of(ctx.author)

        # Filter to maps the user actually has
        owned = {k: v for k, v in maps.items() if v > 0}
        if not owned:
            return await ctx.send(
                f"❌ You don't have any treasure maps. Buy one with `{ctx.prefix}buymap`."
            )

        # Resolve tier
        if tier:
            tier_key = TIER_ALIASES.get(tier.lower().replace(" ", ""))
            if not tier_key or owned.get(tier_key, 0) == 0:
                return await ctx.send(
                    f"❌ You don't have a map of that tier. "
                    f"You own: {', '.join(MAP_TIERS[k]['label'] for k in owned)}."
                )
        else:
            # Default: highest tier
            for tk in ["newworld", "grandline", "eastblue"]:
                if owned.get(tk, 0) > 0:
                    tier_key = tk
                    break

        tier_data = MAP_TIERS[tier_key]

        # Consume the map
        async with self.config.member(ctx.author).maps() as m:
            m[tier_key] = max(0, m.get(tier_key, 1) - 1)

        # Roll loot
        jackpot = random.random() < tier_data["jackpot_chance"]
        base = random.randint(tier_data["loot_min"], tier_data["loot_max"])
        loot = base * tier_data["jackpot_mult"] if jackpot else base
        flavour = random.choice(tier_data["flavour"])

        new_bal = await self._safe_modify(
            ctx, ctx.guild, ctx.author, loot,
            reason=f"treasure:usemap:{tier_key}:{'jackpot' if jackpot else 'normal'}",
            actor=ctx.author,
            metadata={"tier": tier_key, "jackpot": jackpot, "loot": loot},
        )
        if new_bal is None:
            return

        color = discord.Color.gold() if jackpot else discord.Color.green()
        title = (
            f"💰 JACKPOT! {tier_data['label']}"
            if jackpot else
            f"🗺️ {tier_data['label']} — Loot Found!"
        )
        embed = discord.Embed(title=title, description=flavour, color=color)
        if jackpot:
            embed.add_field(
                name="🌟 Jackpot Multiplier",
                value=f"x{tier_data['jackpot_mult']}",
                inline=True,
            )
        embed.add_field(name="Loot", value=f"**+{humanize_number(loot)}** {icon}", inline=True)
        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        remaining = (await self._maps_of(ctx.author)).get(tier_key, 0)
        embed.set_footer(text=f"{ctx.author.display_name} • {remaining} {tier_data['label']}(s) remaining")
        await ctx.send(embed=embed)

    @commands.command(name="mymaps", aliases=["maps", "mapinv"])
    @commands.guild_only()
    async def mymaps(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Check how many treasure maps you (or another user) own."""
        target = member or ctx.author
        name, icon = await self._currency_fmt(ctx.guild)
        maps = await self._maps_of(target)

        lines = []
        total = 0
        for tier_key, tier_data in MAP_TIERS.items():
            count = maps.get(tier_key, 0)
            total += count
            lines.append(f"{tier_data['label']} — **{count}** map(s)")

        embed = discord.Embed(
            title=f"🗺️ {target.display_name}'s Maps",
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Total: {total} map(s) • Buy more with {ctx.prefix}buymap")
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════════════════════
    # Den Den Mushi Lottery commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.command(name="buyticket", aliases=["lotto"])
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def buyticket(self, ctx: commands.Context, qty: int = 1):
        """
        Buy lottery tickets for the Den Den Mushi Lottery.
        Each ticket is a separate entry. Max 10 per purchase.
        """
        qty = max(1, min(qty, 10))
        cfg = await self._lottery_cfg(ctx.guild)
        price_each = cfg.get("ticket_price", LOTTERY_DEFAULTS["ticket_price"])
        total_cost = price_each * qty
        name, icon = await self._currency_fmt(ctx.guild)

        balance = await self._get_balance(ctx.guild, ctx.author)
        if balance < total_cost:
            return await ctx.send(
                f"❌ {qty} ticket(s) cost **{humanize_number(total_cost)}** {icon}. "
                f"You only have **{humanize_number(balance)}** {icon}."
            )

        new_bal = await self._safe_modify(
            ctx, ctx.guild, ctx.author, -total_cost,
            reason=f"lottery:buyticket:{qty}",
            actor=ctx.author,
        )
        if new_bal is None:
            return

        async with self.config.guild(ctx.guild).lottery() as lotto:
            uid = str(ctx.author.id)
            lotto["tickets"][uid] = lotto["tickets"].get(uid, 0) + qty
            lotto["pot"] = lotto.get("pot", 0) + total_cost
            if lotto.get("last_draw") is None:
                lotto["last_draw"] = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
            total_held = lotto["tickets"][uid]
            pot = lotto["pot"]

        embed = discord.Embed(
            title="📞 Den Den Mushi — Tickets Purchased!",
            description=f"You bought **{qty}** ticket(s) and entered the draw.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Cost", value=f"**-{humanize_number(total_cost)}** {icon}", inline=True)
        embed.add_field(name="Your Tickets", value=str(total_held), inline=True)
        embed.add_field(name="Current Pot", value=f"**{humanize_number(pot)}** {icon}", inline=True)
        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=f"Use {ctx.prefix}lotteryinfo to see draw schedule.")
        await ctx.send(embed=embed)

    @commands.command(name="lotteryinfo", aliases=["lottoinfo"])
    @commands.guild_only()
    async def lotteryinfo(self, ctx: commands.Context):
        """Show the current lottery pot, ticket counts, and next draw time."""
        cfg = await self._lottery_cfg(ctx.guild)
        name, icon = await self._currency_fmt(ctx.guild)

        pot = cfg.get("pot", 0)
        tickets: dict = cfg.get("tickets", {})
        schedule = cfg.get("schedule", "daily")
        price = cfg.get("ticket_price", LOTTERY_DEFAULTS["ticket_price"])
        house_cut = cfg.get("house_cut", 0.10)
        total_tickets = sum(tickets.values())
        your_tickets = tickets.get(str(ctx.author.id), 0)
        payout = int(pot * (1 - house_cut))

        next_draw = self._next_draw_dt(cfg.get("last_draw"), schedule)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        remaining = next_draw - now

        odds = f"{your_tickets}/{total_tickets}" if total_tickets else "—"

        embed = discord.Embed(
            title="📞 Den Den Mushi Lottery",
            color=discord.Color.gold(),
        )
        embed.add_field(name="🏆 Pot", value=f"**{humanize_number(payout)}** {icon} (after house cut)", inline=False)
        embed.add_field(name="🎟️ Ticket Price", value=f"{humanize_number(price)} {icon}", inline=True)
        embed.add_field(name="📋 Total Tickets Sold", value=str(total_tickets), inline=True)
        embed.add_field(name="Your Tickets", value=f"{your_tickets} (odds: {odds})", inline=True)
        embed.add_field(name="📅 Schedule", value=schedule.capitalize(), inline=True)
        embed.add_field(
            name="⏰ Next Draw",
            value=f"In **{self._fmt_timedelta(remaining)}**" if remaining.total_seconds() > 0 else "Drawing soon!",
            inline=True,
        )
        embed.set_footer(text=f"Buy tickets with {ctx.prefix}buyticket [qty]")
        await ctx.send(embed=embed)

    # ── Admin commands ────────────────────────────────────────────────────

    @commands.group(name="lotteryset", aliases=["lottocfg"])
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def lotteryset(self, ctx: commands.Context):
        """Configure the Den Den Mushi Lottery."""

    @lotteryset.command(name="price")
    async def lotteryset_price(self, ctx: commands.Context, amount: int):
        """Set the ticket price."""
        if amount < 1:
            return await ctx.send("❌ Price must be at least 1.")
        async with self.config.guild(ctx.guild).lottery() as cfg:
            cfg["ticket_price"] = amount
        name, icon = await self._currency_fmt(ctx.guild)
        await ctx.send(f"✅ Ticket price set to **{humanize_number(amount)}** {icon}.")

    @lotteryset.command(name="schedule")
    async def lotteryset_schedule(self, ctx: commands.Context, schedule: str):
        """Set draw schedule: `daily` or `weekly`."""
        schedule = schedule.lower()
        if schedule not in ("daily", "weekly"):
            return await ctx.send("❌ Schedule must be `daily` or `weekly`.")
        async with self.config.guild(ctx.guild).lottery() as cfg:
            cfg["schedule"] = schedule
        await ctx.send(f"✅ Lottery will now draw **{schedule}**.")

    @lotteryset.command(name="channel")
    async def lotteryset_channel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Set the channel where lottery results are announced."""
        async with self.config.guild(ctx.guild).lottery() as cfg:
            cfg["channel"] = channel.id if channel else None
        if channel:
            await ctx.send(f"✅ Lottery results will post in {channel.mention}.")
        else:
            await ctx.send("✅ Lottery channel cleared (will use system channel as fallback).")

    @lotteryset.command(name="housecut")
    async def lotteryset_housecut(self, ctx: commands.Context, percent: float):
        """Set the house cut percentage (0–50). Default is 10."""
        if not (0 <= percent <= 50):
            return await ctx.send("❌ House cut must be between 0 and 50.")
        async with self.config.guild(ctx.guild).lottery() as cfg:
            cfg["house_cut"] = percent / 100
        await ctx.send(f"✅ House cut set to **{percent}%**.")

    @lotteryset.command(name="draw")
    async def lotteryset_draw(self, ctx: commands.Context):
        """Force an immediate lottery draw."""
        cfg = await self._lottery_cfg(ctx.guild)
        if not cfg.get("tickets"):
            return await ctx.send("❌ No tickets have been sold yet — nothing to draw.")
        await ctx.send("📞 Calling the Den Den Mushi… drawing now!")
        winner = await self._run_lottery(ctx.guild, forced_by=ctx.author.display_name)
        if not winner:
            await ctx.send("❌ Draw failed — no tickets or pot was empty.")

    @lotteryset.command(name="test", aliases=["drawhere", "testdraw"])
    async def lotteryset_test(self, ctx: commands.Context):
        """Force a lottery draw announcement in the current channel."""
        cfg = await self._lottery_cfg(ctx.guild)
        if not cfg.get("tickets"):
            return await ctx.send("❌ No tickets have been sold yet — nothing to draw.")
        await ctx.send("📞 Calling the Den Den Mushi… drawing now in this channel!")
        winner = await self._run_lottery(
            ctx.guild,
            forced_by=ctx.author.display_name,
            announce_channel=ctx.channel,
        )
        if not winner:
            await ctx.send("❌ Draw failed — no tickets or pot was empty.")

    @lotteryset.command(name="reset")
    async def lotteryset_reset(self, ctx: commands.Context):
        """Cancel the current lottery and refund all ticket holders."""
        name, icon = await self._currency_fmt(ctx.guild)
        async with self.config.guild(ctx.guild).lottery() as cfg:
            tickets: dict = cfg.get("tickets", {})
            price = cfg.get("ticket_price", LOTTERY_DEFAULTS["ticket_price"])
            if not tickets:
                return await ctx.send("❌ No active lottery to reset.")
            refunded = 0
            for uid, count in tickets.items():
                member = ctx.guild.get_member(int(uid))
                if member:
                    amt = count * price
                    try:
                        await self._modify_balance(
                            ctx.guild, member, amt,
                            reason="lottery:refund",
                            actor=ctx.author,
                        )
                        refunded += 1
                    except RuntimeError:
                        pass
            cfg["tickets"] = {}
            cfg["pot"] = 0
        await ctx.send(f"✅ Lottery cancelled. Refunded **{refunded}** ticket holder(s).")
