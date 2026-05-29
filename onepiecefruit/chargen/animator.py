"""
chargen/animator.py
─────────────────────────────────────────────────────────────────────────────
Asynchronous phased embed animator for character sheet reveals.

Rate limit strategy:
  Discord allows ~5 edits per 5s per message before issuing 429s.

  Phase 0  → 1 initial send
  Spin     → 8 edits over ~5.5s  (≈1 edit/0.69s — safe, well under threshold)
  Phase 1  → 1 edit after 2.0s delay
  Phase 2  → 1 edit after 2.0s delay
  Phase 3  → 1 edit after 2.5s delay
  Total edits: ~11 across ~12 seconds. Effective rate: ~0.92 edits/s.
  discord.py's HTTPClient handles transient 429s via retry-after automatically.

Spin phase design:
  - Cycles through random pool samples per stat, decelerating each round.
  - Intervals: [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0] → natural slowdown.
  - Final "locked" frame uses 🔒 emoji and bold text before transitioning
    into the existing phase 1/2/3 reveal flow unchanged.
  - Each spin tick shows ALL three fields cycling simultaneously, matching
    the viral "wheel of destiny" format where everything spins at once.

Design decisions:
  - embed.set_field_at() vs delete/re-add: preserves index positions,
    prevents embed height jumping during edits.
  - All three phase fields seeded as placeholders in initial send —
    embed height is locked from frame 0.
  - Color progression acts as a subconscious progress bar.
  - Phase 3 delay is 2.5s (vs 2.0s) for climax pacing.
  - Error handling: if any edit fails (network blip), we log and attempt
    the final state in one last effort rather than silently dying mid-reveal.
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
COLOR_DARK    = 0x1A1A2E   # Deep navy — initial blank canvas
COLOR_SPIN    = 0x6A0DAD   # Purple — slot machine spinning state
COLOR_PHASE_1 = 0x1A6DB5   # Royal blue — identity reveal
COLOR_PHASE_2 = 0xD4651A   # Burnt orange — power system reveal
COLOR_FINAL   = 0xF5C518   # IMDb gold — final stats reveal

# ── Timing constants ──────────────────────────────────────────────────────────
DELAY_PHASE_1 = 2.0
DELAY_PHASE_2 = 2.0
DELAY_PHASE_3 = 2.5

# Spin deceleration intervals in seconds — starts fast, slows to a stop
SPIN_INTERVALS = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]

# ── Placeholder / spin text ───────────────────────────────────────────────────
SPINNER = "🌀 *Calculating...*"

# ── Spin sample pools (display values shown during cycling) ──────────────────
_RACE_SAMPLES       = list(P.RACE.keys())
_AFFIL_SAMPLES      = list(P.AFFILIATION.keys())
_FRUIT_SAMPLES      = ["Paramecia", "Zoan", "Logia", "Ancient Zoan", "Mythical Zoan", "None"]
_HAKI_SAMPLES       = list(P.HAKI_POTENTIAL.keys())
_STYLE_SAMPLES      = list(P.FIGHTING_STYLE_OTHER.keys())
_STAT_SAMPLES       = list(P.STAT_TIER.keys())
_THREAT_SAMPLES     = [
    "⚪ Below Radar", "🔵 Notable Threat", "🟢 Super Rookie",
    "🟡 Warlord-Class", "🟠 Emperor's Crew Level", "🔴 Yonko-Class",
]
_BOUNTY_SAMPLES     = [
    "฿ 3,200,000", "฿ 44,000,000", "฿ 120,000,000",
    "฿ 340,000,000", "฿ 860,000,000", "฿ 2,400,000,000",
]


def _spin_identity_value() -> str:
    """Returns a random cycling identity block for the spin phase."""
    return (
        f"> **Race:**        {random.choice(_RACE_SAMPLES)}\n"
        f"> **Lineage:**     ???\n"
        f"> **Affiliation:** {random.choice(_AFFIL_SAMPLES)}\n"
        f"> **Epithet:**     *\"...\"*"
    )


def _spin_power_value() -> str:
    """Returns a random cycling power block for the spin phase."""
    return (
        f"> **Devil Fruit:**    {random.choice(_FRUIT_SAMPLES)}\n"
        f"> **Haki Potential:** {random.choice(_HAKI_SAMPLES)}\n"
        f"> **Combat Style:**   {random.choice(_STYLE_SAMPLES)}"
    )


def _spin_threat_value() -> str:
    """Returns a random cycling threat block for the spin phase."""
    return (
        f"> **Strength:**     {random.choice(_STAT_SAMPLES)}\n"
        f"> **Speed:**        {random.choice(_STAT_SAMPLES)}\n"
        f"> **Battle IQ:**    {random.choice(_STAT_SAMPLES)}\n"
        f"> **World Threat:** {random.choice(_THREAT_SAMPLES)}\n"
        f"> **Bounty:**       {random.choice(_BOUNTY_SAMPLES)}"
    )


def _locked_identity_value(character: OnePieceCharacter) -> str:
    """Final locked identity block shown at end of spin before phase 1 reveal."""
    return (
        f"> 🔒 **Race:**        {character.race}\n"
        f"> 🔒 **Lineage:**     {character.d_clan_display}\n"
        f"> 🔒 **Affiliation:** {character.affiliation}\n"
        f"> 🔒 **Epithet:**     *\"{character.epithet}\"*"
    )


def _locked_power_value(character: OnePieceCharacter) -> str:
    """Final locked power block shown at end of spin before phase 2 reveal."""
    return (
        f"> 🔒 **Devil Fruit:**    {character.devil_fruit_display}\n"
        f"> 🔒 **Haki Potential:** {character.haki}\n"
        f"> 🔒 **Combat Style:**   {character.fighting_style}"
    )


def _locked_threat_value(character: OnePieceCharacter) -> str:
    """Final locked threat block shown at end of spin before phase 3 reveal."""
    if character.affiliation == "Marine":
        bounty_line = f"> 🔒 **Marine Rank:**  {character.marine_rank}"
    elif character.affiliation == "World Noble":
        bounty_line = f"> 🔒 **Bounty:**       *Immune (World Noble)*"
    else:
        bounty_line = f"> 🔒 **Bounty:**       {character.bounty_display}"

    return (
        f"> 🔒 **Strength:**     {character.strength}\n"
        f"> 🔒 **Speed:**        {character.speed}\n"
        f"> 🔒 **Battle IQ:**    {character.battle_iq}\n"
        f"> 🔒 **World Threat:** {character.threat_level_display}\n"
        f"{bounty_line}"
    )


class CharacterAnimator:
    """
    Handles the phased reveal of a generated OnePieceCharacter.
    Fully decoupled from the generation engine — accepts any pre-built character.

    Flow:
        Phase 0  → Initial send (blank canvas, locked field layout)
        Spin     → 8 ticks of decelerating slot-machine cycling
        Lock     → All three fields snap to real values with 🔒 indicators
        Phase 1  → Core Identity revealed (color shift, 🔒 removed)
        Phase 2  → Power System revealed
        Phase 3  → Stats + Threat + Bounty final reveal
    """

    @classmethod
    async def animate_roll(
        cls,
        ctx: commands.Context,
        character: OnePieceCharacter,
    ) -> discord.Message:
        """
        Full animation sequence. Returns the final message object.
        Total wall time: ~12 seconds.
        """
        msg = await cls._send_initial(ctx, character)

        try:
            msg = await cls._spin_phase(msg, character)
            msg = await cls._reveal_phase_1(msg, character)
            msg = await cls._reveal_phase_2(msg, character)
            msg = await cls._reveal_phase_3(msg, character)
        except discord.HTTPException as e:
            log.error(
                "CharacterAnimator edit failed for user %s in guild %s: %s",
                character.user_id, character.guild_id, e,
            )
            try:
                await msg.edit(embed=cls._build_final_embed(character))
            except discord.HTTPException:
                log.error("CharacterAnimator final fallback edit also failed — giving up.")

        return msg

    # ─────────────────────────────────────────────────────────────────────────
    # Phase builders
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    async def _send_initial(
        cls,
        ctx: commands.Context,
        character: OnePieceCharacter,
    ) -> discord.Message:
        """
        Phase 0 — Blank canvas. Seeds all three fields as placeholders
        to lock embed height before the spin phase begins.
        """
        embed = discord.Embed(
            title="🎰 The Wheel of Destiny Spins...",
            description=(
                f"*The fate of **{character.display_name}** hangs in the balance...*"
            ),
            color=COLOR_DARK,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="One Piece Community • Character Generation")

        embed.add_field(name="🧬 Core Identity",   value=SPINNER, inline=False)
        embed.add_field(name="🌀 Power System",    value=SPINNER, inline=False)
        embed.add_field(name="📊 Threat Analysis", value=SPINNER, inline=False)

        return await ctx.send(embed=embed)

    @classmethod
    async def _spin_phase(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        """
        Slot machine spin — cycles through random values across all three
        fields simultaneously, decelerating across SPIN_INTERVALS ticks.
        Final tick snaps to real locked values with 🔒 indicators.
        """
        embed = msg.embeds[0]
        embed.color = COLOR_SPIN
        embed.title = "🎰 The Wheel of Destiny Spins..."

        total_ticks = len(SPIN_INTERVALS)

        for i, interval in enumerate(SPIN_INTERVALS):
            is_last = i == total_ticks - 1

            if is_last:
                # Final tick — snap to real values with lock indicators
                identity_val = _locked_identity_value(character)
                power_val    = _locked_power_value(character)
                threat_val   = _locked_threat_value(character)
                embed.title  = "🔒 Fate Sealed — Destiny Locked In..."
            else:
                # Cycling tick — random values
                identity_val = _spin_identity_value()
                power_val    = _spin_power_value()
                threat_val   = _spin_threat_value()

            embed.set_field_at(0, name="🧬 Core Identity",   value=identity_val, inline=False)
            embed.set_field_at(1, name="🌀 Power System",    value=power_val,    inline=False)
            embed.set_field_at(2, name="📊 Threat Analysis", value=threat_val,   inline=False)

            await msg.edit(embed=embed)
            await asyncio.sleep(interval)

        return msg

    @classmethod
    async def _reveal_phase_1(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        """Phase 1 — Core Identity reveal. Removes 🔒 indicators, shifts color."""
        await asyncio.sleep(DELAY_PHASE_1)

        embed = msg.embeds[0]
        embed.color = COLOR_PHASE_1
        embed.title = f"🏴‍☠️ The Grand Line Stirs..."
        embed.description = (
            f"*The fate of **{character.display_name}** is being written "
            f"into the tides of history...*"
        )

        identity_lines = [
            f"> **Race:**        {character.race}",
            f"> **Lineage:**     {character.d_clan_display}",
            f"> **Affiliation:** {character.affiliation}",
            f"> **Epithet:**     *\"{character.epithet}\"*",
        ]

        embed.set_field_at(0, name="🧬 Core Identity",   value="\n".join(identity_lines), inline=False)
        embed.set_field_at(1, name="🌀 Power System",    value=SPINNER,                   inline=False)
        embed.set_field_at(2, name="📊 Threat Analysis", value=SPINNER,                   inline=False)

        await msg.edit(embed=embed)
        return msg

    @classmethod
    async def _reveal_phase_2(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        """Phase 2 — Power System reveal."""
        await asyncio.sleep(DELAY_PHASE_2)

        embed = msg.embeds[0]
        embed.color = COLOR_PHASE_2

        power_lines = [
            f"> **Devil Fruit:**    {character.devil_fruit_display}",
            f"> **Haki Potential:** {character.haki}",
            f"> **Combat Style:**   {character.fighting_style}",
        ]

        embed.set_field_at(1, name="🌀 Power System",    value="\n".join(power_lines), inline=False)
        embed.set_field_at(2, name="📊 Threat Analysis", value=SPINNER,                inline=False)

        await msg.edit(embed=embed)
        return msg

    @classmethod
    async def _reveal_phase_3(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        """Phase 3 — Final stats, threat level, and bounty/rank reveal."""
        await asyncio.sleep(DELAY_PHASE_3)

        embed = msg.embeds[0]
        embed.color = COLOR_FINAL

        if character.affiliation == "Marine":
            bounty_line = f"> **Marine Rank:**  {character.marine_rank}"
        elif character.affiliation == "World Noble":
            bounty_line = f"> **Bounty:**       *Immune (World Noble)*"
        else:
            bounty_line = f"> **Bounty:**       {character.bounty_display}"

        threat_lines = [
            f"> **Strength:**    {character.strength}",
            f"> **Speed:**       {character.speed}",
            f"> **Battle IQ:**   {character.battle_iq}",
            f"> **World Threat:** {character.threat_level_display}",
            bounty_line,
        ]

        embed.set_field_at(2, name="📊 Threat Analysis", value="\n".join(threat_lines), inline=False)

        embed.title = f"👑 {character.full_name}"
        embed.description = (
            f"*This is your permanent character sheet. "
            f"The Grand Line does not give second chances.*"
        )
        embed.timestamp = datetime.fromtimestamp(character.rolled_at, tz=timezone.utc)

        await msg.edit(embed=embed)
        return msg

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_final_embed(character: OnePieceCharacter) -> discord.Embed:
        """
        Builds the fully completed embed in one shot.
        Used only as a fallback when the phased animation fails mid-way.
        """
        embed = discord.Embed(
            title=f"👑 {character.full_name}",
            description="*This is your permanent character sheet.*",
            color=COLOR_FINAL,
            timestamp=datetime.fromtimestamp(character.rolled_at, tz=timezone.utc),
        )

        embed.add_field(
            name="🧬 Core Identity",
            value=(
                f"> **Race:**        {character.race}\n"
                f"> **Lineage:**     {character.d_clan_display}\n"
                f"> **Affiliation:** {character.affiliation}\n"
                f"> **Epithet:**     *\"{character.epithet}\"*"
            ),
            inline=False,
        )
        embed.add_field(
            name="🌀 Power System",
            value=(
                f"> **Devil Fruit:**    {character.devil_fruit_display}\n"
                f"> **Haki Potential:** {character.haki}\n"
                f"> **Combat Style:**   {character.fighting_style}"
            ),
            inline=False,
        )

        if character.affiliation == "Marine":
            bounty_line = f"> **Marine Rank:**  {character.marine_rank}"
        elif character.affiliation == "World Noble":
            bounty_line = f"> **Bounty:**       *Immune (World Noble)*"
        else:
            bounty_line = f"> **Bounty:**       {character.bounty_display}"

        embed.add_field(
            name="📊 Threat Analysis",
            value=(
                f"> **Strength:**     {character.strength}\n"
                f"> **Speed:**        {character.speed}\n"
                f"> **Battle IQ:**    {character.battle_iq}\n"
                f"> **World Threat:** {character.threat_level_display}\n"
                f"{bounty_line}"
            ),
            inline=False,
        )

        embed.set_footer(text="One Piece Community • Character Generation")
        return embed