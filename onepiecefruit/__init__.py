"""OnePieceFruit — Devil Fruit companion cog for vertyco's LevelUp."""

__red_end_user_data_statement__ = (
    "This cog stores per-server Devil Fruit and character choices, reroll history, "
    "Pirate Rep activity counts and streaks, and audit entries containing user IDs. "
    "This data supports the cog's profile, progression, economy, and administration "
    "features. Red's data deletion request removes the user's records."
)

from .core import OnePieceFruit, setup

__all__ = ["OnePieceFruit", "setup"]

