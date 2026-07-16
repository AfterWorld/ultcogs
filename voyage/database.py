"""SQLite persistence for the Voyage cog."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
STAT_COLUMNS = {"str", "spd", "def", "will"}
RENOWN_COLUMNS = {"bounty", "commendation", "infamy"}


class CharacterExistsError(ValueError):
    """Raised when a user already has a character in a guild."""


class VoyageDatabase:
    """Small async SQLite wrapper for Voyage player state."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA foreign_keys = ON")
        await self._db.execute("PRAGMA journal_mode = WAL")
        await self._run_migrations()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            msg = "Voyage database is not connected."
            raise RuntimeError(msg)
        return self._db

    async def _run_migrations(self) -> None:
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        async with self.db.execute("SELECT version FROM schema_migrations") as cursor:
            applied = {row["version"] async for row in cursor}

        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = path.stem
            if version in applied:
                continue
            await self.db.executescript(path.read_text(encoding="utf-8"))
            await self.db.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (version,),
            )
        await self.db.commit()

    async def get_character(self, guild_id: int, user_id: int) -> dict[str, Any] | None:
        async with self.db.execute(
            """
            SELECT *
            FROM characters
            WHERE guild_id = ? AND user_id = ?
            """,
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
        return dict(row) if row else None

    async def create_character(
        self,
        *,
        guild_id: int,
        user_id: int,
        faction: str,
        rank_tier: str,
        stats: dict[str, int],
    ) -> dict[str, Any]:
        try:
            await self.db.execute(
                """
                INSERT INTO characters (
                    guild_id, user_id, faction, rank_tier,
                    str, spd, def, will,
                    bounty, commendation, infamy
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
                """,
                (
                    guild_id,
                    user_id,
                    faction,
                    rank_tier,
                    stats["str"],
                    stats["spd"],
                    stats["def"],
                    stats["will"],
                ),
            )
        except aiosqlite.IntegrityError as exc:
            msg = "Character already exists for this user and guild."
            raise CharacterExistsError(msg) from exc

        await self.db.commit()
        character = await self.get_character(guild_id, user_id)
        if character is None:
            msg = "Character insert succeeded but the row could not be read back."
            raise RuntimeError(msg)
        return character

    async def delete_character(self, guild_id: int, user_id: int) -> int:
        await self.db.execute(
            "DELETE FROM cooldowns WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        cursor = await self.db.execute(
            "DELETE FROM characters WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self.db.commit()
        return cursor.rowcount

    async def add_stat(self, guild_id: int, user_id: int, stat: str, amount: int) -> dict[str, Any]:
        if stat not in STAT_COLUMNS:
            msg = f"Unknown stat column: {stat}"
            raise ValueError(msg)

        await self.db.execute(
            f"""
            UPDATE characters
            SET {stat} = {stat} + ?, updated_at = datetime('now')
            WHERE guild_id = ? AND user_id = ?
            """,
            (amount, guild_id, user_id),
        )
        await self.db.commit()
        character = await self.get_character(guild_id, user_id)
        if character is None:
            msg = "Character stat update succeeded but the row could not be read back."
            raise RuntimeError(msg)
        return character

    async def add_renown(
        self,
        guild_id: int,
        user_id: int,
        field: str,
        amount: int,
    ) -> dict[str, Any]:
        if field not in RENOWN_COLUMNS:
            msg = f"Unknown renown column: {field}"
            raise ValueError(msg)

        await self.db.execute(
            f"""
            UPDATE characters
            SET {field} = {field} + ?, updated_at = datetime('now')
            WHERE guild_id = ? AND user_id = ?
            """,
            (amount, guild_id, user_id),
        )
        await self.db.commit()
        character = await self.get_character(guild_id, user_id)
        if character is None:
            msg = "Character renown update succeeded but the row could not be read back."
            raise RuntimeError(msg)
        return character

    async def get_cooldown(self, guild_id: int, user_id: int, action_type: str) -> datetime | None:
        async with self.db.execute(
            """
            SELECT expires_at
            FROM cooldowns
            WHERE guild_id = ? AND user_id = ? AND action_type = ?
            """,
            (guild_id, user_id, action_type),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row["expires_at"])

    async def set_cooldown(
        self,
        guild_id: int,
        user_id: int,
        action_type: str,
        expires_at: datetime,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO cooldowns (guild_id, user_id, action_type, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id, action_type)
            DO UPDATE SET expires_at = excluded.expires_at
            """,
            (guild_id, user_id, action_type, expires_at.isoformat()),
        )
        await self.db.commit()

    async def create_voyage(
        self,
        *,
        guild_id: int,
        user_id: int,
        risk_tier: str,
        duration_seconds: int,
        started_at: datetime | None = None,
    ) -> dict[str, Any]:
        started_at = started_at or datetime.now(UTC)
        cursor = await self.db.execute(
            """
            INSERT INTO active_voyages (
                guild_id, user_id, risk_tier, started_at, duration_seconds, resolved
            )
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (guild_id, user_id, risk_tier, started_at.isoformat(), duration_seconds),
        )
        await self.db.commit()
        return await self.get_voyage(cursor.lastrowid)

    async def get_voyage(self, voyage_id: int) -> dict[str, Any]:
        async with self.db.execute(
            "SELECT * FROM active_voyages WHERE id = ?",
            (voyage_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            msg = f"Voyage row not found: {voyage_id}"
            raise RuntimeError(msg)
        return dict(row)

    async def get_open_voyage(self, guild_id: int, user_id: int) -> dict[str, Any] | None:
        async with self.db.execute(
            """
            SELECT *
            FROM active_voyages
            WHERE guild_id = ? AND user_id = ? AND resolved = 0
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_due_voyages(self, now: datetime | None = None) -> list[dict[str, Any]]:
        now = now or datetime.now(UTC)
        async with self.db.execute(
            """
            SELECT *
            FROM active_voyages
            WHERE resolved = 0
            ORDER BY started_at ASC
            """
        ) as cursor:
            rows = [dict(row) async for row in cursor]

        due = []
        for row in rows:
            started = datetime.fromisoformat(row["started_at"])
            if started + timedelta(seconds=row["duration_seconds"]) <= now:
                due.append(row)
        return due

    async def mark_voyage_resolved(
        self,
        voyage_id: int,
        *,
        outcome_key: str,
        berry_delta: int,
        resolved_at: datetime | None = None,
    ) -> None:
        resolved_at = resolved_at or datetime.now(UTC)
        await self.db.execute(
            """
            UPDATE active_voyages
            SET resolved = 1,
                resolved_at = ?,
                outcome_key = ?,
                berry_delta = ?
            WHERE id = ?
            """,
            (resolved_at.isoformat(), outcome_key, berry_delta, voyage_id),
        )
        await self.db.commit()

    async def log_transaction(
        self,
        *,
        guild_id: int,
        user_id: int,
        source: str,
        action_type: str,
        delta_requested: int,
        delta_applied: int,
        reason: str,
        balance_after: int | None,
        related_voyage_id: int | None = None,
        related_contract_id: int | None = None,
        status: str = "applied",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO transactions (
                guild_id, user_id, source, action_type,
                delta_requested, delta_applied, reason, balance_after,
                related_voyage_id, related_contract_id, status, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                source,
                action_type,
                delta_requested,
                delta_applied,
                reason,
                balance_after,
                related_voyage_id,
                related_contract_id,
                status,
                json.dumps(metadata or {}, sort_keys=True),
            ),
        )
        await self.db.commit()

    async def get_open_contract_for_target(
        self,
        guild_id: int,
        target_user_id: int,
    ) -> dict[str, Any] | None:
        async with self.db.execute(
            """
            SELECT *
            FROM contracts
            WHERE guild_id = ? AND target_user_id = ? AND status = 'open'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (guild_id, target_user_id),
        ) as cursor:
            row = await cursor.fetchone()
        return dict(row) if row else None

    async def create_contract(
        self,
        *,
        guild_id: int,
        target_user_id: int,
        net_amount: int,
        fee_amount: int,
        expires_at: datetime,
        created_at: datetime | None = None,
    ) -> dict[str, Any]:
        created_at = created_at or datetime.now(UTC)
        cursor = await self.db.execute(
            """
            INSERT INTO contracts (
                guild_id, target_user_id, status, total_pooled,
                posting_fee_collected, created_at, expires_at
            )
            VALUES (?, ?, 'open', ?, ?, ?, ?)
            """,
            (
                guild_id,
                target_user_id,
                net_amount,
                fee_amount,
                created_at.isoformat(),
                expires_at.isoformat(),
            ),
        )
        await self.db.commit()
        return await self.get_contract(cursor.lastrowid)

    async def get_contract(self, contract_id: int) -> dict[str, Any]:
        async with self.db.execute(
            "SELECT * FROM contracts WHERE id = ?",
            (contract_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            msg = f"Contract row not found: {contract_id}"
            raise RuntimeError(msg)
        return dict(row)

    async def add_contract_contribution(
        self,
        *,
        contract_id: int,
        contributor_user_id: int,
        amount: int,
        fee_amount: int,
        anonymous: bool,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO contract_contributions (
                contract_id, contributor_user_id, amount, fee_amount, anonymous
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (contract_id, contributor_user_id, amount, fee_amount, int(anonymous)),
        )
        await self.db.execute(
            """
            UPDATE contracts
            SET total_pooled = total_pooled + ?,
                posting_fee_collected = posting_fee_collected + ?
            WHERE id = ? AND status = 'open'
            """,
            (amount - fee_amount, fee_amount, contract_id),
        )
        await self.db.commit()

    async def add_contribution_to_open_contract(
        self,
        *,
        guild_id: int,
        target_user_id: int,
        contributor_user_id: int,
        amount: int,
        fee_amount: int,
        anonymous: bool,
        expires_at: datetime,
    ) -> dict[str, Any]:
        contract = await self.get_open_contract_for_target(guild_id, target_user_id)
        if contract is None:
            contract = await self.create_contract(
                guild_id=guild_id,
                target_user_id=target_user_id,
                net_amount=0,
                fee_amount=0,
                expires_at=expires_at,
            )
        await self.add_contract_contribution(
            contract_id=contract["id"],
            contributor_user_id=contributor_user_id,
            amount=amount,
            fee_amount=fee_amount,
            anonymous=anonymous,
        )
        return await self.get_contract(contract["id"])

    async def get_contract_contributions(self, contract_id: int) -> list[dict[str, Any]]:
        async with self.db.execute(
            """
            SELECT *
            FROM contract_contributions
            WHERE contract_id = ?
            ORDER BY contributed_at ASC
            """,
            (contract_id,),
        ) as cursor:
            return [dict(row) async for row in cursor]

    async def user_contributed_to_contract(self, contract_id: int, user_id: int) -> bool:
        async with self.db.execute(
            """
            SELECT 1
            FROM contract_contributions
            WHERE contract_id = ? AND contributor_user_id = ?
            LIMIT 1
            """,
            (contract_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
        return row is not None

    async def claim_contract(self, contract_id: int, claimer_user_id: int) -> bool:
        claimed_at = datetime.now(UTC).isoformat()
        cursor = await self.db.execute(
            """
            UPDATE contracts
            SET status = 'claimed',
                claimed_by = ?,
                claimed_at = ?
            WHERE id = ? AND status = 'open'
            """,
            (claimer_user_id, claimed_at, contract_id),
        )
        await self.db.commit()
        return cursor.rowcount == 1

    async def mark_contract_resolved(self, contract_id: int) -> None:
        await self.db.execute(
            """
            UPDATE contracts
            SET status = 'resolved',
                resolved_at = ?
            WHERE id = ?
            """,
            (datetime.now(UTC).isoformat(), contract_id),
        )
        await self.db.commit()

    async def mark_contract_expired(self, contract_id: int) -> None:
        await self.db.execute(
            """
            UPDATE contracts
            SET status = 'expired',
                resolved_at = ?
            WHERE id = ? AND status = 'open'
            """,
            (datetime.now(UTC).isoformat(), contract_id),
        )
        await self.db.commit()

    async def get_due_contracts(self, now: datetime | None = None) -> list[dict[str, Any]]:
        now = now or datetime.now(UTC)
        async with self.db.execute(
            """
            SELECT *
            FROM contracts
            WHERE status = 'open'
            ORDER BY expires_at ASC
            """
        ) as cursor:
            rows = [dict(row) async for row in cursor]
        return [row for row in rows if datetime.fromisoformat(row["expires_at"]) <= now]
