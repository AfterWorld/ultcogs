"""Pydantic models for the OnePieceFruit cog."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class UserFruitData(BaseModel):
    """Tracks one user's Devil Fruit state inside a guild."""

    fruit_name: str = ""
    fruit_type: str = ""           # e.g. "Logia", "Mythical Zoan"
    assigned_at_level: int = 0
    awakening_stage: int = 0       # 0=base, 1=first awakening, 2=full awakening
    reroll_count: int = 0
    last_reroll_cost: int = 0
    last_daily_stipend: str = ""
    profile_visible: bool = True   # Show Devil Fruit on profile / pf views by default


class GuildData(BaseModel):
    """Per-guild storage: maps user_id (str) → UserFruitData."""

    users: dict[str, UserFruitData] = Field(default_factory=dict)

    # -----------------------------------------------------------------------
    # Convenience helpers
    # -----------------------------------------------------------------------
    def get_user(self, user_id: int) -> Optional[UserFruitData]:
        return self.users.get(str(user_id))

    def set_user(self, user_id: int, data: UserFruitData) -> None:
        self.users[str(user_id)] = data

    def remove_user(self, user_id: int) -> None:
        self.users.pop(str(user_id), None)


class AuditEntry(BaseModel):
    """Single audit record for admin actions, duels, and giveaways."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    guild_id: int
    actor_id: int
    action: str
    target_id: Optional[int] = None
    details: str = ""


class DB(BaseModel):
    """Top-level DB: maps guild_id (str) → GuildData."""

    guilds: dict[str, GuildData] = Field(default_factory=dict)
    audit_log: list[AuditEntry] = Field(default_factory=list)

    # -----------------------------------------------------------------------
    def get_guild(self, guild_id: int) -> GuildData:
        key = str(guild_id)
        if key not in self.guilds:
            self.guilds[key] = GuildData()
        return self.guilds[key]

    def add_audit(self, entry: AuditEntry) -> None:
        self.audit_log.append(entry)

    def audit_for_guild(self, guild_id: int) -> list[AuditEntry]:
        return [entry for entry in self.audit_log if entry.guild_id == guild_id]

    def clear_audit(self, guild_id: int) -> None:
        self.audit_log = [entry for entry in self.audit_log if entry.guild_id != guild_id]

    # -----------------------------------------------------------------------
    # File I/O (sync, run via asyncio.to_thread)
    # -----------------------------------------------------------------------
    @classmethod
    def from_file(cls, path: Path) -> "DB":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def to_file(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
