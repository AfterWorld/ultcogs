CREATE TABLE IF NOT EXISTS active_voyages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    risk_tier TEXT NOT NULL CHECK (risk_tier IN ('safe', 'risky')),
    started_at TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    resolved_at TEXT,
    outcome_key TEXT,
    berry_delta INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_active_voyages_due
    ON active_voyages (resolved, started_at);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    action_type TEXT NOT NULL,
    delta_requested INTEGER NOT NULL,
    delta_applied INTEGER NOT NULL,
    reason TEXT NOT NULL,
    balance_after INTEGER,
    related_voyage_id INTEGER,
    status TEXT NOT NULL DEFAULT 'applied',
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (related_voyage_id) REFERENCES active_voyages (id)
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_created
    ON transactions (guild_id, user_id, created_at);
