"""
chargen/animator.py
─────────────────────────────────────────────────────────────────────────────
Asynchronous phased embed animator for character sheet reveals.

Rate limit strategy:
  Discord allows ~5 edits per 5s per message before issuing 429s.
  We emit 4 edits total across ~8.5 seconds of total wall time.
  Effective rate: 1 edit per ~2.1 seconds — well under the threshold.
  discord.py's HTTPClient will handle transient 429s automatically via
  retry-after, but at this pace we should never trigger one.

Design decisions:
  - embed.set_field_at() vs delete/re-add: set_field_at() preserves index
    positions and prevents the embed "jumping" during edits.
  - All three phase fields are seeded as placeholder rows in the initial
    send, so the embed height is locked from frame 0. No layout shift.
  - Color progression acts as a subconscious progress bar.
  - Phase 3 delay is 2.5s (vs 2.0s) for climax pacing.
  - Error handling: if any edit fails (network blip), we log and attempt
    the final state in one last effort rather than silently dying mid-reveal.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import discord
from redbot.core import commands

from .models import OnePieceCharacter

log = logging.getLogger("red.OnePieceFruit.chargen")

# ── Color constants ────────────────────────────────────────────────────────────
COLOR_DARK    = 0x1A1A2E   # Deep navy — initial blank canvas
COLOR_PHASE_1 = 0x1A6DB5   # Royal blue — identity reveal
COLOR_PHASE_2 = 0xD4651A   # Burnt orange — power system reveal
COLOR_FINAL   = 0xF5C518   # IMDb gold — final stats reveal

# ── Timing constants ──────────────────────────────────────────────────────────
DELAY_PHASE_1 = 2.0   # seconds before revealing identity
DELAY_PHASE_2 = 2.0   # seconds before revealing powers
DELAY_PHASE_3 = 2.5   # slightly longer for climax feel

# ── Placeholder text ──────────────────────────────────────────────────────────
SPINNER = "🌀 *Calculating...*"


class CharacterAnimator:
    """
    Handles the phased reveal of a generated OnePieceCharacter.
    Fully decoupled from the generation engine — accepts any pre-built character.
    """

    @classmethod
    async def animate_roll(
        cls,
        ctx: commands.Context,
        character: OnePieceCharacter,
    ) -> discord.Message:
        """
        Executes the 3-phase embed animation and returns the final message.
        Total execution time: ~6.5–7 seconds.

        Phases:
          0 → Initial send with placeholders
          1 → Core identity revealed (Race, D-Clan, Affiliation, Epithet)
          2 → Power system revealed (Devil Fruit, Haki, Fighting Style)
          3 → Stats + Threat Level + Bounty/Rank final reveal
        """
        msg = await cls._send_initial(ctx, character)

        try:
            msg = await cls._reveal_phase_1(msg, character)
            msg = await cls._reveal_phase_2(msg, character)
            msg = await cls._reveal_phase_3(msg, character)
        except discord.HTTPException as e:
            log.error(
                "CharacterAnimator edit failed for user %s in guild %s: %s",
                character.user_id, character.guild_id, e,
            )
            # Best-effort: try to push the fully completed embed in one final edit
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
        Phase 0 — Send the blank canvas with three locked placeholder fields.
        Locking the field count here prevents layout shift on subsequent edits.
        """
        embed = discord.Embed(
            title=f"🏴‍☠️ The Grand Line Stirs...",
            description=(
                f"*The fate of **{character.display_name}** is being written "
                f"into the tides of history...*"
            ),
            color=COLOR_DARK,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="One Piece Community • Character Generation")

        # Seed all three fields as placeholders — index positions are now locked
        embed.add_field(name="🧬 Core Identity",   value=SPINNER, inline=False)
        embed.add_field(name="🌀 Power System",    value=SPINNER, inline=False)
        embed.add_field(name="📊 Threat Analysis", value=SPINNER, inline=False)

        return await ctx.send(embed=embed)

    @classmethod
    async def _reveal_phase_1(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        """Phase 1 — Core Identity reveal after suspense delay."""
        await asyncio.sleep(DELAY_PHASE_1)

        embed = msg.embeds[0]
        embed.color = COLOR_PHASE_1

        d_flag = " 🇩" if character.is_d_clan else ""
        identity_lines = [
            f"> **Race:**        {character.race}",
            f"> **Lineage:**     {character.d_clan_display}",
            f"> **Affiliation:** {character.affiliation}",
            f"> **Epithet:**     *\"{character.epithet}\"*",
        ]

        embed.set_field_at(
            0,
            name="🧬 Core Identity",
            value="\n".join(identity_lines),
            inline=False,
        )
        # Phase 2 still spinning
        embed.set_field_at(1, name="🌀 Power System",    value=SPINNER, inline=False)
        embed.set_field_at(2, name="📊 Threat Analysis", value=SPINNER, inline=False)

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

        embed.set_field_at(
            1,
            name="🌀 Power System",
            value="\n".join(power_lines),
            inline=False,
        )
        # Phase 3 still spinning
        embed.set_field_at(2, name="📊 Threat Analysis", value=SPINNER, inline=False)

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

        # Bounty vs Rank conditional block
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

        embed.set_field_at(
            2,
            name="📊 Threat Analysis",
            value="\n".join(threat_lines),
            inline=False,
        )

        # Final title + description upgrade
        embed.title = f"👑 {character.full_name}"
        embed.description = (
            f"*This is your permanent character sheet. "
            f"The Grand Line does not give second chances.*"
        )

        # Timestamp on final reveal
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