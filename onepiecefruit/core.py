"""
OnePieceFruit — a Red-DiscordBot companion cog for vertyco's LevelUp.

Assigns Devil Fruits at level 5, tracks awakenings at levels 50 and 100,
and lets users reroll using Beri (Red economy credits) at unlimited but
ever-escalating costs.

Includes Pirate Rep system (piraterep.py):
  - Tracks total messages, weekly activity, daily streaks, and rep points.
  - Appends rep fields to [p]df info embeds.
  - New commands: [p]df rep, [p]df weekly, [p]df streak.

MIT License — feel free to use and modify.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import typing as t
from contextlib import suppress
from pathlib import Path

import discord
from redbot.core import bank, commands, Config
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path

from .fruits import (
    DEVIL_FRUITS,
    FRUIT_ASSIGN_LEVEL,
    AWAKENING_STAGE1_LEVEL,
    AWAKENING_STAGE2_LEVEL,
    RARITY_WEIGHTS,
    REROLL_COST_TABLE,
    REROLL_COST_SCALE_FACTOR,
    SEASONAL_EVENTS,
)
from .models import DB, GuildData, UserFruitData
from .piraterep import RepTracker  # ← Pirate Rep integration

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
def _draw_fruit(event: t.Optional[str] = None) -> tuple[str, dict]:
    """Return (rarity_type, fruit_dict), using a seasonal event pool when active."""
    if event:
        event_info = SEASONAL_EVENTS.get(event.lower())
        if event_info and event_info["fruits"]:
            chosen_fruit = random.choice(event_info["fruits"])
            return chosen_fruit["fruit_type"], chosen_fruit

    types = list(RARITY_WEIGHTS.keys())
    weights = [RARITY_WEIGHTS[t] for t in types]
    chosen_type = random.choices(types, weights=weights, k=1)[0]
    chosen_fruit = random.choice(DEVIL_FRUITS[chosen_type])
    return chosen_type, chosen_fruit


def _next_reroll_cost(reroll_count: int) -> int:
    table_len = len(REROLL_COST_TABLE)
    if reroll_count < table_len:
        return REROLL_COST_TABLE[reroll_count]
    extra = reroll_count - (table_len - 1)
    base = REROLL_COST_TABLE[-1]
    return int(math.floor(base * (REROLL_COST_SCALE_FACTOR ** extra)))


def _build_fruit_embed(
    member: discord.Member,
    data: UserFruitData,
    *,
    title_prefix: str = "",
    rep_tracker: t.Optional[RepTracker] = None,
) -> discord.Embed:
    """
    Build a Discord embed showing a user's Devil Fruit status.

    If rep_tracker is provided (for the [p]df info command), Pirate Rep
    fields are appended automatically.
    """
    rarity = data.fruit_type
    colour = RARITY_COLOURS.get(rarity, discord.Colour.blurple())
    emoji = RARITY_EMOJIS.get(rarity, "❓")
    stage_label = AWAKENING_LABELS.get(data.awakening_stage, "Base Form")

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
    embed.add_field(
        name="Reroll Info",
        value=(
            f"**{data.reroll_count}** reroll{'s' if data.reroll_count != 1 else ''}\n"
            f"Next cost: **{_next_reroll_cost(data.reroll_count):,}**"
        ),
        inline=False,
    )

    # ── Pirate Rep section ──────────────────────────────────────────────────
    if rep_tracker is not None and member.guild is not None:
        for name, value, inline in rep_tracker.rep_embed_fields(member.guild.id, member.id):
            embed.add_field(name=name, value=value, inline=inline)

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

    Assigns Devil Fruits at level 5, tracks awakenings at 50 and 100,
    and lets users reroll using Beri (Red economy) with no reroll cap —
    but costs escalate significantly with each attempt.

    Also tracks Pirate Rep: message activity, daily streaks, weekly standings,
    and a rank ladder from Cabin Boy to Yonko.
    """

    __author__ = "UltPanda"
    __version__ = "1.2.0"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.db = DB()
        self._io_lock = asyncio.Lock()
        self._settings_file: t.Optional[Path] = None
        self.rep_tracker: t.Optional[RepTracker] = None  # initialised in cog_load

        self.config = Config.get_conf(self, identifier=0x99ac92bc1d2e3f44, force_registration=True)
        self.config.register_guild(rank_announcement_channel=None, active_event=None)

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------
    async def cog_load(self) -> None:
        data_path = cog_data_path(self)

        # Devil Fruit DB
        self._settings_file = data_path / "onepiecefruit.json"
        if self._settings_file.exists():
            try:
                self.db = await asyncio.to_thread(DB.from_file, self._settings_file)
                log.info("OnePieceFruit: config loaded.")
            except Exception as exc:
                log.error("OnePieceFruit: failed to load config.", exc_info=exc)

        # Pirate Rep tracker
        self.rep_tracker = RepTracker(data_path / "piraterep.json")
        await self.rep_tracker.load()

    async def cog_unload(self) -> None:
        await self._save()
        if self.rep_tracker:
            await self.rep_tracker.save()

    # -----------------------------------------------------------------------
    # Persistence — Devil Fruit DB
    # -----------------------------------------------------------------------
    async def _save(self) -> None:
        if self._settings_file is None:
            return
        async with self._io_lock:
            try:
                await asyncio.to_thread(self.db.to_file, self._settings_file)
            except Exception as exc:
                log.error("OnePieceFruit: failed to save config.", exc_info=exc)

    def _bericog(self) -> t.Optional[object]:
        return self.bot.get_cog("BeriCog")

    def _bericore(self) -> t.Optional[object]:
        return self.bot.get_cog("BeriCore")

    async def _get_currency_name(self, guild: discord.Guild) -> str:
        beri_core = self._bericore()
        if beri_core is not None:
            return "Beri"
        beri = self._bericog()
        if beri is not None:
            return (await beri._currency_fmt(guild))[0]
        return await bank.get_currency_name(guild)

    async def _get_balance(self, guild: discord.Guild, member: discord.Member) -> int:
        beri_core = self._bericore()
        if beri_core is not None:
            return await beri_core.get_beri(member)
        beri = self._bericog()
        if beri is not None:
            return await beri._get_balance(guild, member)
        return await bank.get_balance(member)

    async def _withdraw_currency(self, ctx: commands.Context, member: discord.Member, amount: int) -> int:
        beri_core = self._bericore()
        if beri_core is not None:
            balance = await beri_core.get_beri(member)
            if balance < amount:
                raise ValueError("Insufficient funds")
            return await beri_core.add_beri(
                member,
                -amount,
                reason="devilfruit:reroll",
                actor=ctx.author or "System",
            )
        beri = self._bericog()
        if beri is not None:
            balance = await beri._get_balance(ctx.guild, member)
            if balance < amount:
                raise ValueError("Insufficient funds")
            return await beri._modify_balance(
                ctx.guild,
                member,
                -amount,
                reason="devilfruit:reroll",
                actor=ctx.author or "System",
            )
        return await bank.withdraw_credits(member, amount)

    async def _modify_currency(
        self,
        member: discord.Member,
        amount: int,
        guild: t.Optional[discord.Guild] = None,
        actor: t.Union[discord.Member, str] = "System",
        reason: str = "devilfruit:perk",
    ) -> int:
        beri_core = self._bericore()
        if beri_core is not None:
            return await beri_core.add_beri(member, amount, reason=reason, actor=actor)

        beri = self._bericog()
        if beri is not None and guild is not None:
            return await beri._modify_balance(guild, member, amount, reason=reason, actor=actor)

        if amount >= 0:
            return await bank.deposit_credits(member, amount)
        return await bank.withdraw_credits(member, -amount)

    def _reroll_cost_multiplier(self, rarity: str) -> float:
        return {
            "Paramecia": 0.90,
            "Zoan": 0.95,
            "Legendary": 0.90,
        }.get(rarity, 1.0)

    def _daily_stipend_amount(self, rarity: str) -> int:
        return {
            "Logia": 150,
            "Mythical Zoan": 100,
            "Legendary": 250,
        }.get(rarity, 0)

    async def _maybe_grant_daily_stipend(self, message: discord.Message) -> None:
        if message.guild is None or self.db is None:
            return
        guild_data = self.db.get_guild(message.guild.id)
        user_data = guild_data.get_user(message.author.id)
        if user_data is None or not user_data.fruit_name:
            return

        amount = self._daily_stipend_amount(user_data.fruit_type)
        if amount <= 0:
            return

        today = _utc_today().isoformat()
        if user_data.last_daily_stipend == today:
            return

        try:
            await self._modify_currency(
                message.author,
                amount,
                guild=message.guild,
                actor=message.author,
                reason="devilfruit:daily_stipend",
            )
        except Exception:
            return

        user_data.last_daily_stipend = today
        guild_data.set_user(message.author.id, user_data)
        await self._save()

        with suppress(discord.HTTPException):
            await message.channel.send(
                f"✨ {message.author.mention}, your {user_data.fruit_type} Devil Fruit grants you a daily Beri stipend of **{amount:,} Beri**!"
            )

    async def _send_paginated_embed(
        self,
        ctx: commands.Context,
        title: str,
        lines: list[str],
        colour: discord.Colour,
        footer: str,
        max_per_page: int = 15,
    ) -> None:
        page_chunks = [lines[i : i + max_per_page] for i in range(0, len(lines), max_per_page)]
        total_pages = len(page_chunks)
        total_items = len(lines)

        def make_embed(page_idx: int) -> discord.Embed:
            embed = discord.Embed(
                title=title,
                description="\n".join(page_chunks[page_idx]),
                colour=colour,
            )
            embed.set_footer(text=f"{footer} • Page {page_idx + 1}/{total_pages}")
            return embed

        if total_pages == 1:
            return await ctx.send(embed=make_embed(0))

        current = 0
        msg = await ctx.send(embed=make_embed(current))
        controls = ["⬅️", "➡️", "❌"]
        for emoji in controls:
            await msg.add_reaction(emoji)

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return (
                user == ctx.author
                and reaction.message.id == msg.id
                and str(reaction.emoji) in controls
            )

        while True:
            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                with suppress(discord.HTTPException):
                    await msg.clear_reactions()
                break

            emoji_str = str(reaction.emoji)
            if emoji_str == "❌":
                with suppress(discord.HTTPException):
                    await msg.clear_reactions()
                break
            elif emoji_str == "⬅️":
                current = (current - 1) % total_pages
            elif emoji_str == "➡️":
                current = (current + 1) % total_pages

            with suppress(discord.HTTPException):
                await msg.edit(embed=make_embed(current))
                await msg.remove_reaction(reaction, ctx.author)

    async def _rank_announcement_channel(self, guild: discord.Guild) -> t.Optional[int]:
        return await self.config.guild(guild).rank_announcement_channel()

    async def _get_active_event(self, guild: discord.Guild) -> t.Optional[str]:
        return await self.config.guild(guild).active_event()

    def _event_label(self, event_key: str) -> str:
        event_def = SEASONAL_EVENTS.get(event_key.lower())
        if event_def:
            return f"{event_def['emoji']} {event_def['name']}"
        return event_key

    async def _send_rank_announcement(
        self,
        guild: discord.Guild,
        member: discord.Member,
        old_title: str,
        old_emoji: str,
        new_title: str,
        new_emoji: str,
        rep: int,
    ) -> None:
        channel_id = await self._rank_announcement_channel(guild)
        if channel_id is None:
            return

        channel = guild.get_channel(channel_id)
        if channel is None:
            return

        embed = discord.Embed(
            title="🏴‍☠️ Pirate Rank Up!",
            description=(
                f"{member.mention} has advanced from **{old_title}** {old_emoji}"
                f" to **{new_title}** {new_emoji}!"
            ),
            colour=discord.Colour.gold(),
        )
        embed.add_field(name="New Rank", value=f"{new_emoji} {new_title}", inline=True)
        embed.add_field(name="Total Rep", value=f"**{rep:,}** rep", inline=True)
        embed.set_footer(text="Keep chatting to climb the ranks!")

        with suppress(discord.HTTPException):
            await channel.send(embed=embed)

    async def _process_rep_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None or self.rep_tracker is None:
            return

        result = await self.rep_tracker.record_message(message.guild.id, message.author.id)
        if result is None:
            await self._maybe_grant_daily_stipend(message)
            return

        promotion, decay_amount, decay_days = result
        if decay_amount > 0:
            with suppress(discord.HTTPException):
                await message.channel.send(
                    f"💨 {message.author.mention}, your Pirate Rep decayed by **{decay_amount:,}** "
                    f"after {decay_days} days of inactivity. Keep chatting to recover!"
                )

        if promotion is not None:
            old_title, old_emoji, new_title, new_emoji, rep = promotion
            await self._send_rank_announcement(
                message.guild,
                message.author,
                old_title,
                old_emoji,
                new_title,
                new_emoji,
                rep,
            )

        await self._maybe_grant_daily_stipend(message)

    async def _resolve_profile_target(self, ctx: commands.Context) -> discord.Member:
        target = ctx.kwargs.get("member")
        if isinstance(target, discord.Member):
            return target

        if ctx.guild is None:
            return ctx.author

        if ctx.message and ctx.message.content:
            parts = ctx.message.content.strip().split()
            if len(parts) > 1:
                query = " ".join(parts[1:])
                try:
                    return await commands.MemberConverter().convert(ctx, query)
                except Exception:
                    query_lower = query.lower()
                    for member in ctx.guild.members:
                        if member.display_name.lower() == query_lower or member.name.lower() == query_lower:
                            return member

        return ctx.author

    # -----------------------------------------------------------------------
    # Message tracking → Pirate Rep
    # -----------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Record every non-bot guild message for Pirate Rep tracking."""
        if message.author.bot or message.guild is None:
            return
        if self.rep_tracker is None:
            return
        # Fire-and-forget; save is debounced inside RepTracker
        asyncio.create_task(self._process_rep_message(message))

    # -----------------------------------------------------------------------
    # Profile command hook — append Devil Fruit embed after [p]profile / [p]pf
    # -----------------------------------------------------------------------
    @commands.Cog.listener("on_command_completion")
    async def on_command_completion(self, ctx: commands.Context) -> None:
        """
        After a LevelUp profile command completes, send the user's Devil Fruit
        card into the same channel as a follow-up embed.
        """
        if ctx.command is None or ctx.guild is None:
            return

        cmd_name = ctx.command.qualified_name.lower()
        profile_names = {"profile", "pf"}

        if not (cmd_name in profile_names or cmd_name.endswith(" profile") or cmd_name.endswith(" pf")):
            return

        if ctx.command.cog is None or "levelup" not in type(ctx.command.cog).__name__.lower():
            return

        target = await self._resolve_profile_target(ctx)
        if not isinstance(target, discord.Member):
            target = ctx.author

        guild_data = self.db.get_guild(ctx.guild.id)
        user_data = guild_data.get_user(target.id)

        if user_data is None or not user_data.fruit_name or not user_data.profile_visible:
            return

        embed = _build_fruit_embed(target, user_data, rep_tracker=self.rep_tracker)
        footer_text = embed.footer.text or ""
        embed.set_footer(text=f"🍎 Devil Fruit  •  {footer_text}" if footer_text else "🍎 Devil Fruit")

        with suppress(discord.HTTPException):
            await ctx.send(embed=embed)

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
        """Fired by LevelUp cog. Handles fruit assignment and awakenings."""
        if level < FRUIT_ASSIGN_LEVEL:
            return

        guild_data = self.db.get_guild(guild.id)
        user_data = guild_data.get_user(member.id)

        # ── Level 5: first fruit assignment ──────────────────────────────
        if level == FRUIT_ASSIGN_LEVEL and user_data is None:
            active_event = await self._get_active_event(guild)
            rarity, fruit = _draw_fruit(active_event)
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
            if active_event:
                event_def = SEASONAL_EVENTS.get(active_event.lower())
                if event_def:
                    embed.description += (
                        f"\n\n*Seasonal event active: {event_def['emoji']} {event_def['name']}.*"
                    )
            if channel:
                await channel.send(embed=embed)
            else:
                with suppress(discord.HTTPException):
                    await member.send(embed=embed)
            return

        # ── Level 50: Stage 1 Awakening ──────────────────────────────────
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

        # ── Level 100: Full Awakening ─────────────────────────────────────
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
    # Commands — Devil Fruit
    # -----------------------------------------------------------------------
    @commands.group(name="devilfruit", aliases=["df"])
    @commands.guild_only()
    async def devilfruit(self, ctx: commands.Context) -> None:
        """Devil Fruit commands."""

    # ── [p]df info ──────────────────────────────────────────────────────────
    @devilfruit.command(name="info", aliases=["check", "fruit"])
    async def df_info(self, ctx: commands.Context, member: t.Optional[discord.Member] = None) -> None:
        """Show your (or another member's) Devil Fruit — including Pirate Rep."""
        target = member or ctx.author
        guild_data = self.db.get_guild(ctx.guild.id)
        user_data = guild_data.get_user(target.id)

        if user_data is None or not user_data.fruit_name:
            who = "You haven't" if target == ctx.author else f"{target.display_name} hasn't"
            await ctx.send(f"🌊 {who} eaten a Devil Fruit yet. Reach **Level {FRUIT_ASSIGN_LEVEL}** to receive one!")
            return

        # Pass rep_tracker so rep fields are included
        embed = _build_fruit_embed(target, user_data, rep_tracker=self.rep_tracker)
        active_event = await self._get_active_event(ctx.guild)
        if active_event:
            event_def = SEASONAL_EVENTS.get(active_event.lower())
            if event_def:
                footer_text = embed.footer.text or ""
                embed.set_footer(
                    text=f"{event_def['emoji']} {event_def['name']} event active • {footer_text}"
                )
        await ctx.send(embed=embed)

    @devilfruit.command(name="toggle")
    async def df_toggle(self, ctx: commands.Context, state: t.Optional[str] = None) -> None:
        """Toggle whether your Devil Fruit appears after .profile / .pf."""
        guild_data = self.db.get_guild(ctx.guild.id)
        user_data = guild_data.get_user(ctx.author.id)

        if user_data is None or not user_data.fruit_name:
            return await ctx.send(
                f"🌊 You haven't eaten a Devil Fruit yet. Reach **Level {FRUIT_ASSIGN_LEVEL}** to receive one!"
            )

        if state is None:
            user_data.profile_visible = not user_data.profile_visible
        else:
            normalized = state.lower()
            if normalized in {"on", "enable", "enabled", "yes", "true"}:
                user_data.profile_visible = True
            elif normalized in {"off", "disable", "disabled", "no", "false"}:
                user_data.profile_visible = False
            else:
                return await ctx.send(
                    "❌ Usage: `.df toggle [on/off]` — omit the argument to flip the current state."
                )

        guild_data.set_user(ctx.author.id, user_data)
        await self._save()

        status = "enabled" if user_data.profile_visible else "disabled"
        await ctx.send(
            f"✅ Devil Fruit profile cards are now **{status}** for your .profile / .pf view. "
            f"You can still use `.df info` to view your fruit directly."
        )

    # ── [p]df rep ───────────────────────────────────────────────────────────
    @devilfruit.command(name="rep")
    async def df_rep(self, ctx: commands.Context, member: t.Optional[discord.Member] = None) -> None:
        """Show your full Pirate Rep card (or another member's)."""
        if self.rep_tracker is None:
            return await ctx.send("⚠️ Pirate Rep tracker is not initialised yet.")
        target = member or ctx.author

        weekly_lb = self.rep_tracker.weekly_leaderboard(ctx.guild.id)
        streak_lb = self.rep_tracker.streak_leaderboard(ctx.guild.id)
        rep_lb = self.rep_tracker.rep_leaderboard(ctx.guild.id)

        uid_str = str(target.id)
        weekly_rank = next((i + 1 for i, (uid, _) in enumerate(weekly_lb) if uid == uid_str), None)
        streak_rank = next((i + 1 for i, (uid, _) in enumerate(streak_lb) if uid == uid_str), None)
        rep_rank = next((i + 1 for i, (uid, _) in enumerate(rep_lb) if uid == uid_str), None)

        embed = self.rep_tracker.full_rep_embed(
            target,
            ctx.guild.id,
            weekly_rank=weekly_rank,
            streak_rank=streak_rank,
            rep_rank=rep_rank,
        )
        await ctx.send(embed=embed)

    @devilfruit.command(name="top", aliases=["leaders"])
    async def df_top(self, ctx: commands.Context) -> None:
        """Show the server's top Pirate Rep leaders."""
        if self.rep_tracker is None:
            return await ctx.send("⚠️ Pirate Rep tracker is not initialised yet.")

        lb = self.rep_tracker.rep_leaderboard(ctx.guild.id)
        if not lb:
            return await ctx.send("🌊 No rep data found on this server yet.")

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid_str, rep) in enumerate(lb):
            member = ctx.guild.get_member(int(uid_str))
            name = member.mention if member else f"<@{uid_str}>"
            medal = medals[i] if i < 3 else f"`#{i + 1}`"
            lines.append(f"{medal} {name} — **{rep:,}** rep")

        await self._send_paginated_embed(
            ctx,
            title="🏆 Pirate Rep Leaders",
            lines=lines,
            colour=discord.Colour.gold(),
            footer="Use .df rep to see a full Pirate Rep card.",
        )

    @devilfruit.command(name="duel", aliases=["spar", "fight"])
    async def df_duel(
        self,
        ctx: commands.Context,
        target: discord.Member,
        wager: t.Optional[int] = None,
    ) -> None:
        """Challenge another member to a Devil Fruit duel with an optional Beri wager."""
        if target.bot:
            return await ctx.send("🤖 You can't duel bots.")
        if target == ctx.author:
            return await ctx.send("❌ You can't duel yourself.")

        guild_data = self.db.get_guild(ctx.guild.id)
        challenger_data = guild_data.get_user(ctx.author.id)
        target_data = guild_data.get_user(target.id)

        if challenger_data is None or not challenger_data.fruit_name:
            return await ctx.send("🌊 You need a Devil Fruit to duel.")
        if target_data is None or not target_data.fruit_name:
            return await ctx.send(f"🌊 {target.display_name} doesn't have a Devil Fruit to duel.")

        if wager is None:
            wager = 0
        elif wager < 0:
            return await ctx.send("❌ Wager must be a positive amount of Beri.")

        currency_name = await self._get_currency_name(ctx.guild)

        if wager > 0:
            challenger_balance = await self._get_balance(ctx.guild, ctx.author)
            target_balance = await self._get_balance(ctx.guild, target)
            if challenger_balance < wager:
                return await ctx.send(
                    f"💸 You need **{wager:,} {currency_name}** for that wager, but only have **{challenger_balance:,}**."
                )
            if target_balance < wager:
                return await ctx.send(
                    f"💸 {target.display_name} needs at least **{wager:,} {currency_name}** to accept the duel."
                )

        strength_values = {
            "Paramecia": 70,
            "Zoan": 85,
            "Logia": 100,
            "Ancient Zoan": 110,
            "Mythical Zoan": 120,
            "Legendary": 140,
        }
        stage_bonus = {0: 0, 1: 10, 2: 25}

        def combat_strength(data: UserFruitData) -> int:
            base = strength_values.get(data.fruit_type, 80)
            return base + stage_bonus.get(data.awakening_stage, 0)

        challenger_strength = combat_strength(challenger_data)
        target_strength = combat_strength(target_data)
        differential = challenger_strength - target_strength
        win_chance = 0.5 + (differential / 200)
        win_chance = max(0.10, min(0.90, win_chance))

        if wager > 0:
            await self._withdraw_currency(ctx, ctx.author, wager)
            try:
                await self._withdraw_currency(ctx, target, wager)
            except ValueError:
                await self._modify_currency(ctx.author, wager, ctx.guild, actor=ctx.bot, reason="devilfruit:duel_refund")
                return await ctx.send(
                    f"💸 {target.display_name} can't cover the wager right now."
                )

        winner = ctx.author if random.random() < win_chance else target
        upset = (
            winner == target and challenger_strength > target_strength
            or winner == ctx.author and challenger_strength < target_strength
        )

        result_text = (
            f"⚔️ **{ctx.author.display_name}** ({challenger_data.fruit_type}) vs "
            f"**{target.display_name}** ({target_data.fruit_type})\n"
            f"Chance to win: **{int(win_chance * 100)}%** for {ctx.author.display_name}."
        )

        if wager > 0:
            total_pot = wager * 2
            winner_name = winner.display_name
            await self._modify_currency(winner, total_pot, ctx.guild, actor=ctx.bot, reason="devilfruit:duel")
            result_text += f"\n🏆 {winner_name} wins **{total_pot:,} {currency_name}**!"
        else:
            result_text += f"\n🏆 {winner.display_name} wins the duel!"

        if upset:
            result_text += "\n✨ What an upset!"

        embed = discord.Embed(
            title="⚔️ Devil Fruit Duel",
            description=result_text,
            colour=discord.Colour.dark_red(),
        )
        embed.add_field(name="Your strength", value=str(challenger_strength), inline=True)
        embed.add_field(name=f"{target.display_name}'s strength", value=str(target_strength), inline=True)
        if wager > 0:
            embed.set_footer(text=f"{currency_name} wager: {wager:,}")

        await ctx.send(embed=embed)

    # ── [p]df weekly ────────────────────────────────────────────────────────
    @devilfruit.command(name="weekly")
    async def df_weekly(self, ctx: commands.Context) -> None:
        """Show the weekly most-active pirates leaderboard."""
        if self.rep_tracker is None:
            return await ctx.send("⚠️ Pirate Rep tracker is not initialised yet.")

        from .piraterep import _week_key, _weekly_badge

        lb = self.rep_tracker.weekly_leaderboard(ctx.guild.id)
        embed = discord.Embed(
            title=f"📅 Weekly Active Pirates — {_week_key()}",
            colour=discord.Colour.blurple(),
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        if not lb:
            embed.description = "No messages tracked yet this week. Get chatting! 🗣️"
            return await ctx.send(embed=embed)

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid_str, count) in enumerate(lb[:15]):
            m = ctx.guild.get_member(int(uid_str))
            name = m.mention if m else f"<@{uid_str}>"
            badge = _weekly_badge(count)
            medal = medals[i] if i < 3 else f"`#{i + 1}`"
            badge_str = f" {badge}" if badge else ""
            lines.append(f"{medal} {name} — **{count:,}**{badge_str}")

        embed.description = "\n".join(lines)
        embed.set_footer(text="Week resets every Sunday at midnight UTC.")
        await ctx.send(embed=embed)

    # ── [p]df streak ────────────────────────────────────────────────────────
    @devilfruit.command(name="streak")
    async def df_streak(self, ctx: commands.Context) -> None:
        """Show the current daily streak leaderboard."""
        if self.rep_tracker is None:
            return await ctx.send("⚠️ Pirate Rep tracker is not initialised yet.")

        from .piraterep import _utc_today
        from datetime import date

        lb = self.rep_tracker.streak_leaderboard(ctx.guild.id)
        embed = discord.Embed(
            title="🔥 Pirate Streak Leaderboard",
            colour=discord.Colour.orange(),
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        if not lb:
            embed.description = "No active streaks yet. Start chatting every day! 🔥"
            return await ctx.send(embed=embed)

        today = _utc_today()
        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid_str, streak) in enumerate(lb[:15]):
            m = ctx.guild.get_member(int(uid_str))
            name = m.mention if m else f"<@{uid_str}>"
            u = self.rep_tracker.get_user(ctx.guild.id, int(uid_str))
            active = ""
            if u.last_seen:
                last = date.fromisoformat(u.last_seen)
                active = " 🔥" if (today - last).days <= 1 else " 💤"
            medal = medals[i] if i < 3 else f"`#{i + 1}`"
            lines.append(f"{medal} {name} — **{streak}** day{'s' if streak != 1 else ''}{active}")

        embed.description = "\n".join(lines)
        embed.set_footer(text="🔥 = active today/yesterday  💤 = streak at risk")
        await ctx.send(embed=embed)

    # ── [p]df reroll ────────────────────────────────────────────────────────
    @devilfruit.command(name="reroll", aliases=["change", "new"])
    async def df_reroll(self, ctx: commands.Context) -> None:
        """
        Reroll your Devil Fruit for Beri. Unlimited rerolls — but costs grow significantly each time.

        Cost schedule (first 10):
        1st → 10,000 ⬩ 2nd → 25,000 ⬩ 3rd → 50,000 ⬩ 4th → 100,000 ⬩ 5th → 200,000
        6th → 350,000 ⬩ 7th → 500,000 ⬩ 8th → 750,000 ⬩ 9th → 1,000,000 ⬩ 10th → 1,500,000
        Beyond 10th: ×1.5 compounding each time — costs skyrocket fast.
        """
        guild_data = self.db.get_guild(ctx.guild.id)
        user_data = guild_data.get_user(ctx.author.id)

        if user_data is None or not user_data.fruit_name:
            return await ctx.send(
                f"🌊 You haven't eaten a Devil Fruit yet. Reach **Level {FRUIT_ASSIGN_LEVEL}** first!"
            )

        raw_cost = _next_reroll_cost(user_data.reroll_count)
        multiplier = self._reroll_cost_multiplier(user_data.fruit_type)
        cost = max(1, int(math.ceil(raw_cost * multiplier)))
        currency_name = await self._get_currency_name(ctx.guild)
        next_cost_preview = _next_reroll_cost(user_data.reroll_count + 1)

        discount_text = ""
        if multiplier < 1.0:
            discount_pct = int((1.0 - multiplier) * 100)
            discount_text = f"\n*Your {user_data.fruit_type} fruit gives a {discount_pct}% reroll discount.*"

        confirm_msg = await ctx.send(
            f"⚠️ Rerolling your Devil Fruit costs **{cost:,} {currency_name}**.\n"
            f"Your current fruit (**{user_data.fruit_name}**) will be **permanently lost**.\n"
            f"*Next reroll after this would cost: **{next_cost_preview:,} {currency_name}***{discount_text}\n"
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

        try:
            await self._withdraw_currency(ctx, ctx.author, cost)
        except ValueError:
            balance = await self._get_balance(ctx.guild, ctx.author)
            return await ctx.send(
                f"💸 You don't have enough {currency_name}! "
                f"You need **{cost:,}** but only have **{balance:,}**."
            )

        old_type = user_data.fruit_type
        active_event = await self._get_active_event(ctx.guild)
        rarity, fruit = _draw_fruit(active_event)

        user_data.fruit_name = fruit["name"]
        user_data.fruit_type = rarity
        user_data.awakening_stage = 0
        user_data.reroll_count += 1
        user_data.last_reroll_cost = cost
        guild_data.set_user(ctx.author.id, user_data)
        await self._save()

        embed = _build_fruit_embed(ctx.author, user_data, title_prefix="🍎 New Fruit! ")
        description = (
            f"You spent **{cost:,} {currency_name}** and ate a new Devil Fruit!\n"
            f"*Your previous {old_type} fruit is gone forever...*"
        )
        if active_event:
            event_def = SEASONAL_EVENTS.get(active_event.lower())
            if event_def:
                description += (
                    f"\n*Seasonal event active: {event_def['emoji']} {event_def['name']} — "
                    f"new fruits are drawn from the limited-time pool.*"
                )
        if multiplier < 1.0:
            discount_pct = int((1.0 - multiplier) * 100)
            description += f"\n*{user_data.fruit_type} fruits get a {discount_pct}% reroll discount.*"
        embed.description = description

        next_cost = _next_reroll_cost(user_data.reroll_count)
        embed.set_footer(text=f"Reroll #{user_data.reroll_count} complete. Next reroll: {next_cost:,} {currency_name}.")
        await ctx.send(embed=embed)

    # ── [p]df list ──────────────────────────────────────────────────────────
    @devilfruit.command(name="list", aliases=["leaderboard", "lb"])
    async def df_list(self, ctx: commands.Context) -> None:
        """Show all Devil Fruit users in the server, paginated."""
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

        await self._send_paginated_embed(
            ctx,
            title=f"🍎 Devil Fruit Users — {ctx.guild.name}",
            lines=lines,
            colour=discord.Colour.dark_red(),
            footer=f"{len(lines)} pirates total",
        )

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

    # ── [p]df rerollcost ────────────────────────────────────────────────────
    @devilfruit.command(name="rerollcost", aliases=["cost"])
    async def df_reroll_cost(self, ctx: commands.Context, member: t.Optional[discord.Member] = None) -> None:
        """Show the current and upcoming reroll costs for yourself or another member."""
        target = member or ctx.author
        guild_data = self.db.get_guild(ctx.guild.id)
        user_data = guild_data.get_user(target.id)
        currency_name = await self._get_currency_name(ctx.guild)

        count = user_data.reroll_count if user_data else 0
        preview_lines = []
        for i in range(5):
            n = count + i
            c = _next_reroll_cost(n)
            label = f"Reroll #{n + 1}"
            if i == 0:
                label += " ← next"
            preview_lines.append(f"`{label}`: **{c:,} {currency_name}**")

        who = target.display_name
        embed = discord.Embed(
            title=f"💸 Reroll Costs — {who}",
            description="\n".join(preview_lines),
            colour=discord.Colour.dark_gold(),
        )
        embed.set_footer(text=f"Total rerolls so far: {count}. Costs compound ×1.5 after reroll #10.")
        await ctx.send(embed=embed)

    # ── Admin: [p]df admin ───────────────────────────────────────────────────
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
        """Assign (or randomly assign) a Devil Fruit to a member."""
        guild_data = self.db.get_guild(ctx.guild.id)

        if fruit_name:
            found_type, found_fruit = None, None
            for rarity, fruits in DEVIL_FRUITS.items():
                for f in fruits:
                    if fruit_name.lower() in f["name"].lower():
                        found_type, found_fruit = rarity, f
                        break
                if found_fruit:
                    break
            if found_fruit is None:
                return await ctx.send(f"❌ No fruit found matching `{fruit_name}`. Check `.df browse`.")
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

    @df_admin.command(name="resetrep")
    async def df_admin_reset_rep(self, ctx: commands.Context, member: discord.Member) -> None:
        """Reset a member's Pirate Rep data (streak, messages, rep score)."""
        if self.rep_tracker is None:
            return await ctx.send("⚠️ Pirate Rep tracker is not initialised.")
        g = self.rep_tracker._db.get_guild(ctx.guild.id)
        uid_str = str(member.id)
        if uid_str in g.users:
            del g.users[uid_str]
            await self.rep_tracker.save()
            await ctx.send(f"🗑️ Pirate Rep data cleared for **{member.display_name}**.")
        else:
            await ctx.send(f"ℹ️ {member.display_name} has no Pirate Rep data to clear.")

    @df_admin.command(name="rankchannel")
    async def df_admin_rank_channel(
        self,
        ctx: commands.Context,
        channel: t.Optional[discord.TextChannel] = None,
    ) -> None:
        """Set or view the Pirate rank announcement channel."""
        if channel is None:
            current = await self.config.guild(ctx.guild).rank_announcement_channel()
            if current is None:
                return await ctx.send(
                    "ℹ️ Pirate rank announcements are not configured."
                    " Use `.df admin rankchannel #channel` to enable them."
                )

            existing = ctx.guild.get_channel(current)
            if existing is None:
                await self.config.guild(ctx.guild).rank_announcement_channel.set(None)
                return await ctx.send(
                    "⚠️ The configured rank announcement channel no longer exists."
                    " It has been cleared."
                )

            return await ctx.send(
                f"🏴‍☠️ Pirate rank announcements are currently enabled in {existing.mention}."
            )

        await self.config.guild(ctx.guild).rank_announcement_channel.set(channel.id)
        await ctx.send(
            f"✅ Pirate rank announcements will now post in {channel.mention}."
        )

    @df_admin.command(name="event")
    async def df_admin_event(self, ctx: commands.Context, *, event_name: t.Optional[str] = None) -> None:
        """Set or clear the active seasonal Devil Fruit event pool."""
        if event_name is None:
            active = await self._get_active_event(ctx.guild)
            if active is None:
                available = ", ".join(
                    f"{data['emoji']} `{key}`" for key, data in SEASONAL_EVENTS.items()
                )
                return await ctx.send(
                    "ℹ️ No seasonal event is currently active. "
                    f"Available events: {available}. Use `.df admin event <name>` to enable one."
                )

            event_def = SEASONAL_EVENTS.get(active.lower())
            if event_def is None:
                await self.config.guild(ctx.guild).active_event.set(None)
                return await ctx.send(
                    "⚠️ The configured event is no longer available and has been cleared."
                )
            return await ctx.send(
                f"🎉 Seasonal event active: {event_def['emoji']} **{event_def['name']}**. "
                f"New Devil Fruits will draw from that limited pool."
            )

        lookup = event_name.strip().lower()
        if lookup in {"off", "none", "clear", "disable"}:
            await self.config.guild(ctx.guild).active_event.set(None)
            return await ctx.send("✅ Seasonal event cleared. Devil Fruit draws return to normal.")

        normalized = "".join(lookup.split())
        matched = next(
            (
                key
                for key, data in SEASONAL_EVENTS.items()
                if key == normalized or "".join(data["name"].lower().split()) == normalized
            ),
            None,
        )
        if matched is None:
            available = ", ".join(
                f"{data['emoji']} `{key}` ({data['name']})" for key, data in SEASONAL_EVENTS.items()
            )
            return await ctx.send(
                f"❌ Unknown event `{event_name}`. Available seasonal events: {available}."
            )

        await self.config.guild(ctx.guild).active_event.set(matched)
        event_def = SEASONAL_EVENTS[matched]
        await ctx.send(
            f"✅ Seasonal event enabled: {event_def['emoji']} **{event_def['name']}**. "
            f"New Devil Fruits will now draw from the event fruit pool."
        )

    # ── Admin: [p]df admin bulkassign ────────────────────────────────────────
    @df_admin.command(name="bulkassign")
    async def df_admin_bulk_assign(self, ctx: commands.Context) -> None:
        """
        Scan all server members via LevelUp and assign a Devil Fruit to anyone
        at Level 5+ who doesn't already have one.
        """
        levelup_cog = (
            ctx.bot.get_cog("LevelUp")
            or ctx.bot.get_cog("Levelup")
            or ctx.bot.get_cog("levelup")
            or ctx.bot.get_cog("Level")
        )
        if levelup_cog is None:
            for name, cog in ctx.bot.cogs.items():
                if "level" in name.lower():
                    levelup_cog = cog
                    break

        if levelup_cog is None:
            loaded = ", ".join(f"`{n}`" for n in ctx.bot.cogs)
            return await ctx.send(f"❌ Could not find the LevelUp cog. Loaded cogs: {loaded}")

        await ctx.send(f"⏳ Found LevelUp cog as `{type(levelup_cog).__name__}`. Scanning all members...")

        guild_data = self.db.get_guild(ctx.guild.id)
        assigned = 0
        awakening_updated = 0
        skipped = 0
        errors = 0

        try:
            lu_db = getattr(levelup_cog, "db", None)
            if lu_db is None:
                return await ctx.send("❌ LevelUp's `.db` attribute not found — unsupported LevelUp version.")
            lu_conf = lu_db.get_conf(ctx.guild)
        except Exception as exc:
            log.error("OnePieceFruit bulkassign: failed to access LevelUp db.", exc_info=exc)
            return await ctx.send(f"❌ Error accessing LevelUp db: `{exc}`")

        for member in ctx.guild.members:
            if member.bot:
                skipped += 1
                continue
            try:
                profile = lu_conf.get_profile(member.id)
                level = getattr(profile, "level", 0) or 0
                if level < FRUIT_ASSIGN_LEVEL:
                    skipped += 1
                    continue

                existing = guild_data.get_user(member.id)

                if existing is None:
                    rarity, fruit = _draw_fruit()
                    if level >= AWAKENING_STAGE2_LEVEL:
                        awakening_stage = 2
                    elif level >= AWAKENING_STAGE1_LEVEL:
                        awakening_stage = 1
                    else:
                        awakening_stage = 0

                    new_data = UserFruitData(
                        fruit_name=fruit["name"],
                        fruit_type=rarity,
                        assigned_at_level=level,
                        awakening_stage=awakening_stage,
                    )
                    guild_data.set_user(member.id, new_data)
                    assigned += 1
                else:
                    updated = False
                    if level >= AWAKENING_STAGE2_LEVEL and existing.awakening_stage < 2:
                        existing.awakening_stage = 2
                        updated = True
                    elif level >= AWAKENING_STAGE1_LEVEL and existing.awakening_stage < 1:
                        existing.awakening_stage = 1
                        updated = True

                    if updated:
                        guild_data.set_user(member.id, existing)
                        awakening_updated += 1
                    else:
                        skipped += 1

            except Exception as exc:
                log.warning(f"OnePieceFruit bulkassign: error processing {member.id}", exc_info=exc)
                errors += 1

        await self._save()

        embed = discord.Embed(title="🍎 Bulk Assign Complete", colour=discord.Colour.green())
        embed.add_field(name="✅ Fruits Assigned", value=str(assigned), inline=True)
        embed.add_field(name="⚡ Awakenings Updated", value=str(awakening_updated), inline=True)
        embed.add_field(name="⏭️ Skipped", value=str(skipped), inline=True)
        if errors:
            embed.add_field(name="⚠️ Errors", value=str(errors), inline=True)
        embed.set_footer(text="Members below Level 5, bots, and members already fully up-to-date are skipped.")
        await ctx.send(embed=embed)

    # ── [p]df browse ────────────────────────────────────────────────────────
    @devilfruit.command(name="browse")
    async def df_browse(self, ctx: commands.Context, *, rarity: t.Optional[str] = None) -> None:
        """Browse available Devil Fruits by rarity."""
        valid = list(DEVIL_FRUITS.keys())

        if rarity is None:
            active_event = await self._get_active_event(ctx.guild)
            description = (
                "Use `[p]df browse <type>` to see fruits in a category.\n\n"
                + "\n".join(f"{RARITY_EMOJIS[r]} **{r}** — {len(DEVIL_FRUITS[r])} fruits" for r in valid)
            )
            if active_event:
                event_def = SEASONAL_EVENTS.get(active_event.lower())
                if event_def:
                    description += (
                        f"\n\n🎉 Active seasonal event: {event_def['emoji']} **{event_def['name']}** — "
                        f"use `[p]df browse {active_event}` to preview its fruits."
                    )

            embed = discord.Embed(
                title="🍎 Available Devil Fruit Types",
                description=description,
                colour=discord.Colour.dark_red(),
            )
            return await ctx.send(embed=embed)

        lookup = rarity.strip().lower()
        normalized_lookup = "".join(lookup.split())
        matched = next(
            (
                r
                for r in valid
                if r.lower() == lookup or "".join(r.lower().split()) == normalized_lookup
            ),
            None,
        )
        if matched is None:
            event_match = next(
                (
                    key
                    for key, data in SEASONAL_EVENTS.items()
                    if key == normalized_lookup
                    or "".join(data["name"].lower().split()) == normalized_lookup
                ),
                None,
            )
            if event_match is not None:
                event_def = SEASONAL_EVENTS[event_match]
                fruits = event_def["fruits"]
                emoji = event_def["emoji"]
                lines = [f"• {f['name']} — {f['fruit_type']}" for f in fruits]

                embed = discord.Embed(
                    title=f"{emoji} {event_def['name']} Seasonal Fruits ({len(fruits)} total)",
                    description="\n".join(lines),
                    colour=discord.Colour.dark_purple(),
                )
                embed.set_footer(text="Seasonal event fruit pool")
                return await ctx.send(embed=embed)

            return await ctx.send(f"❌ Unknown rarity `{rarity}`. Valid options: {', '.join(valid)}")

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

    @devilfruit.command(name="search")
    async def df_search(self, ctx: commands.Context, *, query: str) -> None:
        """Search Devil Fruits by partial name."""
        normalized = query.strip().lower()
        if not normalized:
            return await ctx.send("❌ Usage: `.df search <term>`")

        results = []
        for rarity, fruits in DEVIL_FRUITS.items():
            for fruit in fruits:
                if normalized in fruit["name"].lower():
                    results.append(f"{RARITY_EMOJIS.get(rarity, '❓')} **{fruit['name']}** — {rarity}")

        if not results:
            return await ctx.send(f"❌ No Devil Fruits found matching `{query}`.")

        if len(results) > 20:
            results = results[:20] + ["...and more results not shown."]

        embed = discord.Embed(
            title=f"🔎 Devil Fruit Search — {query}",
            description="\n".join(results),
            colour=discord.Colour.dark_red(),
        )
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
