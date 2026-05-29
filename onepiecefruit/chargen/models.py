"""
chargen/models.py
─────────────────────────────────────────────────────────────────────────────
Typed character sheet model with full Red Config serialization support.

Design notes:
- Uses dataclass for clean field declaration and asdict() serialization.
- from_dict / to_dict are the only serialization boundary — keeps Config
  schema changes isolated to this file.
- Optional fields use None as the sentinel; presenter layer handles display.
- Mastery fields are conditional:
    haki_mastery        → None if haki == "None"
    devil_fruit_mastery → None if has_devil_fruit == False
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class OnePieceCharacter:
    """
    Immutable after generation — permanent character sheet.
    All fields stored in Red Config under guild → user → "character".
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    user_id: int
    guild_id: int
    display_name: str               # Snapshot of name at roll time
    epithet: str = ""               # e.g. "the Ironclad"

    # ── Core traits ───────────────────────────────────────────────────────────
    race: str = "Unknown"
    is_d_clan: bool = False
    affiliation: str = "Unknown"
    origin: str = "Unknown"         # Backstory origin

    # ── Weapon ────────────────────────────────────────────────────────────────
    weapon_type: str = "Unknown"
    weapon_mastery: str = "Unknown"

    # ── Power system ──────────────────────────────────────────────────────────
    has_devil_fruit: bool = False
    devil_fruit_type: Optional[str] = None
    devil_fruit_name: Optional[str] = None
    devil_fruit_mastery: Optional[str] = None   # None if no fruit

    haki: str = "None"
    haki_mastery: Optional[str] = None          # None if haki == "None"
    fighting_style: str = "Unknown"

    # ── Stats ─────────────────────────────────────────────────────────────────
    strength: str = "Unknown"
    speed: str = "Unknown"
    battle_iq: str = "Unknown"
    endurance: str = "Unknown"      # New stat
    willpower: str = "Unknown"      # New stat — determines Haki ceiling

    # ── Rival ─────────────────────────────────────────────────────────────────
    rival: str = "Unknown"

    # ── Affiliation-conditional ───────────────────────────────────────────────
    marine_rank: Optional[str] = None
    bounty: Optional[int] = None

    # ── Meta ──────────────────────────────────────────────────────────────────
    rolled_at: int = 0

    # ─────────────────────────────────────────────────────────────────────────
    # Serialization
    # ─────────────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OnePieceCharacter":
        """Reconstruct from Config. Unknown keys silently dropped to survive
        schema additions without crashing existing saved characters."""
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    # ─────────────────────────────────────────────────────────────────────────
    # Display helpers
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def full_name(self) -> str:
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
    def devil_fruit_mastery_display(self) -> str:
        if not self.has_devil_fruit:
            return "N/A *(No Fruit)*"
        return self.devil_fruit_mastery or "Unknown"

    @property
    def haki_mastery_display(self) -> str:
        if self.haki == "None":
            return "N/A *(No Haki)*"
        return self.haki_mastery or "Unknown"

    @property
    def weapon_display(self) -> str:
        return f"{self.weapon_type} *(Mastery: {self.weapon_mastery})*"

    @property
    def bounty_display(self) -> str:
        if self.affiliation == "Marine":
            return f"N/A *(Rank: {self.marine_rank})*"
        if self.bounty is None:
            return "None"
        return f"฿ {self.bounty:,}"

    @property
    def threat_level_display(self) -> str:
        """Derives World Government threat classification from five stats."""
        tiers = {
            "Yonko-Tier": 6, "S-Tier": 5, "A-Tier": 4,
            "B-Tier": 3, "C-Tier": 2, "D-Tier": 1, "F-Tier": 0,
        }
        score = sum(tiers.get(s, 0) for s in (
            self.strength, self.speed, self.battle_iq,
            self.endurance, self.willpower,
        ))
        if score >= 26: return "🔴 Yonko-Class"
        if score >= 20: return "🟠 Emperor's Crew Level"
        if score >= 14: return "🟡 Warlord-Class"
        if score >= 9:  return "🟢 Super Rookie"
        if score >= 5:  return "🔵 Notable Threat"
        return "⚪ Below Radar"