"""
Session state for an active GridDrop round.

Volatile: these objects live only in memory (core.py's active_sessions dict).
Nothing here is written to RedBot Config until round resolution.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from datetime import datetime, timezone

from .coordinates import GridPoint, MacroSector, MicroCell


class RoundPhase(Enum):
    """Lifecycle phases of a single round."""
    WAITING    = auto()   # session created, map not yet sent
    MACRO      = auto()   # macro grid is live; players selecting sectors
    MICRO      = auto()   # micro grid is live per-player (ephemeral UI)
    LOCKED     = auto()   # timer expired; no further guesses accepted
    RESOLVING  = auto()   # Pillow render in progress
    COMPLETE   = auto()   # scores written, session will be purged


@dataclass
class PlayerGuess:
    """
    All state for a single player's guess in one round.

    Fields are set incrementally as the player completes each UI step.
    `resolved_point` is None until both tiers are chosen (or macro-only mode).
    """
    user_id:        int
    macro:          Optional[MacroSector] = field(default=None)
    micro:          Optional[MicroCell]   = field(default=None)
    resolved_point: Optional[GridPoint]   = field(default=None)
    score:          Optional[int]          = field(default=None)
    distance:       Optional[float]        = field(default=None)

    # Timestamp of the Lock In press, for future tiebreaking
    locked_at: Optional[datetime] = field(default=None)

    @property
    def is_complete(self) -> bool:
        """True once the player has a fully resolved point."""
        return self.resolved_point is not None

    def lock(self) -> None:
        """Mark the guess as submitted (no further edits)."""
        self.locked_at = datetime.now(tz=timezone.utc)


@dataclass
class GameSession:
    """
    All state for one active round in one Discord channel.

    Keyed by channel_id in core.py's `active_sessions` dict.
    """
    channel_id:    int
    guild_id:      int
    message_id:    Optional[int]          = field(default=None)  # set after send
    target:        Optional[GridPoint]    = field(default=None)  # set during generation
    pack_name:     str                    = field(default="earth")
    phase:         RoundPhase            = field(default=RoundPhase.WAITING)
    guesses:       dict[int, PlayerGuess] = field(default_factory=dict)
    timer_task:    Optional[asyncio.Task] = field(default=None, repr=False)
    started_at:    datetime               = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    round_seconds: int                    = field(default=60)

    # Config snapshots captured at round start (so mid-round admin changes don't affect scoring)
    max_score:   int   = field(default=5000)
    decay_rate:  float = field(default=0.05)
    micro_mode:  bool  = field(default=True)

    # --- player management ---

    def get_or_create_guess(self, user_id: int) -> PlayerGuess:
        if user_id not in self.guesses:
            self.guesses[user_id] = PlayerGuess(user_id=user_id)
        return self.guesses[user_id]

    def set_macro(self, user_id: int, macro: MacroSector) -> PlayerGuess:
        guess = self.get_or_create_guess(user_id)
        guess.macro = macro
        guess.resolved_point = None  # invalidate stale resolution
        return guess

    def set_micro(self, user_id: int, micro: MicroCell) -> PlayerGuess:
        guess = self.get_or_create_guess(user_id)
        guess.micro = micro
        # Auto-resolve once both tiers are set
        if guess.macro is not None:
            guess.resolved_point = GridPoint.from_tiers(guess.macro, micro)
        return guess

    def lock_guess(self, user_id: int) -> Optional[PlayerGuess]:
        """
        Finalise a player's guess. Returns the guess if valid, None if not ready.
        In macro-only mode, resolves to the sector centre automatically.
        """
        guess = self.guesses.get(user_id)
        if guess is None or guess.macro is None:
            return None

        if not self.micro_mode:
            guess.resolved_point = GridPoint.from_macro_only(guess.macro)

        if not guess.is_complete:
            return None

        guess.lock()
        return guess

    # --- convenience queries ---

    @property
    def locked_guesses(self) -> list[PlayerGuess]:
        return [g for g in self.guesses.values() if g.is_complete and g.locked_at]

    @property
    def participant_count(self) -> int:
        return len(self.guesses)

    def cancel_timer(self) -> None:
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
