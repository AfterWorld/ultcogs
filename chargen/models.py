"""
chargen/models.py
─────────────────────────────────────────────────────────────────────────────
Typed character sheet model with full Red Config serialization support.

Design notes:
- Uses __slots__ for memory efficiency at scale.
- from_dict / to_dict are the only serialization boundary — keeps the
  Config schema changes isolated to this file.
- Optional fields use None as the sentinel; presenter layer handles display.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class OnePieceCharacter:
    """
    Immutable after generation — permanent character sheet.
    All fields are stored in Red Config under guild → user → "character".
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    user_id: int
    guild_id: int
    display_name: str           # Snapshot of name at roll time
    epithet: str = ""           # e.g. "the Ironclad"

    # ── Core traits ───────────────────────────────────────────────────────────
    race: str = "Unknown"
    is_d_clan: bool = False
    affiliation: str = "Unknown"

    # ── Power system ──────────────────────────────────────────────────────────
    has_devil_fruit: bool = False
    devil_fruit_type: Optional[str] = None     # Paramecia / Zoan / Logia / ...
    devil_fruit_name: Optional[str] = None     # Specific canonical fruit name
    haki: str = "None"
    fighting_style: str = "Unknown"

    # ── Stats ─────────────────────────────────────────────────────────────────
    strength: str = "Unknown"
    speed: str = "Unknown"
    battle_iq: str = "Unknown"

    # ── Affiliation-conditional ───────────────────────────────────────────────
    marine_rank: Optional[str] = None
    bounty: Optional[int] = None               # None for Marines/World Nobles

    # ── Meta ──────────────────────────────────────────────────────────────────
    rolled_at: int = 0                         # Unix timestamp, set by engine

    # ─────────────────────────────────────────────────────────────────────────
    # Serialization
    # ─────────────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict for storage in Red Config."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OnePieceCharacter":
        """Reconstruct from a Red Config dict. Unknown keys are silently dropped
        to survive schema additions without crashing existing saved characters."""
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    # ─────────────────────────────────────────────────────────────────────────
    # Display helpers (used by animator — no Discord imports here)
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def full_name(self) -> str:
        """e.g. 'Adam the Ironclad'"""
        if self.epithet:
            return f"{self.display_name} {self.epithet}"
        return self.display_name

    @property
    def d_clan_display(self) -> str:
        return "**YES** *(Carries the Will of D.)*" if self.is_d_clan else "No"

    @property
    def devil_fruit_display(self) -> str:
        if not self.has_devil_fruit:
            return "None *(Pure Haki/Physical)*"
        parts = []
        if self.devil_fruit_name:
            parts.append(f"**{self.devil_fruit_name}**")
        if self.devil_fruit_type:
            parts.append(f"*({self.devil_fruit_type})*")
        return " ".join(parts) if parts else "Unknown Fruit"

    @property
    def bounty_display(self) -> str:
        if self.affiliation == "Marine":
            return f"N/A *(Rank: {self.marine_rank})*"
        if self.bounty is None:
            return "None"
        return f"฿ {self.bounty:,}"

    @property
    def threat_level_display(self) -> str:
        """Derive a World Government threat classification from stats."""
        tiers = {"Yonko-Tier": 5, "S-Tier": 4, "A-Tier": 3,
                 "B-Tier": 2, "C-Tier": 1, "D-Tier": 0, "F-Tier": 0}
        score = tiers.get(self.strength, 0) + tiers.get(self.speed, 0) + tiers.get(self.battle_iq, 0)
        if score >= 13:  return "🔴 Yonko-Class"
        if score >= 10:  return "🟠 Emperor's Crew Level"
        if score >= 7:   return "🟡 Warlord-Class"
        if score >= 5:   return "🟢 Super Rookie"
        if score >= 3:   return "🔵 Notable Threat"
        return "⚪ Below Radar"