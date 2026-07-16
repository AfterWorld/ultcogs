CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    faction TEXT NOT NULL CHECK (faction IN ('pirate', 'marine', 'revolutionary')),
    rank_tier TEXT NOT NULL,
    str INTEGER NOT NULL,
    spd INTEGER NOT NULL,
    def INTEGER NOT NULL,
    will INTEGER NOT NULL,
    bounty INTEGER NOT NULL DEFAULT 0,
    commendation INTEGER NOT NULL DEFAULT 0,
    infamy INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, guild_id)
);

CREATE INDEX IF NOT EXISTS idx_characters_guild_faction
    ON characters (guild_id, faction);

CREATE TABLE IF NOT EXISTS cooldowns (
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    PRIMARY KEY (user_id, guild_id, action_type)
);

CREATE INDEX IF NOT EXISTS idx_cooldowns_expires_at
    ON cooldowns (expires_at);
