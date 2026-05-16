"""
piraterep.py — Pirate Reputation tracking for OnePieceFruit.

Tracks per-user, per-guild:
  - Total lifetime messages (in any channel)
  - Weekly message count (resets each Sunday at midnight UTC)
  - Current daily streak (consecutive days with ≥1 message)
  - Longest streak ever recorded
  - Last-seen date (for streak calculation)
  - Reputation points (awarded at activity milestones)
  - Pirate rank title derived from rep

This module is self-contained. OnePieceFruit's core.py imports it and:
  1. Calls RepTracker.record_message(guild_id, user_id) inside on_message.
  2. Calls RepTracker.rep_embed_fields(guild_id, user_id) to append fields
     to the [p]df info embed.
  3. Provides rep leaderboard helpers for [p]df rep/weekly/streak.

MIT License — feel free to use and modify.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import discord
from redbot.core import commands

log = logging.getLogger("red.onepiecefruit.piraterep")

# ---------------------------------------------------------------------------
# Rank ladder  (min_rep → title, emoji)
# ---------------------------------------------------------------------------
RANK_LADDER: list[tuple[int, str, str]] = [
    (0,      "Cabin Boy",       "⚓"),
    (100,    "Sailor",          "🌊"),
    (300,    "Petty Officer",   "🗺️"),
    (600,    "Navigator",       "🧭"),
    (1_000,  "First Mate",      "⚔️"),
    (2_000,  "Ship Captain",    "🏴‍☠️"),
    (4_000,  "Rear Admiral",    "🎖️"),
    (7_500,  "Vice Admiral",    "🌟"),
    (12_000, "Admiral",         "💠"),
    (20_000, "Warlord",         "👑"),
    (35_000, "Yonko Commander", "🔥"),
    (60_000, "Yonko",          "⭐"),
]

# Rep earned at each milestone (milestone: rep_award)
# Keys are *total message* milestones.
MSG_MILESTONES: dict[int, int] = {
    50:     25,
    100:    50,
    250:    75,
    500:    100,
    1_000:  150,
    2_500:  200,
    5_000:  300,
    10_000: 500,
}

# Rep awarded per consecutive-day streak milestone (streak_days: rep)
STREAK_MILESTONES: dict[int, int] = {
    3:   15,
    7:   30,
    14:  60,
    30:  120,
    60:  200,
    100: 350,
    365: 1_000,
}

# Rep decay for inactivity
INACTIVITY_DECAY_DAYS = 7
INACTIVITY_DECAY_RATE = 0.05
INACTIVITY_DECAY_MIN = 10

# Weekly activity badges (weekly msg count → badge label)
WEEKLY_BADGES: list[tuple[int, str]] = [
    (500, "🌊 Tidal Force"),
    (250, "⚡ Thunderstrike"),
    (100, "🔥 Active Pirate"),
    (50,  "🗣️ Chatty Crew"),
    (10,  "📝 Showing Up"),
]

# ─── internal helpers ──────────────────────────────────────────────────────


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _week_key(d: Optional[date] = None) -> str:
    """ISO year-week string, e.g. '2025-W22'."""
    d = d or _utc_today()
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _rank_for_rep(rep: int) -> tuple[str, str]:
    """Return (title, emoji) for a rep total."""
    title, emoji = RANK_LADDER[0][1], RANK_LADDER[0][2]
    for min_rep, t, e in RANK_LADDER:
        if rep >= min_rep:
            title, emoji = t, e
        else:
            break
    return title, emoji


def _next_rank(rep: int) -> Optional[tuple[int, str, str]]:
    """Return the next rank entry (min_rep, title, emoji) or None if max rank."""
    for min_rep, t, e in RANK_LADDER:
        if rep < min_rep:
            return min_rep, t, e
    return None


def _calculate_inactivity_decay(rep: int, days_inactive: int) -> int:
    if days_inactive < INACTIVITY_DECAY_DAYS or rep <= 0:
        return 0
    weeks = days_inactive // INACTIVITY_DECAY_DAYS
    decay = max(INACTIVITY_DECAY_MIN, int(rep * INACTIVITY_DECAY_RATE * weeks))
    return min(decay, rep)


def _weekly_badge(weekly_msgs: int) -> Optional[str]:
    for threshold, label in WEEKLY_BADGES:
        if weekly_msgs >= threshold:
            return label
    return None


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class UserRepData:
    total_messages: int = 0
    weekly_messages: int = 0
    current_week: str = ""          # ISO week key when weekly_messages was last updated
    streak: int = 0
    longest_streak: int = 0
    last_seen: str = ""             # ISO date string, e.g. "2025-05-14"
    rep: int = 0
    # track which milestones already awarded (stored as sorted lists for JSON)
    awarded_msg_milestones: list[int] = field(default_factory=list)
    awarded_streak_milestones: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "UserRepData":
        return cls(
            total_messages=d.get("total_messages", 0),
            weekly_messages=d.get("weekly_messages", 0),
            current_week=d.get("current_week", ""),
            streak=d.get("streak", 0),
            longest_streak=d.get("longest_streak", 0),
            last_seen=d.get("last_seen", ""),
            rep=d.get("rep", 0),
            awarded_msg_milestones=d.get("awarded_msg_milestones", []),
            awarded_streak_milestones=d.get("awarded_streak_milestones", []),
        )


@dataclass
class GuildRepData:
    users: dict[str, UserRepData] = field(default_factory=dict)

    def get_user(self, user_id: int) -> UserRepData:
        key = str(user_id)
        if key not in self.users:
            self.users[key] = UserRepData()
        return self.users[key]

    def to_dict(self) -> dict:
        return {"users": {k: v.to_dict() for k, v in self.users.items()}}

    @classmethod
    def from_dict(cls, d: dict) -> "GuildRepData":
        users = {k: UserRepData.from_dict(v) for k, v in d.get("users", {}).items()}
        return cls(users=users)


@dataclass
class RepDB:
    guilds: dict[str, GuildRepData] = field(default_factory=dict)

    def get_guild(self, guild_id: int) -> GuildRepData:
        key = str(guild_id)
        if key not in self.guilds:
            self.guilds[key] = GuildRepData()
        return self.guilds[key]

    def to_dict(self) -> dict:
        return {"guilds": {k: v.to_dict() for k, v in self.guilds.items()}}

    @classmethod
    def from_dict(cls, d: dict) -> "RepDB":
        guilds = {k: GuildRepData.from_dict(v) for k, v in d.get("guilds", {}).items()}
        return cls(guilds=guilds)

    def to_file(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def from_file(cls, path: Path) -> "RepDB":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Core tracker — owns the RepDB and all mutation logic
# ---------------------------------------------------------------------------

class RepTracker:
    """
    Manages all Pirate Rep state.

    Usage (from inside the cog):

        # in cog_load:
        self.rep_tracker = RepTracker(cog_data_path(self) / "piraterep.json")
        await self.rep_tracker.load()

        # in on_message:
        await self.rep_tracker.record_message(guild.id, author.id)

        # in cog_unload:
        await self.rep_tracker.save()
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._db = RepDB()
        self._io_lock = asyncio.Lock()
        self._dirty = False
        self._save_task: Optional[asyncio.Task] = None

    async def load(self) -> None:
        if self._path.exists():
            try:
                self._db = await asyncio.to_thread(RepDB.from_file, self._path)
                log.info("PirateRep: loaded from %s", self._path)
            except Exception as exc:
                log.error("PirateRep: failed to load — starting fresh.", exc_info=exc)

    async def save(self) -> None:
        async with self._io_lock:
            try:
                await asyncio.to_thread(self._db.to_file, self._path)
            except Exception as exc:
                log.error("PirateRep: failed to save.", exc_info=exc)

    async def _debounced_save(self) -> None:
        await asyncio.sleep(30)
        if self._dirty:
            await self.save()
            self._dirty = False
        self._save_task = None

    def _schedule_save(self) -> None:
        if self._save_task is None or self._save_task.done():
            self._save_task = asyncio.create_task(self._debounced_save())

    # ── Message recording ───────────────────────────────────────────────────

    async def record_message(
        self,
        guild_id: int,
        user_id: int,
    ) -> Optional[tuple[Optional[tuple[str, str, str, str, int]], int, int]]:
        """
        Record one message for a user. Updates total, weekly, streak, rep.
        Saves automatically (debounced via asyncio — fire-and-forget in the cog).

        Returns a tuple with:
            - rank promotion details if the user advances rank
            - rep decay amount due to inactivity
            - days inactive used for decay calculation

        Returns None if no promotion or decay occurred.
        """
        today = _utc_today()
        week = _week_key(today)
        g = self._db.get_guild(guild_id)
        u = g.get_user(user_id)

        old_title, old_emoji = _rank_for_rep(u.rep)
        decay_amount = 0
        inactive_days = 0

        # ── Weekly reset ─────────────────────────────────────────────────
        if u.current_week != week:
            u.weekly_messages = 0
            u.current_week = week

        u.total_messages += 1
        u.weekly_messages += 1

        # ── Streak calculation ────────────────────────────────────────────
        today_str = today.isoformat()
        if u.last_seen:
            last = date.fromisoformat(u.last_seen)
            delta = (today - last).days
            if delta == 0:
                pass  # same day, streak unchanged
            elif delta == 1:
                u.streak += 1  # consecutive day
            else:
                inactive_days = delta
                decay_amount = _calculate_inactivity_decay(u.rep, inactive_days)
                if decay_amount:
                    u.rep -= decay_amount
                u.streak = 1   # streak broken
        else:
            u.streak = 1  # first ever message

        u.last_seen = today_str
        if u.streak > u.longest_streak:
            u.longest_streak = u.streak

        # ── Rep awards ────────────────────────────────────────────────────
        for milestone, award in MSG_MILESTONES.items():
            if u.total_messages >= milestone and milestone not in u.awarded_msg_milestones:
                u.rep += award
                u.awarded_msg_milestones.append(milestone)

        for streak_days, award in STREAK_MILESTONES.items():
            if u.streak >= streak_days and streak_days not in u.awarded_streak_milestones:
                u.rep += award
                u.awarded_streak_milestones.append(streak_days)

        new_title, new_emoji = _rank_for_rep(u.rep)
        promotion: Optional[tuple[str, str, str, str, int]] = None
        if (old_title, old_emoji) != (new_title, new_emoji):
            promotion = (old_title, old_emoji, new_title, new_emoji, u.rep)

        # save is deferred and debounced to avoid excessive disk writes
        self._dirty = True
        self._schedule_save()

        if promotion is None and decay_amount == 0:
            return None
        return promotion, decay_amount, inactive_days

    # ── Read helpers ────────────────────────────────────────────────────────

    def get_user(self, guild_id: int, user_id: int) -> UserRepData:
        return self._db.get_guild(guild_id).get_user(user_id)

    def weekly_leaderboard(self, guild_id: int) -> list[tuple[str, int]]:
        """Return [(user_id_str, weekly_msgs), ...] sorted desc for current week."""
        week = _week_key()
        g = self._db.get_guild(guild_id)
        results = []
        for uid, u in g.users.items():
            count = u.weekly_messages if u.current_week == week else 0
            if count > 0:
                results.append((uid, count))
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def streak_leaderboard(self, guild_id: int) -> list[tuple[str, int]]:
        """Return [(user_id_str, streak), ...] sorted desc."""
        g = self._db.get_guild(guild_id)
        results = [(uid, u.streak) for uid, u in g.users.items() if u.streak > 0]
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def rep_leaderboard(self, guild_id: int) -> list[tuple[str, int]]:
        """Return [(user_id_str, rep), ...] sorted desc."""
        g = self._db.get_guild(guild_id)
        results = [(uid, u.rep) for uid, u in g.users.items() if u.rep > 0]
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    # ── Embed helpers ───────────────────────────────────────────────────────

    def rep_embed_fields(self, guild_id: int, user_id: int) -> list[tuple[str, str, bool]]:
        """
        Return a list of (name, value, inline) tuples ready to add to a Discord
        embed via embed.add_field(name=…, value=…, inline=…).

        Designed to be appended to the existing [p]df info embed in core.py.
        """
        u = self.get_user(guild_id, user_id)
        title, emoji = _rank_for_rep(u.rep)
        week = _week_key()
        weekly = u.weekly_messages if u.current_week == week else 0
        badge = _weekly_badge(weekly)

        # Check if streak is active (last_seen was today or yesterday — safe grace window)
        today = _utc_today()
        streak_active = False
        if u.last_seen:
            last = date.fromisoformat(u.last_seen)
            streak_active = (today - last).days <= 1

        streak_display = f"{'🔥' if streak_active else '💤'} {u.streak} day{'s' if u.streak != 1 else ''}"
        best_streak = f"🏆 Best: {u.longest_streak} day{'s' if u.longest_streak != 1 else ''}"

        next_rank_info = _next_rank(u.rep)
        if next_rank_info:
            need = next_rank_info[0] - u.rep
            rank_progress = f"{u.rep:,} rep  ›  {need:,} to **{next_rank_info[1]}** {next_rank_info[2]}"
        else:
            rank_progress = f"{u.rep:,} rep  ›  **MAX RANK** ⭐"

        weekly_display = f"{weekly:,} msgs this week"
        if badge:
            weekly_display += f"\n{badge}"

        return [
            # Divider field
            ("\u200b", "\u200b", False),
            ("⚓ Pirate Rank", f"{emoji} **{title}**\n{rank_progress}", True),
            ("🔥 Streak", f"{streak_display}\n{best_streak}", True),
            ("📊 Activity", f"📨 {u.total_messages:,} total msgs\n{weekly_display}", True),
        ]

    def full_rep_embed(
        self,
        member: discord.Member,
        guild_id: int,
        *,
        weekly_rank: Optional[int] = None,
        streak_rank: Optional[int] = None,
        rep_rank: Optional[int] = None,
    ) -> discord.Embed:
        """Build a full standalone rep card embed for [p]df rep."""
        u = self.get_user(guild_id, member.id)
        title, emoji = _rank_for_rep(u.rep)
        week = _week_key()
        weekly = u.weekly_messages if u.current_week == week else 0
        badge = _weekly_badge(weekly)

        today = _utc_today()
        streak_active = False
        if u.last_seen:
            last = date.fromisoformat(u.last_seen)
            streak_active = (today - last).days <= 1

        embed = discord.Embed(
            title=f"{emoji} {title}",
            colour=discord.Colour.dark_gold(),
        )
        embed.set_author(
            name=f"{member.display_name}'s Pirate Rep",
            icon_url=member.display_avatar.url,
        )

        # Rank / rep
        next_rank_info = _next_rank(u.rep)
        if next_rank_info:
            needed = next_rank_info[0] - u.rep
            rank_value = (
                f"**{u.rep:,}** Pirate Rep\n"
                f"*{needed:,} more to reach **{next_rank_info[1]}** {next_rank_info[2]}*"
            )
        else:
            rank_value = f"**{u.rep:,}** Pirate Rep\n*Maximum rank achieved!* ⭐"

        embed.add_field(name="🏅 Reputation", value=rank_value, inline=False)

        # Streak
        streak_icon = "🔥" if streak_active else "💤"
        streak_status = "Active" if streak_active else "Inactive"
        embed.add_field(
            name=f"{streak_icon} Daily Streak ({streak_status})",
            value=f"Current: **{u.streak}** day{'s' if u.streak != 1 else ''}\nLongest: **{u.longest_streak}** days",
            inline=True,
        )

        # Weekly activity
        weekly_value = f"**{weekly:,}** messages this week"
        if badge:
            weekly_value += f"\n{badge}"
        if weekly_rank:
            weekly_value += f"\n📊 Rank **#{weekly_rank}** this week"
        embed.add_field(name="📅 Weekly Activity", value=weekly_value, inline=True)

        # Totals
        total_value = f"**{u.total_messages:,}** lifetime messages"
        if rep_rank:
            total_value += f"\n🎖️ Rep Rank **#{rep_rank}** on server"
        embed.add_field(name="📨 Total Messages", value=total_value, inline=True)

        # Last seen
        if u.last_seen:
            embed.set_footer(text=f"Last active: {u.last_seen}")

        return embed


