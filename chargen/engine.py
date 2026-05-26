"""
chargen/engine.py
─────────────────────────────────────────────────────────────────────────────
Dependency-driven stochastic generation engine.

Architecture:
- All generation is synchronous and instant — happens in memory before
  Discord is touched. The animator handles the async reveal separately.
- spin() is a pure function: (pool) → outcome. No side effects.
- generate_character() is the only public entry point. It enforces the
  conditional dependency graph explicitly.
- Fighting style pool selection is affiliation-aware.
- Bounty is seeded from a tier-aware range, not a fixed multiplier.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import random
import time
from typing import Any, Union

from . import pools as P
from .models import OnePieceCharacter


Pool = dict[Union[str, bool], int]


class WheelEngine:
    """
    Stateless RNG engine. All methods are classmethods — no instantiation needed.
    """

    @staticmethod
    def spin(pool: Pool) -> Any:
        """
        Weighted random selection from a {outcome: weight} dict.
        Using random.choices() with k=1 for O(n) weighted selection.
        Returns the bare value, not a list.
        """
        outcomes = list(pool.keys())
        weights = list(pool.values())
        return random.choices(outcomes, weights=weights, k=1)[0]

    @classmethod
    def _roll_bounty(cls, strength_tier: str) -> int:
        """
        Generates a bounty from a tier-aware range to produce realistic
        Beri values rather than flat multipliers.
        Returns 0 for tiers not in the table (shouldn't happen, but safe).
        """
        config = P.BOUNTY_RANGE_BY_TIER.get(strength_tier)
        if not config:
            return 0
        low, high, multiplier = config
        return random.randint(low, high) * multiplier

    @classmethod
    def _select_fighting_style(cls, affiliation: str, has_devil_fruit: bool) -> str:
        """
        Pulls from the affiliation-appropriate style pool.
        If the character has no devil fruit, removes 'Devil Fruit Mastery'
        from the pool to avoid a contradiction (then renormalizes weights).
        """
        pool = dict(P.FIGHTING_STYLES_BY_AFFILIATION.get(affiliation, P.FIGHTING_STYLE_OTHER))

        if not has_devil_fruit and "Devil Fruit Mastery" in pool:
            del pool["Devil Fruit Mastery"]

        return cls.spin(pool)

    @classmethod
    def generate_character(
        cls,
        user_id: int,
        guild_id: int,
        display_name: str,
    ) -> OnePieceCharacter:
        """
        Traverses the full dependency graph and returns a fully populated
        OnePieceCharacter. No Discord I/O. Safe to call synchronously.

        Dependency graph:
            race            → (standalone)
            is_d_clan       → (standalone)
            affiliation     → fighting_style pool, bounty vs rank branch
            has_devil_fruit → devil_fruit_type, devil_fruit_name, style pool trim
            devil_fruit_type→ devil_fruit_name lookup
            strength        → bounty range
        """
        # ── Phase 1: Core identity ─────────────────────────────────────────
        race: str           = cls.spin(P.RACE)
        is_d_clan: bool     = cls.spin(P.WILL_OF_D)
        affiliation: str    = cls.spin(P.AFFILIATION)
        epithet: str        = random.choice(P.EPITHETS)

        # ── Phase 2: Power system ──────────────────────────────────────────
        has_devil_fruit: bool = cls.spin(P.HAS_DEVIL_FRUIT)

        devil_fruit_type: str | None = None
        devil_fruit_name: str | None = None

        if has_devil_fruit:
            devil_fruit_type = cls.spin(P.DEVIL_FRUIT_TYPE)
            fruit_pool = P.DEVIL_FRUITS_BY_TYPE.get(devil_fruit_type, [])
            devil_fruit_name = random.choice(fruit_pool) if fruit_pool else None

        haki: str           = cls.spin(P.HAKI_POTENTIAL)
        fighting_style: str = cls._select_fighting_style(affiliation, has_devil_fruit)

        # ── Phase 3: Stats ─────────────────────────────────────────────────
        strength: str  = cls.spin(P.STAT_TIER)
        speed: str     = cls.spin(P.STAT_TIER)
        battle_iq: str = cls.spin(P.STAT_TIER)

        # ── Phase 4: Affiliation-conditional outputs ───────────────────────
        marine_rank: str | None = None
        bounty: int | None      = None

        if affiliation == "Marine":
            marine_rank = cls.spin(P.MARINE_RANK)
            bounty = 0  # Marines have no bounty
        elif affiliation == "World Noble":
            bounty = None  # Immune to bounty system
        else:
            bounty = cls._roll_bounty(strength)

        return OnePieceCharacter(
            user_id=user_id,
            guild_id=guild_id,
            display_name=display_name,
            epithet=epithet,
            race=race,
            is_d_clan=is_d_clan,
            affiliation=affiliation,
            has_devil_fruit=has_devil_fruit,
            devil_fruit_type=devil_fruit_type,
            devil_fruit_name=devil_fruit_name,
            haki=haki,
            fighting_style=fighting_style,
            strength=strength,
            speed=speed,
            battle_iq=battle_iq,
            marine_rank=marine_rank,
            bounty=bounty,
            rolled_at=int(time.time()),
        )
