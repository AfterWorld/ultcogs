"""Single-file SQLite persistence; state/rewards and spawn claims commit atomically."""

import asyncio
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .content import QUESTS
from .engine import RuleError
from .loot import migrate_item_flags, migrate_names


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = asyncio.Lock()

    @contextmanager
    def _open(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    async def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)

        def work():
            with self._open() as c:
                if c.execute("PRAGMA user_version").fetchone()[0] > 3:
                    raise RuntimeError(
                        "This database belongs to a newer Aetherbound version; update the cog."
                    )
                c.execute("PRAGMA journal_mode=WAL")
                c.executescript("""
                CREATE TABLE IF NOT EXISTS players(guild INTEGER,user INTEGER,data TEXT NOT NULL,PRIMARY KEY(guild,user));
                CREATE TABLE IF NOT EXISTS settings(guild INTEGER PRIMARY KEY,data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS spawns(id TEXT PRIMARY KEY,guild INTEGER,channel INTEGER,message INTEGER,monster TEXT,expires REAL,claimed INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS trades(message INTEGER PRIMARY KEY,guild INTEGER,user INTEGER,thread INTEGER,created REAL);
                CREATE TABLE IF NOT EXISTS economy_events(id INTEGER PRIMARY KEY,guild INTEGER,user INTEGER,created REAL,reason TEXT,data TEXT);
                CREATE INDEX IF NOT EXISTS economy_events_guild ON economy_events(guild,id);
                CREATE TABLE IF NOT EXISTS boss_pools(id TEXT PRIMARY KEY,guild INTEGER,monster TEXT,hp INTEGER,maxhp INTEGER,expires REAL,defeated REAL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS boss_members(pool TEXT,guild INTEGER,user INTEGER,level INTEGER,damage INTEGER DEFAULT 0,claimed INTEGER DEFAULT 0,PRIMARY KEY(pool,user));
                PRAGMA user_version=3;
                """)
                # Additive, idempotent migration: retain previously tracked quest progress.
                for row in c.execute("SELECT guild,user,data FROM players").fetchall():
                    p = json.loads(row["data"])
                    p.setdefault(
                        "accepted_quests", {key: 0 for key in QUESTS if key not in p["quests"]}
                    )
                    migrate_names(p)
                    migrate_item_flags(p)
                    c.execute(
                        "UPDATE players SET data=? WHERE guild=? AND user=?",
                        (json.dumps(p), row["guild"], row["user"]),
                    )

        await asyncio.to_thread(work)

    async def transaction(self, fn):
        async with self.lock:

            def work():
                with self._open() as c:
                    c.execute("BEGIN IMMEDIATE")
                    return fn(c)

            # Finish an in-flight commit before releasing the lock on cancellation.
            task = asyncio.create_task(asyncio.to_thread(work))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                await task
                raise

    async def player(self, guild, user):
        def work(c):
            r = c.execute(
                "SELECT data FROM players WHERE guild=? AND user=?", (guild, user)
            ).fetchone()
            return json.loads(r[0]) if r else None

        return await self.transaction(work)

    async def change(self, guild, user, fn, create=False, reason="state_change", feature=None):
        def work(c):
            row = c.execute(
                "SELECT data FROM players WHERE guild=? AND user=?", (guild, user)
            ).fetchone()
            p = json.loads(row[0]) if row else None
            if create and p:
                raise RuleError("You already have a character. Use aether tutorial or profile.")
            if not create and not p:
                raise RuleError("Create a character first: aether create vanguard Your Name")
            if feature:
                settings = c.execute("SELECT data FROM settings WHERE guild=?", (guild,)).fetchone()
                flags = json.loads(settings[0]).get("features", {}) if settings else {}
                if not flags.get(feature, True):
                    raise RuleError(f"{feature} is temporarily disabled by an administrator.")
            before = economy_snapshot(p)
            result = fn(p, c)
            if create:
                p = result
            after = economy_snapshot(p)
            delta = {key: after[key] - before[key] for key in ("gold", "potions")}
            delta["materials"] = {
                key: after["materials"].get(key, 0) - before["materials"].get(key, 0)
                for key in set(after["materials"]) | set(before["materials"])
                if after["materials"].get(key, 0) != before["materials"].get(key, 0)
            }
            delta["created"] = sorted(after["items"] - before["items"])
            delta["destroyed"] = sorted(before["items"] - after["items"])
            if any(delta.values()):
                c.execute(
                    "INSERT INTO economy_events(guild,user,created,reason,data) VALUES(?,?,?,?,?)",
                    (guild, user, time.time(), reason, json.dumps(delta)),
                )
            c.execute("INSERT OR REPLACE INTO players VALUES(?,?,?)", (guild, user, json.dumps(p)))
            return result

        return await self.transaction(work)

    async def settings(self, guild, data=None):
        def work(c):
            if data is not None:
                c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (guild, json.dumps(data)))
                return data
            row = c.execute("SELECT data FROM settings WHERE guild=?", (guild,)).fetchone()
            return json.loads(row[0]) if row else {}

        return await self.transaction(work)

    async def rows(self, table):
        if table not in (
            "players",
            "settings",
            "spawns",
            "trades",
            "economy_events",
            "boss_pools",
            "boss_members",
        ):
            raise ValueError(table)
        return await self.transaction(
            lambda c: [dict(r) for r in c.execute(f"SELECT * FROM {table}")]
        )

    async def delete_user(self, user):
        def work(c):
            c.execute("DELETE FROM players WHERE user=?", (user,))
            c.execute("DELETE FROM trades WHERE user=?", (user,))
            c.execute("DELETE FROM economy_events WHERE user=?", (user,))
            c.execute("DELETE FROM boss_members WHERE user=?", (user,))

        await self.transaction(work)


def economy_snapshot(p):
    p = p or {}
    return dict(
        gold=p.get("gold", 0),
        potions=p.get("potions", 0),
        materials=dict(p.get("materials", {})),
        items=set(p.get("inventory", {})) | {i["id"] for i in p.get("unclaimed_loot", [])},
    )
