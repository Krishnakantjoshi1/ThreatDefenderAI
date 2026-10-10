"""SQLite schema. Only masked previews and fingerprints are stored - never full private messages."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    preview TEXT,
    fingerprint TEXT,
    score INTEGER NOT NULL,
    verdict TEXT NOT NULL,
    action TEXT NOT NULL,
    category TEXT,
    result_json TEXT NOT NULL,
    explanation_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_scans_created ON scans(created_at);

CREATE TABLE IF NOT EXISTS quarantine (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    scan_id INTEGER,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    reason TEXT,
    score INTEGER NOT NULL,
    sha256 TEXT,
    path TEXT,
    status TEXT NOT NULL DEFAULT 'quarantined'
);

CREATE TABLE IF NOT EXISTS memory (
    fingerprint TEXT PRIMARY KEY,
    category TEXT,
    risk INTEGER NOT NULL,
    indicators_json TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""
