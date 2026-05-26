"""
ui/embeds.py — Standardised discord.Embed builders for every game state.

All embeds go through this module. No raw Embed construction elsewhere.
Colour constants use Discord's integer format (0xRRGGBB).

Embed inventory:
  round_start      — macro map sent at round open
  micro_prompt     — ephemeral embed shown when player selects a macro sector
  guess_confirmed  — ephemeral acknowledgement after Lock In
  round_locked     — edit of the original embed when the timer expires
  reveal           — final composite image + scoreboard
  leaderboard      — all-time stats for the guild
  pack_list        — admin: available World Packs
  error            — generic error state
"""

from __future__ import annotations

from typing import Optional

import discord

from ..models.coordinates import MacroSector, GridPoint
from ..models.session import GameSession, PlayerGuess, RoundPhase

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

COLOUR_ACTIVE   = 0x5865F2   # Discord blurple — round is live
COLOUR_LOCKED   = 0xED4245   # Discord red — timer expired
COLOUR_REVEAL   = 0xF0B132   # Gold — answer reveal
COLOUR_SUCCESS  = 0x57F287   # Green — player confirmed
COLOUR_NEUTRAL  = 0x2B2D31   # Dark neutral — info/admin
COLOUR_ERROR    = 0xED4245   # Red — error state


# ---------------------------------------------------------------------------
# Round lifecycle embeds
# ---------------------------------------------------------------------------

def round_start(session: GameSession, pack_name: str) -> discord.Embed:
    """
    Embed for the opening broadcast. The macro grid image is attached
    separately by the caller via discord.File; this embed references it
    with embed.set_image(url="attachment://map.png").
    """
    e = discord.Embed(
        title="📍 GridDrop — New Round",
        description=(
            "A location has been chosen somewhere on the map.\n"
            "Use the dropdowns below to select your **Macro Sector**, "
            "then your **Micro Cell** for precision targeting.\n"
            "Lock in your guess before time runs out!"
        ),
        colour=COLOUR_ACTIVE,
    )
    e.add_field(name="Map Pack", value=pack_name, inline=True)
    e.add_field(name="Time Limit", value=f"{session.round_seconds}s", inline=True)
    e.add_field(name="Max Score", value=f"{session.max_score:,}", inline=True)
    e.set_image(url="attachment://map.png")
    e.set_footer(text="Select Row then Column — both are required before locking in.")
    return e


def micro_prompt(macro: MacroSector) -> discord.Embed:
    """
    Ephemeral embed sent when a player selects their macro sector.
    The cropped micro-grid image is attached separately.
    """
    e = discord.Embed(
        title=f"🔍 Sector {macro.label} — Precision Targeting",
        description=(
            f"You've zoomed into **Sector {macro.label}**.\n"
            "Now select the exact row (a–j) and column (1–10) within this sector."
        ),
        colour=COLOUR_ACTIVE,
    )
    e.set_image(url="attachment://micro.png")
    e.set_footer(text="Both dropdowns must be set before you can Lock In.")
    return e


def guess_confirmed(
    guess: PlayerGuess,
    distance_display: str,
    score: int,
    rank: int,
    total_players: int,
) -> discord.Embed:
    """Ephemeral confirmation shown immediately after Lock In."""
    assert guess.macro is not None

    macro_label = guess.macro.label
    micro_label  = guess.micro.label if guess.micro else "—"
    coord_str    = f"{macro_label} / {micro_label}"

    e = discord.Embed(
        title="✅ Guess Locked In",
        description=f"Your guess has been recorded at **{coord_str}**.",
        colour=COLOUR_SUCCESS,
    )
    e.add_field(name="Distance", value=distance_display, inline=True)
    e.add_field(name="Score", value=f"**{score:,}** pts", inline=True)
    e.add_field(name="Current Rank", value=f"#{rank} of {total_players}", inline=True)
    e.set_footer(text="The reveal happens when time expires or everyone locks in.")
    return e


def round_locked(session: GameSession) -> discord.Embed:
    """
    Edits the original round embed when the timer fires.
    Signals players that guesses are closed.
    """
    locked_count = len(session.locked_guesses)
    e = discord.Embed(
        title="⏱️ Time's Up — Calculating Results…",
        description=(
            f"**{locked_count}** player(s) submitted a guess.\n"
            "The reveal is being rendered…"
        ),
        colour=COLOUR_LOCKED,
    )
    e.set_image(url="attachment://map.png")  # keep map visible during render
    return e


def reveal(
    session: GameSession,
    ranked_results: list[dict],
    target: GridPoint,
    pack_name: str,
) -> discord.Embed:
    """
    Final reveal embed. Composite image attached separately as 'reveal.png'.

    ranked_results: output of engine.math.rank_guesses — sorted list of dicts
        {"user_id", "score", "distance", "rank"}
    """
    e = discord.Embed(
        title="🎯 Round Complete — The Reveal",
        colour=COLOUR_REVEAL,
    )

    # Scoreboard
    lines = []
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for result in ranked_results:
        medal   = medals.get(result["rank"], f"#{result['rank']}")
        mention = f"<@{result['user_id']}>"
        score   = f"{result['score']:,} pts"
        dist    = f"{result['distance']:.1f} units away"
        lines.append(f"{medal} {mention} — **{score}** *(~{dist})*")

    if lines:
        e.add_field(name="Scoreboard", value="\n".join(lines), inline=False)
    else:
        e.add_field(name="Scoreboard", value="No one submitted a guess.", inline=False)

    e.add_field(name="Map Pack", value=pack_name, inline=True)
    e.set_image(url="attachment://reveal.png")
    e.set_footer(text="Scores have been recorded. Use /drop leaderboard to see rankings.")
    return e


# ---------------------------------------------------------------------------
# Informational / admin embeds
# ---------------------------------------------------------------------------

def leaderboard(
    guild_name: str,
    entries: list[dict],  # [{"user_id", "total_score", "games_played", "perfect_drops", "average_distance"}]
) -> discord.Embed:
    """Guild leaderboard embed."""
    e = discord.Embed(
        title=f"🏆 GridDrop Leaderboard — {guild_name}",
        colour=COLOUR_REVEAL,
    )

    if not entries:
        e.description = "No scores recorded yet. Start a round with `/drop start`!"
        return e

    lines = []
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for rank, entry in enumerate(entries[:10], start=1):
        medal    = medals.get(rank, f"#{rank}")
        mention  = f"<@{entry['user_id']}>"
        total    = f"{entry['total_score']:,}"
        played   = entry["games_played"]
        perfects = entry.get("perfect_drops", 0)
        lines.append(f"{medal} {mention} — **{total} pts** | {played} games | {perfects} perfects")

    e.description = "\n".join(lines)
    return e


def pack_list(packs: list[dict]) -> discord.Embed:
    """Admin embed listing all installed World Packs."""
    e = discord.Embed(
        title="🗺️ Installed World Packs",
        colour=COLOUR_NEUTRAL,
    )
    if not packs:
        e.description = "No packs installed. Drop a pack directory or ZIP into the packs folder."
        return e

    lines = []
    for pack in packs:
        tags = ", ".join(pack.get("tags", [])) or "none"
        lines.append(
            f"**{pack.get('name', '?')}** (`{pack.get('id', '?')}`) "
            f"v{pack.get('version', '?')} by {pack.get('author', '?')}\n"
            f"  ↳ {pack.get('description', '')}\n"
            f"  ↳ Tags: {tags}"
        )

    e.description = "\n\n".join(lines)
    e.set_footer(text="Use [p]drop setpack <id> to activate a pack for this server.")
    return e


def error(title: str, description: str) -> discord.Embed:
    """Generic error embed."""
    return discord.Embed(title=f"❌ {title}", description=description, colour=COLOUR_ERROR)
