"""
chargen/animator.py
─────────────────────────────────────────────────────────────────────────────
Asynchronous phased embed animator — Manga Panel edition.

Theme: High-contrast black/white with red highlights.
Layout: 3-field infographic. Weapon merged into Combat Profile.

Field structure:
  🧬  Identity       — Race, Lineage, Affiliation, Origin, Epithet
  ⚔️   Combat Profile — Weapon + mastery bar, Devil Fruit, Haki, Style
  📊  Stats & Threat — 5 stat bars, Rival, Threat level, Bounty

Color progression (manga panel):
  Spin    0x111111  near-black — slot machine
  Lock    0xCC0000  blood red  — fate sealed flash
  Phase 1 0xDDDDDD  off-white  — identity reveal
  Phase 2 0xCC0000  red        — combat profile reveal
  Final   0xFFFFFF  white      — full sheet, clean

Rate limit:
  8 spin edits + 3 phase edits = 11 total across ~12s. ~0.92/s. Safe.

Components V2 (spin phase only):
  [📣 Share Sheet]  [⚔️ View Rival]  [🎲 Re-roll?]
  Stripped on final reveal via view=None.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone

import discord
from discord import ui
from redbot.core import commands

from .models import OnePieceCharacter
from . import pools as P

log = logging.getLogger("red.OnePieceFruit.chargen")

# ── Manga panel color palette ─────────────────────────────────────────────────
COLOR_VOID    = 0x111111   # Near-black  — spin phase
COLOR_BLOOD   = 0xCC0000   # Blood red   — lock flash
COLOR_INK     = 0xDDDDDD   # Off-white   — identity reveal (ink on paper)
COLOR_RED     = 0xCC0000   # Red         — combat profile reveal
COLOR_CLEAN   = 0xFFFFFF   # Pure white  — final complete sheet

# ── Timing ────────────────────────────────────────────────────────────────────
SPIN_INTERVALS = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
DELAY_PHASE_1  = 2.0   # Identity reveal
DELAY_PHASE_2  = 2.0   # Combat profile reveal
DELAY_PHASE_3  = 2.5   # Stats reveal (climax)

# ── Placeholder ───────────────────────────────────────────────────────────────
SPINNER  = "```\n[ CALCULATING... ]\n```"
REDACTED = "```\n[ REDACTED       ]\n```"

# ── Spin sample pools ─────────────────────────────────────────────────────────
_RACE_S   = list(P.RACE.keys())
_AFFIL_S  = list(P.AFFILIATION.keys())
_ORIGIN_S = list(P.ORIGIN.keys())
_WEAPON_S = list(P.WEAPON_TYPE.keys())
_WMAST_S  = list(P.WEAPON_MASTERY.keys())
_FRUIT_S  = ["Paramecia", "Zoan", "Logia", "Ancient Zoan", "Mythical Zoan", "None"]
_HAKI_S   = list(P.HAKI_POTENTIAL.keys())
_STYLE_S  = list(P.FIGHTING_STYLE_OTHER.keys())
_STAT_S   = list(P.STAT_TIER.keys())
_RIVAL_S  = list(P.RIVAL.keys())
_THREAT_S = [
    "⚪ Below Radar", "🔵 Notable Threat", "🟢 Super Rookie",
    "🟡 Warlord-Class", "🟠 Emperor's Crew Level", "🔴 Yonko-Class",
]
_BOUNTY_S = [
    "฿ 3,200,000", "฿ 44,000,000", "฿ 120,000,000",
    "฿ 340,000,000", "฿ 860,000,000", "฿ 2,400,000,000",
]

# ── Weapon mastery key order (for bar position) ───────────────────────────────
_WMAST_KEYS = list(P.WEAPON_MASTERY.keys())


# ─────────────────────────────────────────────────────────────────────────────
# Bar helpers
# ─────────────────────────────────────────────────────────────────────────────

def _stat_bar(tier: str, width: int = 10) -> str:
    """Block-fill bar from STAT_TIER_VALUE. e.g. B-Tier → ██████░░░░ 58%"""
    val    = P.STAT_TIER_VALUE.get(tier, 0)
    filled = round(val / 100 * width)
    empty  = width - filled
    return f"{'█' * filled}{'░' * empty} {val}%"


def _mastery_bar(mastery: str | None, width: int = 10) -> str:
    """Position-derived bar from weapon mastery key order."""
    if mastery is None or mastery not in _WMAST_KEYS:
        return "░" * width + "  0%"
    idx    = _WMAST_KEYS.index(mastery)
    val    = round((idx / max(len(_WMAST_KEYS) - 1, 1)) * 100)
    filled = round(val / 100 * width)
    empty  = width - filled
    return f"{'█' * filled}{'░' * empty} {val}%"


def _random_bar(width: int = 10) -> str:
    """Random spin bar for visual noise during slot machine phase."""
    filled = random.randint(1, width - 1)
    val    = round(filled / width * 100)
    return f"{'█' * filled}{'░' * (width - filled)} {val}%"


# ─────────────────────────────────────────────────────────────────────────────
# Divider helper — manga panel section rule
# ─────────────────────────────────────────────────────────────────────────────

DIV = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"


# ─────────────────────────────────────────────────────────────────────────────
# Spin frame builders
# ─────────────────────────────────────────────────────────────────────────────

def _spin_identity() -> str:
    return (
        f"**RACE ——**  {random.choice(_RACE_S)}\n"
        f"**LINEAGE —** `???`\n"
        f"**CREW ———** {random.choice(_AFFIL_S)}\n"
        f"**ORIGIN ——** {random.choice(_ORIGIN_S)}\n"
        f"**EPITHET —** *\"...\"*"
    )


def _spin_combat() -> str:
    return (
        f"**WEAPON ——** {random.choice(_WEAPON_S)}\n"
        f"**MASTERY —** {random.choice(_WMAST_S)}\n"
        f"`{_random_bar()}`\n"
        f"{DIV}\n"
        f"**FRUIT ———** {random.choice(_FRUIT_S)}\n"
        f"**HAKI ————** {random.choice(_HAKI_S)}\n"
        f"**STYLE ———** {random.choice(_STYLE_S)}"
    )


def _spin_stats() -> str:
    r = lambda: random.choice(_STAT_S)
    return (
        f"**STR** {r()}  `{_random_bar()}`\n"
        f"**SPD** {r()}  `{_random_bar()}`\n"
        f"**IQ ·** {r()}  `{_random_bar()}`\n"
        f"**END** {r()}  `{_random_bar()}`\n"
        f"**WIL** {r()}  `{_random_bar()}`\n"
        f"{DIV}\n"
        f"**RIVAL ———** {random.choice(_RIVAL_S)}\n"
        f"**THREAT ——** {random.choice(_THREAT_S)}\n"
        f"**BOUNTY ——** {random.choice(_BOUNTY_S)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Locked frame builders (real values + 🔒)
# ─────────────────────────────────────────────────────────────────────────────

def _locked_identity(c: OnePieceCharacter) -> str:
    return (
        f"🔒 **RACE ——**  {c.race}\n"
        f"🔒 **LINEAGE —** {c.d_clan_display}\n"
        f"🔒 **CREW ———** {c.affiliation}\n"
        f"🔒 **ORIGIN ——** {c.origin}\n"
        f"🔒 **EPITHET —** *\"{c.epithet}\"*"
    )


def _locked_combat(c: OnePieceCharacter) -> str:
    bar = _mastery_bar(c.weapon_mastery)
    lines = [
        f"🔒 **WEAPON ——** {c.weapon_type}",
        f"🔒 **MASTERY —** {c.weapon_mastery}",
        f"`{bar}`",
        DIV,
        f"🔒 **FRUIT ———** {c.devil_fruit_display}",
    ]
    if c.has_devil_fruit:
        lines.append(f"🔒 **FRUIT LVL** {c.devil_fruit_mastery_display}")
    lines.append(f"🔒 **HAKI ————** {c.haki}")
    if c.haki != "None":
        lines.append(f"🔒 **HAKI LVL ·** {c.haki_mastery_display}")
    lines.append(f"🔒 **STYLE ———** {c.fighting_style}")
    return "\n".join(lines)


def _locked_stats(c: OnePieceCharacter) -> str:
    bl = _bounty_line(c, locked=True)
    return (
        f"🔒 **STR** {c.strength}  `{_stat_bar(c.strength)}`\n"
        f"🔒 **SPD** {c.speed}  `{_stat_bar(c.speed)}`\n"
        f"🔒 **IQ ·** {c.battle_iq}  `{_stat_bar(c.battle_iq)}`\n"
        f"🔒 **END** {c.endurance}  `{_stat_bar(c.endurance)}`\n"
        f"🔒 **WIL** {c.willpower}  `{_stat_bar(c.willpower)}`\n"
        f"{DIV}\n"
        f"🔒 **RIVAL ———** *{c.rival}*\n"
        f"🔒 **THREAT ——** {c.threat_level_display}\n"
        f"{bl}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Reveal frame builders (clean, no 🔒)
# ─────────────────────────────────────────────────────────────────────────────

def _reveal_identity(c: OnePieceCharacter) -> str:
    return (
        f"**RACE ——**  {c.race}\n"
        f"**LINEAGE —** {c.d_clan_display}\n"
        f"**CREW ———** {c.affiliation}\n"
        f"**ORIGIN ——** {c.origin}\n"
        f"**EPITHET —** *\"{c.epithet}\"*"
    )


def _reveal_combat(c: OnePieceCharacter) -> str:
    bar = _mastery_bar(c.weapon_mastery)
    lines = [
        f"**WEAPON ——** {c.weapon_type}",
        f"**MASTERY —** {c.weapon_mastery}",
        f"`{bar}`",
        DIV,
        f"**FRUIT ———** {c.devil_fruit_display}",
    ]
    if c.has_devil_fruit:
        lines.append(f"**FRUIT LVL** {c.devil_fruit_mastery_display}")
    lines.append(f"**HAKI ————** {c.haki}")
    if c.haki != "None":
        lines.append(f"**HAKI LVL ·** {c.haki_mastery_display}")
    lines.append(f"**STYLE ———** {c.fighting_style}")
    return "\n".join(lines)


def _reveal_stats(c: OnePieceCharacter) -> str:
    bl = _bounty_line(c, locked=False)
    return (
        f"**STR** {c.strength}  `{_stat_bar(c.strength)}`\n"
        f"**SPD** {c.speed}  `{_stat_bar(c.speed)}`\n"
        f"**IQ ·** {c.battle_iq}  `{_stat_bar(c.battle_iq)}`\n"
        f"**END** {c.endurance}  `{_stat_bar(c.endurance)}`\n"
        f"**WIL** {c.willpower}  `{_stat_bar(c.willpower)}`\n"
        f"{DIV}\n"
        f"**RIVAL ———** *{c.rival}*\n"
        f"**THREAT ——** {c.threat_level_display}\n"
        f"{bl}"
    )


def _bounty_line(c: OnePieceCharacter, locked: bool = False) -> str:
    lock = "🔒 " if locked else ""
    if c.affiliation == "Marine":
        return f"{lock}**RANK ————** {c.marine_rank}"
    if c.affiliation == "World Noble":
        return f"{lock}**BOUNTY ——** *Immune — World Noble*"
    return f"{lock}**BOUNTY ——** {c.bounty_display}"


# ─────────────────────────────────────────────────────────────────────────────
# Components V2
# ─────────────────────────────────────────────────────────────────────────────

class CharGenView(ui.View):
    """
    Three buttons shown during spin phase only.
    Stripped on final reveal by passing view=None to msg.edit().
    Times out after 120s as a safety net.
    """

    def __init__(self, character: OnePieceCharacter, roller: discord.Member):
        super().__init__(timeout=120)
        self.character = character
        self.roller    = roller

    @ui.button(label="📣 Share Sheet", style=discord.ButtonStyle.secondary)
    async def share_sheet(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        c = self.character
        embed = discord.Embed(
            title=f"📋 {c.full_name}",
            description=(
                f"**{self.roller.mention}**'s character sheet:\n\n"
                f"**Race:** {c.race}  ·  **Crew:** {c.affiliation}\n"
                f"**Fruit:** {c.devil_fruit_display}\n"
                f"**Haki:** {c.haki}\n"
                f"**Weapon:** {c.weapon_type} — *{c.weapon_mastery}*\n"
                f"**Rival:** *{c.rival}*  ·  **Threat:** {c.threat_level_display}"
            ),
            color=COLOR_RED,
        )
        embed.set_thumbnail(url=self.roller.display_avatar.url)
        embed.set_footer(text="One Piece Community • Character Generation")
        await interaction.response.send_message(embed=embed)

    @ui.button(label="⚔️ View Rival", style=discord.ButtonStyle.primary)
    async def view_rival(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        rival_name = self.character.rival
        lore = P.RIVAL_LORE.get(
            rival_name,
            f"*{rival_name}* — their name carries weight on the seas. "
            f"Their full story has yet to be written into history.",
        )
        embed = discord.Embed(
            title=f"⚔️ RIVAL DOSSIER — {rival_name}",
            description=lore,
            color=COLOR_BLOOD,
        )
        embed.set_footer(text="One Piece Community • Rival Intel")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="🎲 Re-roll?", style=discord.ButtonStyle.danger)
    async def reroll_warning(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        await interaction.response.send_message(
            "**THE GRAND LINE GRANTS NO SECOND CHANCES.**\n\n"
            "Your character sheet is permanent. The sea does not give refunds.\n"
            "Only a server admin with `chardelete` can reset your record.",
            ephemeral=True,
        )

    async def on_timeout(self) -> None:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Animator
# ─────────────────────────────────────────────────────────────────────────────

class CharacterAnimator:
    """
    Manga panel phased reveal. 3 fields, infographic layout.

    Flow:
        Phase 0 → Initial send   (3 REDACTED placeholders + components)
        Spin    → 8 ticks        (slot-machine across all 3 fields, decelerating)
        Lock    → Snap frame     (real values + 🔒, embed turns blood red)
        Phase 1 → Identity       (🔒 removed, embed off-white)
        Phase 2 → Combat Profile (embed red)
        Phase 3 → Stats & Threat (embed white, title upgrade, timestamp,
                                  components stripped)
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
        except discord.HTTPException as exc:
            log.error(
                "CharacterAnimator failed user=%s guild=%s: %s",
                character.user_id, character.guild_id, exc,
            )
            try:
                await msg.edit(embed=cls._build_final_embed(character), view=None)
            except discord.HTTPException:
                log.error("CharacterAnimator fallback also failed — giving up.")

        return msg

    # ── Phase 0 — Initial send ────────────────────────────────────────────────

    @classmethod
    async def _send_initial(
        cls,
        ctx: commands.Context,
        character: OnePieceCharacter,
        view: CharGenView,
    ) -> discord.Message:
        embed = discord.Embed(
            title="▓▓▓ ACCESSING BUSTER CALL ARCHIVES... ▓▓▓",
            description=(
                f"*Scanning for **{character.display_name}**...*\n"
                f"*World Government clearance required.*"
            ),
            color=COLOR_VOID,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="One Piece Community  •  Character Generation")

        embed.add_field(name="🧬  IDENTITY",        value=REDACTED, inline=False)
        embed.add_field(name="⚔️   COMBAT PROFILE",  value=REDACTED, inline=False)
        embed.add_field(name="📊  STATS & THREAT",  value=REDACTED, inline=False)

        return await ctx.send(embed=embed, view=view)

    # ── Spin phase ────────────────────────────────────────────────────────────

    @classmethod
    async def _spin_phase(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        embed = msg.embeds[0]
        total = len(SPIN_INTERVALS)

        for i, interval in enumerate(SPIN_INTERVALS):
            is_last = i == total - 1

            if is_last:
                embed.color = COLOR_BLOOD
                embed.title = "🔴  SUBJECT IDENTIFIED — FATE SEALED"
                id_v = _locked_identity(character)
                cb_v = _locked_combat(character)
                st_v = _locked_stats(character)
            else:
                # Ramp color from void toward blood over the spin
                progress = i / (total - 1)
                r = int(0x11 + (0xCC - 0x11) * progress)
                embed.color = (r << 16)
                embed.title = f"▓ CROSS-REFERENCING... {'█' * (i + 1)}{'░' * (total - 1 - i)}"
                id_v = _spin_identity()
                cb_v = _spin_combat()
                st_v = _spin_stats()

            embed.set_field_at(0, name="🧬  IDENTITY",       value=id_v, inline=False)
            embed.set_field_at(1, name="⚔️   COMBAT PROFILE", value=cb_v, inline=False)
            embed.set_field_at(2, name="📊  STATS & THREAT", value=st_v, inline=False)

            await msg.edit(embed=embed)
            await asyncio.sleep(interval)

        return msg

    # ── Phase 1 — Identity ────────────────────────────────────────────────────

    @classmethod
    async def _reveal_phase_1(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        await asyncio.sleep(DELAY_PHASE_1)

        embed = msg.embeds[0]
        embed.color = COLOR_INK
        embed.title = f"[ IDENTITY CONFIRMED ]"
        embed.description = (
            f"*The ink dries on **{character.display_name}**'s record...*"
        )

        embed.set_field_at(0, name="🧬  IDENTITY",       value=_reveal_identity(character), inline=False)
        embed.set_field_at(1, name="⚔️   COMBAT PROFILE", value=SPINNER,                     inline=False)
        embed.set_field_at(2, name="📊  STATS & THREAT", value=SPINNER,                     inline=False)

        await msg.edit(embed=embed)
        return msg

    # ── Phase 2 — Combat Profile ──────────────────────────────────────────────

    @classmethod
    async def _reveal_phase_2(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        await asyncio.sleep(DELAY_PHASE_2)

        embed = msg.embeds[0]
        embed.color = COLOR_RED
        embed.title = "[ COMBAT PROFILE UNLOCKED ]"
        embed.description = "*Threat assessment in progress...*"

        embed.set_field_at(1, name="⚔️   COMBAT PROFILE", value=_reveal_combat(character), inline=False)
        embed.set_field_at(2, name="📊  STATS & THREAT", value=SPINNER,                   inline=False)

        await msg.edit(embed=embed)
        return msg

    # ── Phase 3 — Stats & Threat (final) ─────────────────────────────────────

    @classmethod
    async def _reveal_phase_3(
        cls,
        msg: discord.Message,
        character: OnePieceCharacter,
    ) -> discord.Message:
        await asyncio.sleep(DELAY_PHASE_3)

        embed = msg.embeds[0]
        embed.color = COLOR_CLEAN
        embed.title = f"👑  {character.full_name}"
        embed.description = (
            "*This is your permanent, living record.\n"
            "The Grand Line does not give second chances.*"
        )
        embed.timestamp = datetime.fromtimestamp(character.rolled_at, tz=timezone.utc)

        embed.set_field_at(2, name="📊  STATS & THREAT", value=_reveal_stats(character), inline=False)

        await msg.edit(embed=embed, view=None)
        return msg

    # ── Fallback ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_final_embed(character: OnePieceCharacter) -> discord.Embed:
        embed = discord.Embed(
            title=f"👑  {character.full_name}",
            description="*This is your permanent, living record.*",
            color=COLOR_CLEAN,
            timestamp=datetime.fromtimestamp(character.rolled_at, tz=timezone.utc),
        )
        embed.set_footer(text="One Piece Community  •  Character Generation")
        embed.add_field(name="🧬  IDENTITY",       value=_reveal_identity(character), inline=False)
        embed.add_field(name="⚔️   COMBAT PROFILE", value=_reveal_combat(character),  inline=False)
        embed.add_field(name="📊  STATS & THREAT", value=_reveal_stats(character),    inline=False)
        return embed