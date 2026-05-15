"""
OnePieceFruit — a Red-DiscordBot companion cog for vertyco's LevelUp.

Assigns Devil Fruits at level 5, tracks awakenings at levels 15 and 30,
and lets users reroll using Beri (Red economy credits) at escalating costs.

MIT License — feel free to use and modify.
"""

from __future__ import annotations

import asyncio
import logging
import random
import typing as t
from pathlib import Path

import discord
from redbot.core import bank, commands
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path

from .fruits import (
    DEVIL_FRUITS,
    FRUIT_ASSIGN_LEVEL,
    AWAKENING_STAGE1_LEVEL,
    AWAKENING_STAGE2_LEVEL,
    RARITY_WEIGHTS,
    REROLL_COST_TABLE,
)
from .models import DB, GuildData, UserFruitData

log = logging.getLogger("red.onepiecefruit")

# ---------------------------------------------------------------------------
# Rarity colour palette for embeds
# ---------------------------------------------------------------------------
RARITY_COLOURS: dict[str, discord.Colour] = {
    "Paramecia":     discord.Colour.blue(),
    "Zoan":          discord.Colour.green(),
    "Logia":         discord.Colour.orange(),
    "Ancient Zoan":  discord.Colour.dark_gold(),
    "Mythical Zoan": discord.Colour.purple(),
    "Legendary":     discord.Colour.gold(),
}

RARITY_EMOJIS: dict[str, str] = {
    "Paramecia":     "🔵",
    "Zoan":          "🟢",
    "Logia":         "🟠",
    "Ancient Zoan":  "🟤",
    "Mythical Zoan": "🟣",
    "Legendary":     "⭐",
}

AWAKENING_LABELS = {0: "Base Form", 1: "Awakening — Stage 1", 2: "Full Awakening"}


# ---------------------------------------------------------------------------
# Helper — weighted random fruit draw
# ---------------------------------------------------------------------------
def _draw_fruit() -> tuple[str, dict]:
    """Return (rarity_type, fruit_dict) using RARITY_WEIGHTS."""
    types = list(RARITY_WEIGHTS.keys())
    weights = [RARITY_WEIGHTS[t] for t in types]
    chosen_type = random.choices(types, weights=weights, k=1)[0]
    chosen_fruit = random.choice(DEVIL_FRUITS[chosen_type])
    return chosen_type, chosen_fruit


def _next_reroll_cost(reroll_count: int) -> int:
    idx = min(reroll_count, len(REROLL_COST_TABLE) - 1)
    return REROLL_COST_TABLE[idx]


def _build_fruit_embed(
    member: discord.Member,
    data: UserFruitData,
    *,
    title_prefix: str = "",
) -> discord.Embed:
    """Build a Discord embed showing a user's Devil Fruit status."""
    rarity = data.fruit_type
    colour = RARITY_COLOURS.get(rarity, discord.Colour.blurple())
    emoji = RARITY_EMOJIS.get(rarity, "❓")
    stage_label = AWAKENING_LABELS.get(data.awakening_stage, "Base Form")

    # Pick the right ability description
    # Find the fruit dict by name
    fruit_dict = None
    for fruit in DEVIL_FRUITS.get(rarity, []):
        if fruit["name"] == data.fruit_name:
            fruit_dict = fruit
            break

    if fruit_dict is None:
        ability_text = "*Unknown ability.*"
    elif data.awakening_stage == 2:
        ability_text = fruit_dict["awakening_2"]
    elif data.awakening_stage == 1:
        ability_text = fruit_dict["awakening_1"]
    else:
        ability_text = fruit_dict["ability"]

    title = f"{title_prefix}{emoji} {data.fruit_name}" if title_prefix else f"{emoji} {data.fruit_name}"

    embed = discord.Embed(title=title, colour=colour)
    embed.set_author(
        name=f"{member.display_name}'s Devil Fruit",
        icon_url=member.display_avatar.url,
    )
    embed.add_field(name="Type", value=f"**{rarity}**", inline=True)
    embed.add_field(name="Stage", value=f"**{stage_label}**", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="Power", value=ability_text, inline=False)

    if data.awakening_stage < 2:
        next_lvl = AWAKENING_STAGE2_LEVEL if data.awakening_stage == 1 else AWAKENING_STAGE1_LEVEL
        embed.set_footer(text=f"Next awakening unlocks at Level {next_lvl}.")
    else:
        embed.set_footer(text="Your fruit has reached its full awakening. ⭐")

    return embed


# ===========================================================================
# Main Cog
# ===========================================================================
class OnePieceFruit(commands.Cog):
    """
    One Piece Devil Fruit companion cog for LevelUp.

    Assigns Devil Fruits at level 5, tracks awakenings at 15 and 30,
    and lets users reroll using Beri (Red economy) at escalating costs.
    """

    __author__ = "your-name-here"
    __version__ = "1.0.0"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.db = DB()
        self._io_lock = asyncio.Lock()
        self._settings_file: t.Optional[Path] = None

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------
    async def cog_load(self) -> None:
        self._settings_file = cog_data_path(self) / "onepiecefruit.json"
        if self._settings_file.exists():
            try:
                self.db = await asyncio.to_thread(DB.from_file, self._settings_file)
                log.info("OnePieceFruit: config loaded.")
            except Exception as exc:
                log.error("OnePieceFruit: failed to load config.", exc_info=exc)

    async def cog_unload(self) -> None:
        await self._save()

    # -----------------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------------
    async def _save(self) -> None:
        if self._settings_file is None:
            return
        async with self._io_lock:
            try:
                await asyncio.to_thread(self.db.to_file, self._settings_file)
            except Exception as exc:
                log.error("OnePieceFruit: failed to save config.", exc_info=exc)

    # -----------------------------------------------------------------------
    # LevelUp event hook
    # -----------------------------------------------------------------------
    @commands.Cog.listener("on_levelup")
    async def on_levelup(
        self,
        guild: discord.Guild,
        member: discord.Member,
        level: int,
        channel: t.Optional[discord.TextChannel],
    ) -> None:
        """
        Fired by vertyco's LevelUp cog via bot.dispatch('levelup', guild, member, level, channel).

        Handles:
        - Level 5:  Assign a random Devil Fruit
        - Level 15: Stage 1 Awakening
        - Level 30: Full Awakening
        """
        if level < FRUIT_ASSIGN_LEVEL:
            return

        guild_data = self.db.get_guild(guild.id)
        user_data = guild_data.get_user(member.id)

        # ── Level 5: first fruit assignment ──────────────────────────────
        if level == FRUIT_ASSIGN_LEVEL and user_data is None:
            rarity, fruit = _draw_fruit()
            user_data = UserFruitData(
                fruit_name=fruit["name"],
                fruit_type=rarity,
                assigned_at_level=level,
                awakening_stage=0,
            )
            guild_data.set_user(member.id, user_data)
            await self._save()

            embed = _build_fruit_embed(member, user_data, title_prefix="🍎 Devil Fruit Obtained! ")
            embed.description = (
                f"Congratulations {member.mention}! You've eaten a **Devil Fruit** and gained a mysterious power!\n"
                f"You can never swim again — but the power is worth it. 💀"
            )
            if channel:
                await channel.send(embed=embed)
            else:
                with suppress(discord.HTTPException):
                    await member.send(embed=embed)
            return

        # ── Level 15: Stage 1 Awakening ──────────────────────────────────
        if level == AWAKENING_STAGE1_LEVEL and user_data is not None and user_data.awakening_stage == 0:
            user_data.awakening_stage = 1
            guild_data.set_user(member.id, user_data)
            await self._save()

            embed = _build_fruit_embed(member, user_data, title_prefix="⚡ Awakening — Stage 1! ")
            embed.description = (
                f"{member.mention}, your Devil Fruit stirs with new power!\n"
                f"**Stage 1 Awakening** has been unlocked. Your abilities grow beyond their base form."
            )
            if channel:
                await channel.send(embed=embed)
            return

        # ── Level 30: Full Awakening ──────────────────────────────────────
        if level == AWAKENING_STAGE2_LEVEL and user_data is not None and user_data.awakening_stage == 1:
            user_data.awakening_stage = 2
            guild_data.set_user(member.id, user_data)
            await self._save()

            embed = _build_fruit_embed(member, user_data, title_prefix="🌟 Full Awakening! ")
            embed.description = (
                f"**{member.mention} — FULL AWAKENING ACHIEVED!**\n\n"
                f"Your Devil Fruit has reached its ultimate form. You stand among the greatest powers in the world."
            )
            if channel:
                await channel.send(embed=embed)
            return

    # -----------------------------------------------------------------------
    # Commands
    # -----------------------------------------------------------------------
    @commands.group(name="devilfruit", aliases=["df"])
    @commands.guild_only()
    async def devilfruit(self, ctx: commands.Context) -> None:
        """Devil Fruit commands."""

    # ── [p]df info ──────────────────────────────────────────────────────────
    @devilfruit.command(name="info", aliases=["check", "fruit"])
    async def df_info(self, ctx: commands.Context, member: t.Optional[discord.Member] = None) -> None:
        """Show your (or another member's) Devil Fruit."""
        target = member or ctx.author
        guild_data = self.db.get_guild(ctx.guild.id)
        user_data = guild_data.get_user(target.id)

        if user_data is None or not user_data.fruit_name:
            who = "You haven't" if target == ctx.author else f"{target.display_name} hasn't"
            await ctx.send(f"🌊 {who} eaten a Devil Fruit yet. Reach **Level {FRUIT_ASSIGN_LEVEL}** to receive one!")
            return

        embed = _build_fruit_embed(target, user_data)
        await ctx.send(embed=embed)

    # ── [p]df reroll ────────────────────────────────────────────────────────
    @devilfruit.command(name="reroll", aliases=["change", "new"])
    async def df_reroll(self, ctx: commands.Context) -> None:
        """
        Reroll your Devil Fruit for Beri.

        Cost increases with each reroll:
        1st → 10,000 ⬩ 2nd → 25,000 ⬩ 3rd → 50,000 ⬩ 4th+ → 100,000
        """
        guild_data = self.db.get_guild(ctx.guild.id)
        user_data = guild_data.get_user(ctx.author.id)

        if user_data is None or not user_data.fruit_name:
            return await ctx.send(
                f"🌊 You haven't eaten a Devil Fruit yet. Reach **Level {FRUIT_ASSIGN_LEVEL}** first!"
            )

        cost = _next_reroll_cost(user_data.reroll_count)
        currency_name = await bank.get_currency_name(ctx.guild)

        # Confirm
        confirm_msg = await ctx.send(
            f"⚠️ Rerolling your Devil Fruit costs **{cost:,} {currency_name}**.\n"
            f"Your current fruit (**{user_data.fruit_name}**) will be **permanently lost**.\n"
            f"React with ✅ to confirm, or ❌ to cancel."
        )
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return (
                user == ctx.author
                and str(reaction.emoji) in ("✅", "❌")
                and reaction.message.id == confirm_msg.id
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("⏰ Reroll cancelled — timed out.")

        if str(reaction.emoji) == "❌":
            return await ctx.send("❌ Reroll cancelled.")

        # Check balance
        try:
            await bank.withdraw_credits(ctx.author, cost)
        except ValueError:
            balance = await bank.get_balance(ctx.author)
            return await ctx.send(
                f"💸 You don't have enough {currency_name}! "
                f"You need **{cost:,}** but only have **{balance:,}**."
            )

        # Draw new fruit (guaranteed different type if possible)
        old_type = user_data.fruit_type
        for _ in range(10):
            rarity, fruit = _draw_fruit()
            if fruit["name"] != user_data.fruit_name:
                break

        user_data.fruit_name = fruit["name"]
        user_data.fruit_type = rarity
        user_data.awakening_stage = 0   # reset awakening on reroll
        user_data.reroll_count += 1
        user_data.last_reroll_cost = cost
        guild_data.set_user(ctx.author.id, user_data)
        await self._save()

        embed = _build_fruit_embed(ctx.author, user_data, title_prefix="🍎 New Fruit! ")
        embed.description = (
            f"You spent **{cost:,} {currency_name}** and ate a new Devil Fruit!\n"
            f"*Your previous {old_type} fruit is gone forever...*"
        )

        next_cost = _next_reroll_cost(user_data.reroll_count)
        embed.set_footer(text=f"Next reroll will cost {next_cost:,} {currency_name}.")
        await ctx.send(embed=embed)

    # ── [p]df list ──────────────────────────────────────────────────────────
    @devilfruit.command(name="list", aliases=["leaderboard", "lb"])
    async def df_list(self, ctx: commands.Context) -> None:
        """Show all Devil Fruit users in the server."""
        guild_data = self.db.get_guild(ctx.guild.id)

        if not guild_data.users:
            return await ctx.send("🌊 No one has eaten a Devil Fruit yet in this server!")

        lines: list[str] = []
        for uid_str, udata in guild_data.users.items():
            if not udata.fruit_name:
                continue
            member = ctx.guild.get_member(int(uid_str))
            name = member.display_name if member else f"User {uid_str}"
            emoji = RARITY_EMOJIS.get(udata.fruit_type, "❓")
            stage = ["", " ⚡", " 🌟"][udata.awakening_stage]
            lines.append(f"{emoji} **{name}** — {udata.fruit_name}{stage}")

        if not lines:
            return await ctx.send("🌊 No active Devil Fruit users found.")

        # Paginate naively if long
        chunk_size = 15
        pages = [lines[i : i + chunk_size] for i in range(0, len(lines), chunk_size)]

        for i, page in enumerate(pages):
            embed = discord.Embed(
                title=f"🍎 Devil Fruit Users — {ctx.guild.name}",
                description="\n".join(page),
                colour=discord.Colour.dark_red(),
            )
            if len(pages) > 1:
                embed.set_footer(text=f"Page {i + 1}/{len(pages)}")
            await ctx.send(embed=embed)

    # ── [p]df types ─────────────────────────────────────────────────────────
    @devilfruit.command(name="types")
    async def df_types(self, ctx: commands.Context) -> None:
        """Show Devil Fruit rarity tiers and drop weights."""
        embed = discord.Embed(title="🍎 Devil Fruit Rarity Tiers", colour=discord.Colour.dark_red())
        for rarity, weight in RARITY_WEIGHTS.items():
            emoji = RARITY_EMOJIS.get(rarity, "❓")
            count = len(DEVIL_FRUITS.get(rarity, []))
            embed.add_field(
                name=f"{emoji} {rarity}",
                value=f"Drop chance: **{weight}%** | {count} fruits",
                inline=False,
            )
        await ctx.send(embed=embed)

    # ── Admin: [p]df admin assign ────────────────────────────────────────────
    @devilfruit.group(name="admin")
    @commands.admin_or_permissions(administrator=True)
    async def df_admin(self, ctx: commands.Context) -> None:
        """Admin Devil Fruit management."""

    @df_admin.command(name="assign")
    async def df_admin_assign(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        fruit_name: t.Optional[str] = None,
    ) -> None:
        """
        Assign (or randomly assign) a Devil Fruit to a member.

        If fruit_name is omitted, a random fruit is drawn.
        Use the exact fruit name from [p]df browse to assign a specific one.
        """
        guild_data = self.db.get_guild(ctx.guild.id)

        if fruit_name:
            # Search by name (case-insensitive partial match)
            found_type, found_fruit = None, None
            for rarity, fruits in DEVIL_FRUITS.items():
                for f in fruits:
                    if fruit_name.lower() in f["name"].lower():
                        found_type, found_fruit = rarity, f
                        break
                if found_fruit:
                    break
            if found_fruit is None:
                return await ctx.send(f"❌ No fruit found matching `{fruit_name}`. Check `[p]df browse`.")
            rarity, fruit = found_type, found_fruit
        else:
            rarity, fruit = _draw_fruit()

        user_data = UserFruitData(
            fruit_name=fruit["name"],
            fruit_type=rarity,
            assigned_at_level=0,
            awakening_stage=0,
        )
        guild_data.set_user(member.id, user_data)
        await self._save()

        embed = _build_fruit_embed(member, user_data, title_prefix="🍎 Admin Assigned: ")
        await ctx.send(embed=embed)

    @df_admin.command(name="reset")
    async def df_admin_reset(self, ctx: commands.Context, member: discord.Member) -> None:
        """Remove a member's Devil Fruit data entirely."""
        guild_data = self.db.get_guild(ctx.guild.id)
        guild_data.remove_user(member.id)
        await self._save()
        await ctx.send(f"🗑️ Devil Fruit data cleared for **{member.display_name}**.")

    @df_admin.command(name="awaken")
    async def df_admin_awaken(
        self,
        ctx: commands.Context,
        member: discord.Member,
        stage: int,
    ) -> None:
        """Manually set a member's awakening stage (0, 1, or 2)."""
        if stage not in (0, 1, 2):
            return await ctx.send("❌ Stage must be 0 (base), 1 (stage 1), or 2 (full).")

        guild_data = self.db.get_guild(ctx.guild.id)
        user_data = guild_data.get_user(member.id)
        if user_data is None:
            return await ctx.send(f"❌ {member.display_name} has no Devil Fruit assigned.")

        user_data.awakening_stage = stage
        guild_data.set_user(member.id, user_data)
        await self._save()

        label = AWAKENING_LABELS[stage]
        await ctx.send(f"✅ Set **{member.display_name}**'s awakening to **{label}**.")

    @df_admin.command(name="resetrerolls")
    async def df_admin_reset_rerolls(self, ctx: commands.Context, member: discord.Member) -> None:
        """Reset a member's reroll counter to 0 (resets cost back to 10,000)."""
        guild_data = self.db.get_guild(ctx.guild.id)
        user_data = guild_data.get_user(member.id)
        if user_data is None:
            return await ctx.send(f"❌ {member.display_name} has no Devil Fruit data.")
        user_data.reroll_count = 0
        user_data.last_reroll_cost = 0
        guild_data.set_user(member.id, user_data)
        await self._save()
        await ctx.send(f"✅ Reset reroll counter for **{member.display_name}**.")

    # ── [p]df browse ────────────────────────────────────────────────────────
    @devilfruit.command(name="browse")
    async def df_browse(self, ctx: commands.Context, rarity: t.Optional[str] = None) -> None:
        """
        Browse available Devil Fruits by rarity.

        Usage: [p]df browse [Paramecia|Zoan|Logia|Ancient Zoan|Mythical Zoan|Legendary]
        """
        valid = list(DEVIL_FRUITS.keys())

        if rarity is None:
            embed = discord.Embed(
                title="🍎 Available Devil Fruit Types",
                description="Use `[p]df browse <type>` to see fruits in a category.\n\n"
                + "\n".join(f"{RARITY_EMOJIS[r]} **{r}** — {len(DEVIL_FRUITS[r])} fruits" for r in valid),
                colour=discord.Colour.dark_red(),
            )
            return await ctx.send(embed=embed)

        # Fuzzy match rarity
        matched = next((r for r in valid if r.lower() == rarity.lower()), None)
        if matched is None:
            return await ctx.send(
                f"❌ Unknown rarity `{rarity}`. Valid options: {', '.join(valid)}"
            )

        fruits = DEVIL_FRUITS[matched]
        emoji = RARITY_EMOJIS[matched]
        lines = [f"• {f['name']}" for f in fruits]

        embed = discord.Embed(
            title=f"{emoji} {matched} Fruits ({len(fruits)} total)",
            description="\n".join(lines),
            colour=RARITY_COLOURS[matched],
        )
        embed.set_footer(text=f"Drop chance: {RARITY_WEIGHTS[matched]}%")
        await ctx.send(embed=embed)

    # ── Format help ──────────────────────────────────────────────────────────
    def format_help_for_context(self, ctx: commands.Context) -> str:
        base = super().format_help_for_context(ctx)
        return f"{base}\nVersion: {self.__version__}\nAuthor: {self.__author__}"


# ---------------------------------------------------------------------------
# Red cog setup
# ---------------------------------------------------------------------------
async def setup(bot: Red) -> None:
    await bot.add_cog(OnePieceFruit(bot))
