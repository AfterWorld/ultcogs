"""Faction data for Voyage character creation."""

from __future__ import annotations

from dataclasses import dataclass

STAT_KEYS = ("str", "spd", "def", "will")
BASE_STATS = {"str": 10, "spd": 10, "def": 10, "will": 10}


@dataclass(frozen=True)
class Faction:
    """Data-only definition for a Voyage faction."""

    key: str
    label: str
    emoji: str
    rank_tier: str
    renown_field: str
    modifiers: dict[str, int]
    description: str

    @property
    def display_name(self) -> str:
        return f"{self.emoji} {self.label}"


FACTIONS: dict[str, Faction] = {
    "pirate": Faction(
        key="pirate",
        label="Pirate",
        emoji="🏴‍☠️",
        rank_tier="Rookie",
        renown_field="bounty",
        modifiers={"str": 2, "spd": 1, "def": 0, "will": 1},
        description="Free captains chasing treasure, infamy, and impossible seas.",
    ),
    "marine": Faction(
        key="marine",
        label="Marine",
        emoji="🛡️",
        rank_tier="Recruit",
        renown_field="commendation",
        modifiers={"str": 0, "spd": 1, "def": 2, "will": 1},
        description="Uniformed enforcers earning commendations under the banner of justice.",
    ),
    "revolutionary": Faction(
        key="revolutionary",
        label="Revolutionary",
        emoji="🔥",
        rank_tier="Operative",
        renown_field="infamy",
        modifiers={"str": 1, "spd": 2, "def": 0, "will": 1},
        description="Underground fighters moving fast, striking hard, and rewriting the map.",
    ),
}


def get_faction(key: str) -> Faction:
    """Return a faction definition by key."""
    return FACTIONS[key]


def build_starting_stats(faction_key: str) -> dict[str, int]:
    """Build deterministic v1 starting stats from base stats plus faction modifiers."""
    faction = get_faction(faction_key)
    return {stat: BASE_STATS[stat] + faction.modifiers.get(stat, 0) for stat in STAT_KEYS}


def stat_weights_for_faction(faction_key: str) -> list[tuple[str, int]]:
    """Return weighted stat choices for small progression rolls."""
    faction = get_faction(faction_key)
    return [(stat, 1 + max(0, faction.modifiers.get(stat, 0))) for stat in STAT_KEYS]


def format_stats(stats: dict[str, int]) -> str:
    """Format compact stat text for embeds."""
    return (
        f"**STR** {stats['str']}  •  **SPD** {stats['spd']}  •  "
        f"**DEF** {stats['def']}  •  **WILL** {stats['will']}"
    )


def format_modifiers(faction: Faction) -> str:
    """Format faction stat modifiers for select-menu descriptions."""
    parts = [f"+{value} {stat.upper()}" for stat, value in faction.modifiers.items() if value]
    return ", ".join(parts) if parts else "No stat modifier"
