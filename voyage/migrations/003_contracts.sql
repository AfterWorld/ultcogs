CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    target_user_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'claimed', 'resolved', 'expired')),
    total_pooled INTEGER NOT NULL DEFAULT 0,
    posting_fee_collected INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    claimed_by INTEGER,
    claimed_at TEXT,
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_contracts_target_status
    ON contracts (guild_id, target_user_id, status);

CREATE INDEX IF NOT EXISTS idx_contracts_expiry
    ON contracts (status, expires_at);

CREATE TABLE IF NOT EXISTS contract_contributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    contributor_user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    fee_amount INTEGER NOT NULL DEFAULT 0,
    anonymous INTEGER NOT NULL DEFAULT 0,
    contributed_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (contract_id) REFERENCES contracts (id)
);

CREATE INDEX IF NOT EXISTS idx_contract_contributions_contract
    ON contract_contributions (contract_id);

ALTER TABLE transactions ADD COLUMN related_contract_id INTEGER;
