"""
chargen/animator.py
─────────────────────────────────────────────────────────────────────────────
Asynchronous phased embed animator for character sheet reveals.

Rate limit strategy:
  Discord allows ~5 edits per 5s per message before issuing 429s.

  Phase 0   → 1 initial send
  Spin      → 8 edits over ~5.5s  (~1 edit/0.69s — safe)
  Phase 1   → 1 edit after 2.0s
  Phase 2   → 1 edit after 2.0s
  Phase 3   → 1 edit after 2.0s
  Phase 4   → 1 edit after 2.5s   (climax pacing)
  Total: ~13 edits across ~14 seconds. Effective rate: ~0.93 edits/s.

Animation flow:
  Phase 0  → Blank canvas (placeholder fields lock embed height)
  Spin     → Slot-machine cycling across all fields, decelerating 8 ticks
  Lock     → All fields snap to real values with 🔒 indicators
  Phase 1  → Core Identity revealed (race, lineage, affiliation, origin, epithet)
  Phase 2  → Weapon System revealed
  Phase 3  → Power System revealed (fruit, haki, mastery, fighting style)
  Phase 4  → Stats + Rival + Threat Level + Bounty final reveal

Field layout (v2 — 4 fields):
  🧬 Core Identity
  ⚔️  Weapon System
  🌀 Power System
  📊 Threat Analysis
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone

import discord
from redbot.core import commands

from .models import OnePieceCharacter
from . import pools as P

log = logging.getLogger("red.OnePieceFruit.chargen")

# ── Color constants ────────────────────────────────────────────────────────────
COLOR_DARK    = 0x1A1A2E   # Deep navy     — blank canvas
COLOR_SPIN    = 0x6A0DAD   # Purple        — slot machine active
COLOR_PHASE_1 = 0x1A6DB5   # Royal blue    — identity reveal
COLOR_PHASE_2 = 0x2E8B57   # Sea green     — weapon reveal
COLOR_PHASE_3 = 0xD4651A   # Burnt orange  — power system reveal
COLOR_FINAL   = 0xF5C518   # IMDb gold     — final stats reveal

# ── Timing ────────────────────────────────────────────────────────────────────
DELAY_PHASE_1 = 2.0
DELAY_PHASE_2 = 2.0
DELAY_PHASE_3 = 2.0
DELAY_PHASE_4 = 2.5   # Slightly longer for climax feel

# Spin deceleration: starts fast, slows to a halt
SPIN_INTERVALS = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]

# ── Placeholder ───────────────────────────────────────────────────────────────
SPINNER = "🌀 *Calculating...*"

# ── Spin sample pools ─────────────────────────────────────────────────────────
_RACE_SAMPLES     = list(P.RACE.keys())
_AFFIL_SAMPLES    = list(P.AFFILIATION.keys())
_ORIGIN_SAMPLES   = list(P.ORIGIN.keys())
_WEAPON_SAMPLES   = list(P.WEAPON_TYPE.keys())
_MASTERY_SAMPLES  = list(P.WEAPON_MASTERY.keys())
_FRUIT_SAMPLES    = ["Paramecia", "Zoan", "Logia", "Ancient Zoan", "Mythical Zoan", "None"]
_HAKI_SAMPLES     = list(P.HAKI_POTENTIAL.keys())
_STYLE_SAMPLES    = list(P.FIGHTING_STYLE_OTHER.keys())
_STAT_SAMPLES     = list(P.STAT_TIER.keys())
_RIVAL_SAMPLES    = list(P.RIVAL.keys())
_THREAT_SAMPLES   = [
    "⚪ Below Radar", "🔵 Notable Threat", "🟢 Super Rookie",
    "🟡 Warlord-Class", "🟠 Emperor's Crew Level", "🔴 Yonko-Class",
]
_BOUNTY_SAMPLES   = [
    "฿ 3,200,000", "฿ 44,000,000", "฿ 120,000,000",
    "฿ 340,000,000", "฿ 860,000,000", "฿ 2,400,000,000",
]


# ─────────────────────────────────────────────────────────────────────────────
# Spin frame builders
# ─────────────────────────────────────────────────────────────────────────────

def _spin_identity() -> str:
    return (
        f"> **Race:**        {random.choice(_RACE_SAMPLES)}\n"
        f"> **Lineage:**     ???\n"
        f"> **Affiliation:** {random.choice(_AFFIL_SAMPLES)}\n"
        f"> **Origin:**      {random.choice(_ORIGIN_SAMPLES)}\n"
        f"> **Epithet:**     *\"...\"*"
    )

def _spin_weapon() -> str:
    return (
        f"> **Weapon:**          {random.choice(_WEAPON_SAMPLES)}\n"
        f"> **Weapon Mastery:**  {random.choice(_MASTERY_SAMPLES)}"
    )

def _spin_power() -> str:
    return (
        f"> **Devil Fruit:**         {random.choice(_FRUIT_SAMPLES)}\n"
        f"> **Devil Fruit Mastery:** ???\n"
        f"> **Haki Potential:**      {random.choice(_HAKI_SAMPLES)}\n"
        f"> **Haki Mastery:**        ???\n"
        f"> **Combat Style:**        {random.choice(_STYLE_SAMPLES)}"
    )

def _spin_threat() -> str:
    return (
        f"> **Strength:**     {random.choice(_STAT_SAMPLES)}\n"
        f"> **Speed:**        {random.choice(_STAT_SAMPLES)}\n"
        f"> **Battle IQ:**    {random.choice(_STAT_SAMPLES)}\n"
        f"> **Endurance:**    {random.choice(_STAT_SAMPLES)}\n"
        f"> **Willpower:**    {random.choice(_STAT_SAMPLES)}\n"
        f"> **Rival:**        {random.choice(_RIVAL_SAMPLES)}\n"
        f"> **World Threat:** {random.choice(_THREAT_SAMPLES)}\n"
        f"> **Bounty:**       {random.choice(_BOUNTY_SAMPLES)}"
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
    return (
        f"> 🔒 **Weapon:**         {c.weapon_type}\n"
        f"> 🔒 **Weapon Mastery:** {c.weapon_mastery}"
    )

def _locked_power(c: OnePieceCharacter) -> str:
    return (
        f"> 🔒 **Devil Fruit:**         {c.devil_fruit_display}\n"
        f"> 🔒 **Devil Fruit Mastery:** {c.devil_fruit_mastery_display}\n"
        f"> 🔒 **Haki Potential:**      {c.haki}\n"
        f"> 🔒 **Haki Mastery:**        {c.haki_mastery_display}\n"
        f"> 🔒 **Combat Style:**        {c.fighting_style}"
    )

def _locked_threat(c: OnePieceCharacter) -> str:
    if c.affiliation == "Marine":
        bounty_line = f"> 🔒 **Marine Rank:**  {c.marine_rank}"
    elif c.affiliation == "World Noble":
        bounty_line = f"> 🔒 **Bounty:**       *Immune (World Noble)*"
    else:
        bounty_line = f"> 🔒 **Bounty:**       {c.bounty_display}"

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
# Reveal frame builders (clean, no 🔒)
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
    return (
        f"> **Weapon:**         {c.weapon_type}\n"
        f"> **Weapon Mastery:** {c.weapon_mastery}"
    )

def _reveal_power(c: OnePieceCharacter) -> str:
    return (
        f"> **Devil Fruit:**         {c.devil_fruit_display}\n"
        f"> **Devil Fruit Mastery:** {c.devil_fruit_mastery_display}\n"
        f"> **Haki Potential:**      {c.haki}\n"
        f"> **Haki Mastery:**        {c.haki_mastery_display}\n"
        f"> **Combat Style:**        {c.fighting_style}"
    )

def _reveal_threat(c: OnePieceCharacter) -> str:
    if c.affiliation == "Marine":
        bounty_line = f"> **Marine Rank:**  {c.marine_rank}"
    elif c.affiliation == "World Noble":
        bounty_line = f"> **Bounty:**       *Immune (World Noble)*"
    else:
        bounty_line = f"> **Bounty:**       {c.bounty_display}"

    return (
        f"> **Strength:**     {c.strength}\n"
        f"> **Speed:**        {c.speed}\n"
        f"> **Battle IQ:**    {c.battle_iq}\n"
        f"> **Endurance:**    {c.endurance}\n"
        f"> **Willpower:**    {c.willpower}\n"
        f"> **Rival:**        *{c.rival}*\n"
        f"> **World Threat:** {c.threat_level_display}\n"
        f"{bounty_line}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Animator
# ─────────────────────────────────────────────────────────────────────────────

class CharacterAnimator:
    """
    Handles the full phased reveal of a generated OnePieceCharacter.
    Fully decoupled from the generation engine.

    Flow:
        Phase 0 → Initial send   (blank canvas, 4 placeholder fields)
        Spin    → 8 ticks        (slot machine deceleration across all fields)
        Lock    → Snap frame     (real values + 🔒 on every line)
        Phase 1 → Core Identity  (🔒 removed, color → royal blue)
        Phase 2 → Weapon System  (color → sea green)
        Phase 3 → Power System   (color → burnt orange)
        Phase 4 → Threat/Stats   (color → gold, title upgrade, timestamp)
    """

    @classmethod
    async def animate_roll(
        cls,
        ctx: commands.Context,
        character: OnePieceCharacter,
    ) -> discord.Message:
        """Full animation sequence. Returns the final message object."""
        msg = await cls._send_initial(ctx, character)

        try:
            msg = await cls._spin_phase(msg, character)
            msg = await cls._reveal_phase_1(msg, character)
            msg = await cls._reveal_phase_2(msg, character)
            msg = await cls._reveal_phase_3(msg, character)
            msg = await cls._reveal_phase_4(msg, character)
        except discord.HTTPException as e:
            log.error(
                "CharacterAnimator edit failed for user %s in guild %s: %s",
                character.user_id, character.guild_id, e,
            )
            try:
                await msg.edit(embed=cls._build_final_embed(character))
            except discord.HTTPException:
                log.error("CharacterAnimator final fallback also failed — giving up.")

        return msg

    # ── Phase 0 ───────────────────────────────────────────────────────────────

    @classmethod
    async def _send_initial(
        cls,
        ctx: commands.Context,
        character: OnePieceCharacter,
    ) -> discord.Message:
        """Blank canvas. Seeds 4 placeholder fields to lock embed height."""
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

        return await ctx.send(embed=embed)

    # ── Spin phase ────────────────────────────────────────────────────────────

    @classmethod
    async def _spin_phase(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        """
        8-tick decelerating slot machine. All four fields cycle simultaneously.
        Final tick snaps to real values with 🔒 indicators.
        """
        embed = msg.embeds[0]
        embed.color = COLOR_SPIN

        total = len(SPIN_INTERVALS)

        for i, interval in enumerate(SPIN_INTERVALS):
            is_last = i == total - 1

            if is_last:
                embed.title = "🔒 Fate Sealed — Destiny Locked In..."
                id_val  = _locked_identity(character)
                wp_val  = _locked_weapon(character)
                pw_val  = _locked_power(character)
                th_val  = _locked_threat(character)
            else:
                id_val  = _spin_identity()
                wp_val  = _spin_weapon()
                pw_val  = _spin_power()
                th_val  = _spin_threat()

            embed.set_field_at(0, name="🧬 Core Identity",   value=id_val, inline=False)
            embed.set_field_at(1, name="⚔️  Weapon System",   value=wp_val, inline=False)
            embed.set_field_at(2, name="🌀 Power System",    value=pw_val, inline=False)
            embed.set_field_at(3, name="📊 Threat Analysis", value=th_val, inline=False)

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

        embed.set_field_at(1, name="⚔️  Weapon System",   value=_reveal_weapon(character), inline=False)
        embed.set_field_at(2, name="🌀 Power System",    value=SPINNER,                   inline=False)
        embed.set_field_at(3, name="📊 Threat Analysis", value=SPINNER,                   inline=False)

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

        embed.set_field_at(2, name="🌀 Power System",    value=_reveal_power(character), inline=False)
        embed.set_field_at(3, name="📊 Threat Analysis", value=SPINNER,                  inline=False)

        await msg.edit(embed=embed)
        return msg

    # ── Phase 4 — Threat Analysis (final) ─────────────────────────────────────

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

        await msg.edit(embed=embed)
        return msg

    # ── Fallback ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_final_embed(character: OnePieceCharacter) -> discord.Embed:
        """
        One-shot complete embed. Used as fallback if animation fails mid-way.
        """
        embed = discord.Embed(
            title=f"👑 {character.full_name}",
            description="*This is your permanent character sheet.*",
            color=COLOR_FINAL,
            timestamp=datetime.fromtimestamp(character.rolled_at, tz=timezone.utc),
        )
        embed.set_footer(text="One Piece Community • Character Generation")

        embed.add_field(
            name="🧬 Core Identity",
            value=_reveal_identity(character),
            inline=False,
        )
        embed.add_field(
            name="⚔️  Weapon System",
            value=_reveal_weapon(character),
            inline=False,
        )
        embed.add_field(
            name="🌀 Power System",
            value=_reveal_power(character),
            inline=False,
        )
        embed.add_field(
            name="📊 Threat Analysis",
            value=_reveal_threat(character),
            inline=False,
        )

        return embed