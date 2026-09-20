"""Single-file SQLite persistence; state/rewards and spawn claims commit atomically."""

import asyncio
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .engine import RuleError


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
                if c.execute("PRAGMA user_version").fetchone()[0] > 1:
                    raise RuntimeError(
                        "This database belongs to a newer Aetherbound version; update the cog."
                    )
                c.execute("PRAGMA journal_mode=WAL")
                c.executescript("""
                CREATE TABLE IF NOT EXISTS players(guild INTEGER,user INTEGER,data TEXT NOT NULL,PRIMARY KEY(guild,user));
                CREATE TABLE IF NOT EXISTS settings(guild INTEGER PRIMARY KEY,data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS spawns(id TEXT PRIMARY KEY,guild INTEGER,channel INTEGER,message INTEGER,monster TEXT,expires REAL,claimed INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS trades(message INTEGER PRIMARY KEY,guild INTEGER,user INTEGER,thread INTEGER,created REAL);
                PRAGMA user_version=1;
                """)

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

    async def change(self, guild, user, fn, create=False):
        def work(c):
            row = c.execute(
                "SELECT data FROM players WHERE guild=? AND user=?", (guild, user)
            ).fetchone()
            p = json.loads(row[0]) if row else None
            if create and p:
                raise RuleError("You already have a character. Use aether tutorial or profile.")
            if not create and not p:
                raise RuleError("Create a character first: aether create vanguard Your Name")
            result = fn(p, c)
            if create:
                p = result
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
        if table not in ("players", "settings", "spawns", "trades"):
            raise ValueError(table)
        return await self.transaction(
            lambda c: [dict(r) for r in c.execute(f"SELECT * FROM {table}")]
        )

    async def delete_user(self, user):
        def work(c):
            c.execute("DELETE FROM players WHERE user=?", (user,))
            c.execute("DELETE FROM trades WHERE user=?", (user,))

        await self.transaction(work)
