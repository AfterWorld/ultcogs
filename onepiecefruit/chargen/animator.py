"""
chargen/animator.py
─────────────────────────────────────────────────────────────────────────────
Asynchronous phased embed animator — RPG stat screen edition with
Components V2 during spin phase.

Rate limit strategy:
  Spin     → 8 edits over ~5.5s     (~1/0.69s — safe)
  Phases   → 4 edits across ~8.5s   (1 per ~2.1s)
  Total    → ~13 edits / ~14s.  Effective: ~0.93 edits/s. Well under 5/5s.

RPG loading bar:
  Stat string → STAT_TIER_VALUE lookup → int 0-100 → bar string.
  Bar is 10 chars wide: filled = round(val/10), empty = 10 - filled.
  Format: ████████░░ 80%

Components V2 layout (spin phase only):
  ┌─ ActionRow ──────────────────────────────────────────────────────────┐
  │  [📣 Share Sheet]  [⚔️ View Rival]  [🎲 Re-roll?]                   │
  └──────────────────────────────────────────────────────────────────────┘
  Stripped on final reveal via msg.edit(components=[]).

Separator logic:
  discord.py exposes discord.ui.Separator (Components V2) if the library
  version supports it. We wrap usage in a try/except so older builds degrade
  gracefully to no separators rather than crashing.

Animation flow:
  Phase 0  → Initial send   (blank canvas + components)
  Spin     → 8 ticks        (slot-machine deceleration across all 4 fields)
  Lock     → Snap frame     (real values + 🔒 on every line)
  Phase 1  → Core Identity  (🔒 removed, blue)
  Phase 2  → Weapon System  (green)
  Phase 3  → Power System   (orange, mastery bars)
  Phase 4  → Threat/Stats   (gold, stat bars, rival, bounty, timestamp)
             Components stripped on this edit.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import ui
from redbot.core import commands

from .models import OnePieceCharacter
from . import pools as P

log = logging.getLogger("red.OnePieceFruit.chargen")

# ── Colors ─────────────────────────────────────────────────────────────────────
COLOR_DARK    = 0x1A1A2E
COLOR_SPIN    = 0x6A0DAD
COLOR_PHASE_1 = 0x1A6DB5
COLOR_PHASE_2 = 0x2E8B57
COLOR_PHASE_3 = 0xD4651A
COLOR_FINAL   = 0xF5C518

# ── Timing ─────────────────────────────────────────────────────────────────────
SPIN_INTERVALS = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
DELAY_PHASE_1  = 2.0
DELAY_PHASE_2  = 2.0
DELAY_PHASE_3  = 2.0
DELAY_PHASE_4  = 2.5

SPINNER = "🌀 *Calculating...*"

# ── Spin sample pools ──────────────────────────────────────────────────────────
_RACE_S    = list(P.RACE.keys())
_AFFIL_S   = list(P.AFFILIATION.keys())
_ORIGIN_S  = list(P.ORIGIN.keys())
_WEAPON_S  = list(P.WEAPON_TYPE.keys())
_WMAST_S   = list(P.WEAPON_MASTERY.keys())
_FRUIT_S   = ["Paramecia", "Zoan", "Logia", "Ancient Zoan", "Mythical Zoan", "None"]
_HAKI_S    = list(P.HAKI_POTENTIAL.keys())
_STYLE_S   = list(P.FIGHTING_STYLE_OTHER.keys())
_STAT_S    = list(P.STAT_TIER.keys())
_RIVAL_S   = list(P.RIVAL.keys())
_THREAT_S  = [
    "⚪ Below Radar", "🔵 Notable Threat", "🟢 Super Rookie",
    "🟡 Warlord-Class", "🟠 Emperor's Crew Level", "🔴 Yonko-Class",
]
_BOUNTY_S  = [
    "฿ 3,200,000", "฿ 44,000,000", "฿ 120,000,000",
    "฿ 340,000,000", "฿ 860,000,000", "฿ 2,400,000,000",
]


# ─────────────────────────────────────────────────────────────────────────────
# Loading bar helpers
# ─────────────────────────────────────────────────────────────────────────────

def _bar(tier: str, width: int = 10) -> str:
    """
    Returns a block-fill loading bar for a stat tier.
    Example: _bar("S-Tier") → "█████████░ 90%"
    """
    val     = P.STAT_TIER_VALUE.get(tier, 0)
    filled  = round(val / 100 * width)
    empty   = width - filled
    return f"{'█' * filled}{'░' * empty} {val}%"


def _mastery_bar(mastery: Optional[str], pool_keys: list[str], width: int = 10) -> str:
    """
    Derives a loading bar from a mastery string's position in its pool's key list.
    Position 0 = lowest, len-1 = highest.
    """
    if mastery is None:
        return "░" * width + "  0%"
    keys = pool_keys
    idx  = keys.index(mastery) if mastery in keys else 0
    val  = round((idx / max(len(keys) - 1, 1)) * 100)
    filled = round(val / 100 * width)
    empty  = width - filled
    return f"{'█' * filled}{'░' * empty} {val}%"


_HAKI_MASTERY_KEYS = list(P.HAKI_MASTERY.keys())
_DFRUIT_MASTERY_KEYS = list(P.DEVIL_FRUIT_MASTERY.keys())
_WEAPON_MASTERY_KEYS = list(P.WEAPON_MASTERY.keys())


# ─────────────────────────────────────────────────────────────────────────────
# Spin frame builders
# ─────────────────────────────────────────────────────────────────────────────

def _spin_identity() -> str:
    return (
        f"> **Race:**        {random.choice(_RACE_S)}\n"
        f"> **Lineage:**     ???\n"
        f"> **Affiliation:** {random.choice(_AFFIL_S)}\n"
        f"> **Origin:**      {random.choice(_ORIGIN_S)}\n"
        f"> **Epithet:**     *\"...\"*"
    )

def _spin_weapon() -> str:
    return (
        f"> **Weapon:**         {random.choice(_WEAPON_S)}\n"
        f"> **Mastery:**        {random.choice(_WMAST_S)}\n"
        f"> **Mastery Bar:**    `{'█' * random.randint(1,9)}{'░' * random.randint(1,3)}`"
    )

def _spin_power() -> str:
    return (
        f"> **Devil Fruit:**         {random.choice(_FRUIT_S)}\n"
        f"> **Fruit Mastery:**       ???\n"
        f"> **Haki Potential:**      {random.choice(_HAKI_S)}\n"
        f"> **Haki Mastery:**        ???\n"
        f"> **Combat Style:**        {random.choice(_STYLE_S)}"
    )

def _spin_threat() -> str:
    r = lambda: random.choice(_STAT_S)
    return (
        f"> **Strength:**     {r()}\n"
        f"> **Speed:**        {r()}\n"
        f"> **Battle IQ:**    {r()}\n"
        f"> **Endurance:**    {r()}\n"
        f"> **Willpower:**    {r()}\n"
        f"> **Rival:**        {random.choice(_RIVAL_S)}\n"
        f"> **World Threat:** {random.choice(_THREAT_S)}\n"
        f"> **Bounty:**       {random.choice(_BOUNTY_S)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Locked frame builders (real values + 🔒)
# ─────────────────────────────────────────────────────────────────────────────

def _locked_identity(c: OnePieceCharacter) -> str:
    return (
        f"> 🔒 **Race:**        {c.race}\n"
        f"> 🔒 **Lineage:**     {c.d_clan_display}\n"
        f"> 🔒 **Affiliation:** {c.affiliation}\n"
        f"> 🔒 **Origin:**      {c.origin}\n"
        f"> 🔒 **Epithet:**     *\"{c.epithet}\"*"
    )

def _locked_weapon(c: OnePieceCharacter) -> str:
    bar = _mastery_bar(c.weapon_mastery, _WEAPON_MASTERY_KEYS)
    return (
        f"> 🔒 **Weapon:**         {c.weapon_type}\n"
        f"> 🔒 **Mastery:**        {c.weapon_mastery}\n"
        f"> 🔒 **Mastery Bar:**    `{bar}`"
    )

def _locked_power(c: OnePieceCharacter) -> str:
    return (
        f"> 🔒 **Devil Fruit:**         {c.devil_fruit_display}\n"
        f"> 🔒 **Fruit Mastery:**       {c.devil_fruit_mastery_display}\n"
        f"> 🔒 **Haki Potential:**      {c.haki}\n"
        f"> 🔒 **Haki Mastery:**        {c.haki_mastery_display}\n"
        f"> 🔒 **Combat Style:**        {c.fighting_style}"
    )

def _locked_threat(c: OnePieceCharacter) -> str:
    bounty_line = _bounty_line(c, locked=True)
    return (
        f"> 🔒 **Strength:**     {c.strength}\n"
        f"> 🔒 **Speed:**        {c.speed}\n"
        f"> 🔒 **Battle IQ:**    {c.battle_iq}\n"
        f"> 🔒 **Endurance:**    {c.endurance}\n"
        f"> 🔒 **Willpower:**    {c.willpower}\n"
        f"> 🔒 **Rival:**        {c.rival}\n"
        f"> 🔒 **World Threat:** {c.threat_level_display}\n"
        f"{bounty_line}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Reveal frame builders (clean, no 🔒, with loading bars)
# ─────────────────────────────────────────────────────────────────────────────

def _reveal_identity(c: OnePieceCharacter) -> str:
    return (
        f"> **Race:**        {c.race}\n"
        f"> **Lineage:**     {c.d_clan_display}\n"
        f"> **Affiliation:** {c.affiliation}\n"
        f"> **Origin:**      {c.origin}\n"
        f"> **Epithet:**     *\"{c.epithet}\"*"
    )

def _reveal_weapon(c: OnePieceCharacter) -> str:
    bar = _mastery_bar(c.weapon_mastery, _WEAPON_MASTERY_KEYS)
    return (
        f"> **Weapon:**         {c.weapon_type}\n"
        f"> **Mastery:**        {c.weapon_mastery}\n"
        f"> **Mastery Bar:**    `{bar}`"
    )

def _reveal_power(c: OnePieceCharacter) -> str:
    df_bar  = _mastery_bar(c.devil_fruit_mastery, _DFRUIT_MASTERY_KEYS)
    hak_bar = _mastery_bar(c.haki_mastery, _HAKI_MASTERY_KEYS)
    return (
        f"> **Devil Fruit:**         {c.devil_fruit_display}\n"
        f"> **Fruit Mastery:**       {c.devil_fruit_mastery_display}\n"
        f"> **Fruit Bar:**           `{df_bar}`\n"
        f"> **Haki Potential:**      {c.haki}\n"
        f"> **Haki Mastery:**        {c.haki_mastery_display}\n"
        f"> **Haki Bar:**            `{hak_bar}`\n"
        f"> **Combat Style:**        {c.fighting_style}"
    )

def _reveal_threat(c: OnePieceCharacter) -> str:
    bounty_line = _bounty_line(c, locked=False)
    return (
        f"> **Strength:**     {c.strength}  `{_bar(c.strength)}`\n"
        f"> **Speed:**        {c.speed}  `{_bar(c.speed)}`\n"
        f"> **Battle IQ:**    {c.battle_iq}  `{_bar(c.battle_iq)}`\n"
        f"> **Endurance:**    {c.endurance}  `{_bar(c.endurance)}`\n"
        f"> **Willpower:**    {c.willpower}  `{_bar(c.willpower)}`\n"
        f"> **Rival:**        *{c.rival}*\n"
        f"> **World Threat:** {c.threat_level_display}\n"
        f"{bounty_line}"
    )

def _bounty_line(c: OnePieceCharacter, locked: bool = False) -> str:
    lock = "🔒 " if locked else ""
    if c.affiliation == "Marine":
        return f"> {lock}**Marine Rank:**  {c.marine_rank}"
    if c.affiliation == "World Noble":
        return f"> {lock}**Bounty:**       *Immune (World Noble)*"
    return f"> {lock}**Bounty:**       {c.bounty_display}"


# ─────────────────────────────────────────────────────────────────────────────
# Components V2
# ─────────────────────────────────────────────────────────────────────────────

class CharGenView(ui.View):
    """
    Components V2 view shown during the spin phase only.
    Three buttons: Share Sheet, View Rival, Re-roll Warning.
    Stored on the animator so button callbacks can access the character.

    The view is removed from the message on final reveal by passing
    view=None to msg.edit(). The view itself times out after 120s
    as a safety net.
    """

    def __init__(self, character: OnePieceCharacter, roller: discord.Member):
        super().__init__(timeout=120)
        self.character = character
        self.roller    = roller

    @ui.button(label="📣 Share Sheet", style=discord.ButtonStyle.secondary)
    async def share_sheet(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        """Posts a compact public summary mentioning the roller."""
        c = self.character

        # Build compact summary embed
        embed = discord.Embed(
            title=f"📋 {c.full_name}",
            description=(
                f"**{self.roller.mention}**'s One Piece character sheet:\n\n"
                f"**Race:** {c.race}  •  **Affiliation:** {c.affiliation}\n"
                f"**Devil Fruit:** {c.devil_fruit_display}\n"
                f"**Haki:** {c.haki}\n"
                f"**Weapon:** {c.weapon_type} *(Mastery: {c.weapon_mastery})*\n"
                f"**Rival:** *{c.rival}*  •  **Threat:** {c.threat_level_display}"
            ),
            color=COLOR_FINAL,
        )
        embed.set_thumbnail(url=self.roller.display_avatar.url)
        embed.set_footer(text="One Piece Community • Character Generation")

        await interaction.response.send_message(embed=embed)

    @ui.button(label="⚔️ View Rival", style=discord.ButtonStyle.primary)
    async def view_rival(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        """Sends an ephemeral with a lore blurb about the rolled rival."""
        rival_name = self.character.rival
        lore = P.RIVAL_LORE.get(
            rival_name,
            f"*{rival_name} — a name that carries weight on the seas. "
            f"Their full story has yet to be written.*"
        )
        embed = discord.Embed(
            title=f"⚔️ Rival Profile: {rival_name}",
            description=lore,
            color=COLOR_PHASE_1,
        )
        embed.set_footer(text="One Piece Community • Rival Lore")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="🎲 Re-roll?", style=discord.ButtonStyle.danger)
    async def reroll_warning(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        """Ephemeral: explains the no-reroll policy."""
        await interaction.response.send_message(
            "⚓ **The Grand Line grants no second chances.**\n\n"
            "Your character sheet is **permanent**. Once the roll is sealed, "
            "it cannot be undone by anyone except a server admin using "
            "`chardelete`.\n\n"
            "*The sea does not give refunds.*",
            ephemeral=True,
        )

    async def on_timeout(self) -> None:
        """Silently expire — message is already stripped of components by then."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Animator
# ─────────────────────────────────────────────────────────────────────────────

class CharacterAnimator:
    """
    Full phased reveal with RPG stat bars and Components V2.

    Flow:
        Phase 0 → Initial send   (blank canvas + components attached)
        Spin    → 8 ticks        (slot-machine across all 4 fields)
        Lock    → Snap frame     (real values + 🔒)
        Phase 1 → Core Identity  (blue, 🔒 removed)
        Phase 2 → Weapon System  (green, mastery bar)
        Phase 3 → Power System   (orange, fruit + haki bars)
        Phase 4 → Threat/Stats   (gold, stat bars, rival, bounty,
                                  timestamp, COMPONENTS STRIPPED)
    """

    @classmethod
    async def animate_roll(
        cls,
        ctx: commands.Context,
        character: OnePieceCharacter,
    ) -> discord.Message:
        view = CharGenView(character, ctx.author)
        msg  = await cls._send_initial(ctx, character, view)

        try:
            msg = await cls._spin_phase(msg, character)
            msg = await cls._reveal_phase_1(msg, character)
            msg = await cls._reveal_phase_2(msg, character)
            msg = await cls._reveal_phase_3(msg, character)
            msg = await cls._reveal_phase_4(msg, character)   # strips components
        except discord.HTTPException as exc:
            log.error(
                "CharacterAnimator edit failed user=%s guild=%s: %s",
                character.user_id, character.guild_id, exc,
            )
            try:
                await msg.edit(embed=cls._build_final_embed(character), view=None)
            except discord.HTTPException:
                log.error("CharacterAnimator final fallback also failed — giving up.")

        return msg

    # ── Phase 0 ───────────────────────────────────────────────────────────────

    @classmethod
    async def _send_initial(
        cls,
        ctx: commands.Context,
        character: OnePieceCharacter,
        view: CharGenView,
    ) -> discord.Message:
        embed = discord.Embed(
            title="🎰 The Wheel of Destiny Spins...",
            description=f"*The fate of **{character.display_name}** hangs in the balance...*",
            color=COLOR_DARK,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="One Piece Community • Character Generation")

        embed.add_field(name="🧬 Core Identity",   value=SPINNER, inline=False)
        embed.add_field(name="⚔️  Weapon System",   value=SPINNER, inline=False)
        embed.add_field(name="🌀 Power System",    value=SPINNER, inline=False)
        embed.add_field(name="📊 Threat Analysis", value=SPINNER, inline=False)

        return await ctx.send(embed=embed, view=view)

    # ── Spin ──────────────────────────────────────────────────────────────────

    @classmethod
    async def _spin_phase(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        embed = msg.embeds[0]
        embed.color = COLOR_SPIN
        total = len(SPIN_INTERVALS)

        for i, interval in enumerate(SPIN_INTERVALS):
            is_last = i == total - 1

            if is_last:
                embed.title = "🔒 Fate Sealed — Destiny Locked In..."
                id_v  = _locked_identity(character)
                wp_v  = _locked_weapon(character)
                pw_v  = _locked_power(character)
                th_v  = _locked_threat(character)
            else:
                id_v  = _spin_identity()
                wp_v  = _spin_weapon()
                pw_v  = _spin_power()
                th_v  = _spin_threat()

            embed.set_field_at(0, name="🧬 Core Identity",   value=id_v, inline=False)
            embed.set_field_at(1, name="⚔️  Weapon System",   value=wp_v, inline=False)
            embed.set_field_at(2, name="🌀 Power System",    value=pw_v, inline=False)
            embed.set_field_at(3, name="📊 Threat Analysis", value=th_v, inline=False)

            await msg.edit(embed=embed)
            await asyncio.sleep(interval)

        return msg

    # ── Phase 1 — Core Identity ───────────────────────────────────────────────

    @classmethod
    async def _reveal_phase_1(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        await asyncio.sleep(DELAY_PHASE_1)

        embed = msg.embeds[0]
        embed.color = COLOR_PHASE_1
        embed.title = "🏴‍☠️ The Grand Line Stirs..."
        embed.description = (
            f"*The fate of **{character.display_name}** is being written "
            f"into the tides of history...*"
        )

        embed.set_field_at(0, name="🧬 Core Identity",   value=_reveal_identity(character), inline=False)
        embed.set_field_at(1, name="⚔️  Weapon System",   value=SPINNER,                     inline=False)
        embed.set_field_at(2, name="🌀 Power System",    value=SPINNER,                     inline=False)
        embed.set_field_at(3, name="📊 Threat Analysis", value=SPINNER,                     inline=False)

        await msg.edit(embed=embed)
        return msg

    # ── Phase 2 — Weapon System ───────────────────────────────────────────────

    @classmethod
    async def _reveal_phase_2(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        await asyncio.sleep(DELAY_PHASE_2)

        embed = msg.embeds[0]
        embed.color = COLOR_PHASE_2

        embed.set_field_at(1, name="⚔️  Weapon System",   value=_reveal_weapon(character),  inline=False)
        embed.set_field_at(2, name="🌀 Power System",    value=SPINNER,                    inline=False)
        embed.set_field_at(3, name="📊 Threat Analysis", value=SPINNER,                    inline=False)

        await msg.edit(embed=embed)
        return msg

    # ── Phase 3 — Power System ────────────────────────────────────────────────

    @classmethod
    async def _reveal_phase_3(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        await asyncio.sleep(DELAY_PHASE_3)

        embed = msg.embeds[0]
        embed.color = COLOR_PHASE_3

        embed.set_field_at(2, name="🌀 Power System",    value=_reveal_power(character),   inline=False)
        embed.set_field_at(3, name="📊 Threat Analysis", value=SPINNER,                    inline=False)

        await msg.edit(embed=embed)
        return msg

    # ── Phase 4 — Threat Analysis (final, strips components) ─────────────────

    @classmethod
    async def _reveal_phase_4(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        await asyncio.sleep(DELAY_PHASE_4)

        embed = msg.embeds[0]
        embed.color = COLOR_FINAL
        embed.title = f"👑 {character.full_name}"
        embed.description = (
            "*This is your permanent character sheet. "
            "The Grand Line does not give second chances.*"
        )
        embed.timestamp = datetime.fromtimestamp(character.rolled_at, tz=timezone.utc)

        embed.set_field_at(3, name="📊 Threat Analysis", value=_reveal_threat(character), inline=False)

        # Strip components — final state is static
        await msg.edit(embed=embed, view=None)
        return msg

    # ── Fallback ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_final_embed(character: OnePieceCharacter) -> discord.Embed:
        embed = discord.Embed(
            title=f"👑 {character.full_name}",
            description="*This is your permanent character sheet.*",
            color=COLOR_FINAL,
            timestamp=datetime.fromtimestamp(character.rolled_at, tz=timezone.utc),
        )
        embed.set_footer(text="One Piece Community • Character Generation")
        embed.add_field(name="🧬 Core Identity",   value=_reveal_identity(character), inline=False)
        embed.add_field(name="⚔️  Weapon System",   value=_reveal_weapon(character),  inline=False)
        embed.add_field(name="🌀 Power System",    value=_reveal_power(character),   inline=False)
        embed.add_field(name="📊 Threat Analysis", value=_reveal_threat(character),  inline=False)
        return embed