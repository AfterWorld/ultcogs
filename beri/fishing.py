"""
Fishing minigame for the Beri economy cog.

Commands:
  [p]fish          — cast your line (cooldown scales with rod tier)
  [p]fishingrod    — check your current rod and upgrade options
  [p]buyrod <tier> — upgrade your fishing rod
  [p]fishdex       — view the full catch table with rarities
  [p]fishlog       — see your personal fishing stats

Rod tiers:
  driftwood (free) → bamboo → marine → yonko → seaking

Catch rarities (weighted):
  trash → common → uncommon → rare → epic → legendary
"""

import random
import datetime
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number

from .fruitbonuses import FISHING_FRUIT_BONUSES_BY_TYPE, FRUIT_COMMAND_BONUSES, LEGENDARY_ONLY_CATCHES

# ══════════════════════════════════════════════════════════════════════════════
# Rod data
# ══════════════════════════════════════════════════════════════════════════════

RODS = {
    "driftwood": {
        "label": "🪵 Driftwood Rod",
        "cost": 0,
        "cooldown": 120,          # seconds
        "bonus_weight": 0,        # flat bonus added to rare+ weights
        "description": "A sad stick with some string. Better than nothing.",
    },
    "bamboo": {
        "label": "🎋 Bamboo Rod",
        "cost": 2_000,
        "cooldown": 90,
        "bonus_weight": 5,
        "description": "Lightweight and reliable. A pirate's first real rod.",
    },
    "marine": {
        "label": "⚓ Marine-Issue Rod",
        "cost": 8_000,
        "cooldown": 60,
        "bonus_weight": 12,
        "description": "Confiscated from a Marine supply ship. Quality gear.",
    },
    "yonko": {
        "label": "👑 Yonko's Rod",
        "cost": 30_000,
        "cooldown": 45,
        "bonus_weight": 25,
        "description": "Rumored to have been used by an Emperor. Bends but never breaks.",
    },
    "seaking": {
        "label": "🐉 Sea King Slayer",
        "cost": 100_000,
        "cooldown": 30,
        "bonus_weight": 50,
        "description": "Forged from Sea King bone. Legendary catches only.",
    },
}

ROD_ORDER = ["driftwood", "bamboo", "marine", "yonko", "seaking"]

# ══════════════════════════════════════════════════════════════════════════════
# Fish / catch table
# Each entry: (display_name, emoji, rarity_label, base_weight, min_beri, max_beri, flavour)
# ══════════════════════════════════════════════════════════════════════════════

CATCHES = [
    # ── Trash ───────────────────────────────────────────────────────────────
    ("Old Boot",         "👢", "trash",      60,  0,    0,    "A soggy boot. Not even worth selling."),
    ("Broken Bottle",    "🍾", "trash",      50,  0,    0,    "Smells like cheap rum. Worth nothing."),
    ("Tangled Net",      "🕸️", "trash",      40,  0,    50,   "Someone else's problem, now yours."),

    # ── Common ──────────────────────────────────────────────────────────────
    ("Herring",          "🐟", "common",    120, 50,   200,  "A plain fish. At least it's something."),
    ("Mackerel",         "🐠", "common",    110, 80,   250,  "Decent eating. A fair catch."),
    ("Crab",             "🦀", "common",    100, 100,  300,  "Snapped at your fingers but you won."),
    ("Squid",            "🦑", "common",     90, 120,  320,  "Ink everywhere. Worth it though."),

    # ── Uncommon ────────────────────────────────────────────────────────────
    ("Tuna",             "🐡", "uncommon",   60, 350,  700,  "A solid haul — fresh enough for the market."),
    ("Lobster",          "🦞", "uncommon",   55, 400,  800,  "Big claws, bigger price tag."),
    ("Swordfish",        "⚔️", "uncommon",   50, 500,  900,  "Almost took your hand off. Almost."),
    ("Sea Bream",        "🐟", "uncommon",   45, 450,  850,  "Prized in East Blue markets."),

    # ── Rare ────────────────────────────────────────────────────────────────
    ("Oarfish",          "🐍", "rare",       20, 1_000, 2_500, "A deep-sea giant. Sailors call it an omen."),
    ("Giant Clam",       "🐚", "rare",       18, 1_200, 2_800, "Pried it open. A small pearl inside."),
    ("Mola Mola",        "🌊", "rare",       15, 1_500, 3_000, "Enormous and bizarre. A Grand Line specialty."),
    ("Electric Eel",     "⚡", "rare",       12, 1_800, 3_500, "Shocked you twice before you landed it."),

    # ── Epic ────────────────────────────────────────────────────────────────
    ("Knock Up Tuna",    "💨", "epic",        5, 4_000, 8_000,  "Launched itself out of a Knock Up Stream. Unreal."),
    ("Laboon's Sardine", "🐋", "epic",        4, 5_000, 9_000,  "Descended from the fish Laboon befriended."),
    ("Devil Eel",        "😈", "epic",        3, 6_000, 11_000, "Tasted a Devil Fruit once. That's your problem now."),
    ("Golden Coelacanth","✨", "epic",        2, 7_500, 12_000, "Ancient. Beautiful. Absolutely worth a fortune."),

    # ── Legendary ───────────────────────────────────────────────────────────
    ("Baby Sea King",    "🐉", "legendary",   1, 15_000, 30_000, "A juvenile Sea King. The crew is terrified. You're rich."),
    ("Neptunian Eel",    "🌊", "legendary",   1, 20_000, 40_000, "From the deepest trench of the All Blue. Mythical."),
    ("All Blue Phantom", "🌀", "legendary",   1, 25_000, 50_000, "A fish said to exist only in the All Blue. You found it."),
]

RARITY_COLORS = {
    "trash":      discord.Color.dark_gray(),
    "common":     discord.Color.light_gray(),
    "uncommon":   discord.Color.green(),
    "rare":       discord.Color.blue(),
    "epic":       discord.Color.purple(),
    "legendary":  discord.Color.gold(),
}

RARITY_ORDER = ["trash", "common", "uncommon", "rare", "epic", "legendary"]

# ══════════════════════════════════════════════════════════════════════════════
# Mixin
# ══════════════════════════════════════════════════════════════════════════════

class Fishing(commands.Cog):
    """
    Fishing minigame mixin. Expects parent (BeriCog) to expose:
      self.config
      self._get_balance(guild, member)
      self._safe_modify(ctx, guild, member, delta, *, reason, actor, metadata=None)
      self._currency_fmt(guild)
    """

    # ── Config helpers ────────────────────────────────────────────────────────

    _FISHING_DEFAULTS = {
        "rod": "driftwood",
        "last_fish": "",
        "total_casts": 0,
        "total_earned": 0,
        "catches": {},
        "best_catch": {},   # {} = no best catch yet; never None (breaks Red's nested_update)
    }

    async def _fishing_data(self, member: discord.Member) -> dict:
        """
        Load fishing data from a flat JSON string stored under 'fishing_json'.
        Bypasses Red's nested_update entirely, which chokes on None-valued nested keys.
        """
        import json
        raw = await self.config.member(member).fishing_json()
        if not raw:
            return dict(self._FISHING_DEFAULTS)
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            data = {}
        # Fill in any missing keys from defaults
        for k, v in self._FISHING_DEFAULTS.items():
            if k not in data:
                data[k] = v
        return data

    async def _save_fishing_data(self, member: discord.Member, data: dict):
        import json
        await self.config.member(member).fishing_json.set(json.dumps(data))

    def _rod_info(self, rod_key: str) -> dict:
        return RODS.get(rod_key, RODS["driftwood"])

    # ── Weighted catch roll ───────────────────────────────────────────────────

    def _roll_catch(self, bonus_weight: int, fruit_type: str):
        """
        Roll a random catch. bonus_weight is added to every rare+ entry's
        weight, nudging better rods toward richer catches.
        """
        fruit_bonus = FISHING_FRUIT_BONUSES_BY_TYPE.get(fruit_type, {})
        pool = []
        weights = []
        entries = list(CATCHES)
        if fruit_bonus.get("legendary_only_pool"):
            entries += LEGENDARY_ONLY_CATCHES

        for entry in entries:
            name, emoji, rarity, base_w, lo, hi, flavour = entry
            w = base_w
            if rarity in ("trash", "common"):
                w += fruit_bonus.get("trash_common_weight_delta", 0)
            if rarity in ("rare", "epic", "legendary"):
                w += bonus_weight
                w += fruit_bonus.get("rare_plus_weight", 0)
            if rarity in ("epic", "legendary"):
                w += fruit_bonus.get("epic_legendary_weight", 0)
            if rarity == "legendary":
                w += fruit_bonus.get("legendary_weight", 0)
            pool.append(entry)
            weights.append(max(1, w))
        return random.choices(pool, weights=weights, k=1)[0]

    # ══════════════════════════════════════════════════════════════════════════
    # Commands
    # ══════════════════════════════════════════════════════════════════════════

    @commands.command(name="fish", aliases=["cast", "fishing"])
    @commands.guild_only()
    async def fish(self, ctx: commands.Context):
        """Cast your line and see what the sea offers up."""
        name, icon = await self._currency_fmt(ctx.guild)
        data = await self._fishing_data(ctx.author)

        rod_key = data.get("rod", "driftwood")
        rod = self._rod_info(rod_key)
        fruit_info = await self._get_fruit_data(ctx.author)
        fruit_type = fruit_info.get("fruit_type", "")
        fruit_name = fruit_info.get("fruit_name", "")
        cooldown_secs = int(
            rod["cooldown"] *
            (1.0 - FISHING_FRUIT_BONUSES_BY_TYPE.get(fruit_type, {}).get("cooldown_reduce_pct", 0.0))
        )

        # Manual cooldown (per-rod)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        last_str = data.get("last_fish")
        if last_str:
            last = datetime.datetime.fromisoformat(last_str)
            elapsed = (now - last).total_seconds()
            if elapsed < cooldown_secs:
                remaining = int(cooldown_secs - elapsed)
                m, s = divmod(remaining, 60)
                time_str = f"{m}m {s}s" if m else f"{s}s"
                return await ctx.send(
                    f"🎣 Your line is still in the water! Try again in **{time_str}**."
                )

        # Include weather legendary weight bonus in roll
        weather_legendary = int(
            await self.get_weather_modifier(ctx.guild, "legendary_catch_weight", default=0)
        )
        # Roll the catch
        catch = self._roll_catch(rod["bonus_weight"] + weather_legendary, fruit_type)
        c_name, c_emoji, rarity, _, lo, hi, flavour = catch
        beri = random.randint(lo, hi) if hi > 0 else 0
        beri += FISHING_FRUIT_BONUSES_BY_TYPE.get(fruit_type, {}).get("flat_beri_bonus", 0)
        beri += int(beri * FRUIT_COMMAND_BONUSES.get(fruit_name, {}).get("all_activity_luck", 0.0))

        # Apply weather fishing multiplier
        fish_mult = await self.get_weather_modifier(ctx.guild, "fishing_multiplier")
        beri = int(beri * fish_mult)

        # Update stats
        data["last_fish"] = now.isoformat()
        data.setdefault("total_casts", 0)
        data.setdefault("total_earned", 0)
        data.setdefault("catches", {})
        data["total_casts"] += 1
        data["total_earned"] += beri
        data["catches"][c_name] = data["catches"].get(c_name, 0) + 1

        # Track best catch
        prev_best = data.get("best_catch") or {}
        if not prev_best.get("name") or beri > prev_best.get("beri", 0):
            data["best_catch"] = {"name": c_name, "beri": beri, "rarity": rarity}

        await self._save_fishing_data(ctx.author, data)

        # Pay out
        if beri > 0:
            new_bal = await self._safe_modify(
                ctx, ctx.guild, ctx.author, beri,
                reason=f"fishing:catch:{rarity}",
                actor="System",
                metadata={"fish": c_name, "rarity": rarity, "beri": beri},
            )
            if new_bal is None:
                return
        else:
            new_bal = await self._get_balance(ctx.guild, ctx.author)

        color = RARITY_COLORS.get(rarity, discord.Color.blurple())

        # Title drama by rarity
        titles = {
            "trash":     f"🎣 Nothing good...",
            "common":    f"🎣 A Catch!",
            "uncommon":  f"🎣 Nice Catch!",
            "rare":      f"🎣 Rare Catch! ✨",
            "epic":      f"🎣 EPIC CATCH! 🌟",
            "legendary": f"🎣 ⚡ LEGENDARY CATCH ⚡",
        }
        title = titles.get(rarity, "🎣 A Catch!")

        embed = discord.Embed(title=title, description=f"*{flavour}*", color=color)
        embed.add_field(name="Catch", value=f"{c_emoji} **{c_name}**", inline=True)
        embed.add_field(name="Rarity", value=rarity.capitalize(), inline=True)

        if beri > 0:
            embed.add_field(name="Value", value=f"**+{humanize_number(beri)}** {icon}", inline=True)
            embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        else:
            embed.add_field(name="Value", value="Worth nothing 🗑️", inline=True)

        embed.set_footer(
            text=f"{ctx.author.display_name} • {rod['label']} • Next cast in {cooldown_secs}s"
        )
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="fishingrod", aliases=["myrod", "rod"])
    @commands.guild_only()
    async def fishingrod(self, ctx: commands.Context):
        """Check your current fishing rod and see upgrade options."""
        name, icon = await self._currency_fmt(ctx.guild)
        data = await self._fishing_data(ctx.author)
        rod_key = data.get("rod", "driftwood")
        rod = self._rod_info(rod_key)

        embed = discord.Embed(
            title=f"🎣 {ctx.author.display_name}'s Fishing Rod",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Current Rod", value=rod["label"], inline=False)
        embed.add_field(name="Cooldown", value=f"{rod['cooldown']}s per cast", inline=True)
        embed.add_field(name="Rare Bonus", value=f"+{rod['bonus_weight']} weight", inline=True)
        embed.add_field(name="Description", value=rod["description"], inline=False)

        # Show next upgrade
        current_idx = ROD_ORDER.index(rod_key)
        if current_idx < len(ROD_ORDER) - 1:
            next_key = ROD_ORDER[current_idx + 1]
            next_rod = RODS[next_key]
            embed.add_field(
                name="⬆️ Next Upgrade",
                value=(
                    f"{next_rod['label']} — **{humanize_number(next_rod['cost'])}** {icon}\n"
                    f"Cooldown: {next_rod['cooldown']}s • Bonus: +{next_rod['bonus_weight']} weight\n"
                    f"Use `{ctx.prefix}buyrod {next_key}` to upgrade."
                ),
                inline=False,
            )
        else:
            embed.add_field(name="⬆️ Next Upgrade", value="You have the best rod in the seas!", inline=False)

        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="buyrod", aliases=["upgraderod", "rodupgrade"])
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def buyrod(self, ctx: commands.Context, tier: str):
        """
        Upgrade your fishing rod.

        Tiers: bamboo, marine, yonko, seaking
        """
        tier = tier.lower()
        if tier not in RODS:
            options = ", ".join(f"`{k}`" for k in ROD_ORDER[1:])
            return await ctx.send(f"❌ Unknown rod tier. Options: {options}")

        name, icon = await self._currency_fmt(ctx.guild)
        data = await self._fishing_data(ctx.author)
        current_key = data.get("rod", "driftwood")

        if ROD_ORDER.index(tier) <= ROD_ORDER.index(current_key):
            return await ctx.send(
                f"❌ You already have the **{self._rod_info(current_key)['label']}** "
                f"or better. You can only upgrade to a higher tier."
            )

        rod = RODS[tier]
        cost = rod["cost"]

        if cost == 0:
            return await ctx.send("❌ That rod is free and already available to everyone.")

        balance = await self._get_balance(ctx.guild, ctx.author)
        if balance < cost:
            return await ctx.send(
                f"❌ The **{rod['label']}** costs **{humanize_number(cost)}** {icon}. "
                f"You only have **{humanize_number(balance)}** {icon}."
            )

        new_bal = await self._safe_modify(
            ctx, ctx.guild, ctx.author, -cost,
            reason=f"fishing:buyrod:{tier}",
            actor=ctx.author,
        )
        if new_bal is None:
            return

        data["rod"] = tier
        await self._save_fishing_data(ctx.author, data)

        embed = discord.Embed(
            title=f"🎣 Rod Upgraded!",
            description=f"You are now the proud owner of a **{rod['label']}**.\n*{rod['description']}*",
            color=discord.Color.green(),
        )
        embed.add_field(name="Cost", value=f"**-{humanize_number(cost)}** {icon}", inline=True)
        embed.add_field(name="New Cooldown", value=f"{rod['cooldown']}s per cast", inline=True)
        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=ctx.author.display_name)
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="fishdex", aliases=["fishtable", "catchlist"])
    @commands.guild_only()
    async def fishdex(self, ctx: commands.Context):
        """View the full fishing catch table grouped by rarity."""
        name, icon = await self._currency_fmt(ctx.guild)
        embed = discord.Embed(
            title="🎣 Fishdex — Grand Line Catch Guide",
            color=discord.Color.blurple(),
        )

        for rarity in RARITY_ORDER:
            entries = [(c[0], c[1], c[4], c[5]) for c in CATCHES if c[2] == rarity]
            if not entries:
                continue
            lines = []
            for c_name, c_emoji, lo, hi in entries:
                if hi == 0:
                    val = "Worthless"
                else:
                    val = f"{humanize_number(lo)}–{humanize_number(hi)} {icon}"
                lines.append(f"{c_emoji} **{c_name}** — {val}")
            embed.add_field(
                name=f"{'⭐ ' if rarity == 'legendary' else ''}{rarity.capitalize()}",
                value="\n".join(lines),
                inline=False,
            )

        embed.set_footer(text=f"Better rods increase chances of rare+ catches. Use {ctx.prefix}buyrod to upgrade.")
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="fishlog", aliases=["fishstats", "myfish"])
    @commands.guild_only()
    async def fishlog(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """View your (or another user's) fishing statistics."""
        target = member or ctx.author
        name, icon = await self._currency_fmt(ctx.guild)
        data = await self._fishing_data(target)

        rod_key = data.get("rod", "driftwood")
        rod = self._rod_info(rod_key)
        total_casts = data.get("total_casts", 0)
        total_earned = data.get("total_earned", 0)
        catches: dict = data.get("catches", {})
        best = data.get("best_catch") or {}

        embed = discord.Embed(
            title=f"🎣 {target.display_name}'s Fishing Log",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Current Rod", value=rod["label"], inline=True)
        embed.add_field(name="Total Casts", value=humanize_number(total_casts), inline=True)
        embed.add_field(name="Total Earned", value=f"{humanize_number(total_earned)} {icon}", inline=True)

        if best.get("name"):
            embed.add_field(
                name="🏆 Best Catch",
                value=f"**{best['name']}** ({best['rarity'].capitalize()}) — {humanize_number(best['beri'])} {icon}",
                inline=False,
            )

        if catches:
            # Top 5 most-caught fish
            top = sorted(catches.items(), key=lambda x: x[1], reverse=True)[:5]
            lines = [f"**{fish}** × {humanize_number(count)}" for fish, count in top]
            embed.add_field(name="Most Caught", value="\n".join(lines), inline=False)

        if total_casts == 0:
            embed.description = "Never cast a line. Use `{prefix}fish` to get started!".format(prefix=ctx.prefix)

        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"Unique species caught: {len(catches)}")
        await ctx.send(embed=embed)

    # ── Error handler ─────────────────────────────────────────────────────────

    @buyrod.error
    async def _buyrod_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Cooldown — try again in **{int(error.retry_after)}s**.")
        else:
            raise error