"""Indeks bazasi: bitta SQLite fayl (`<repo>/.agent/index.db`)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = "3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS files(
    id    INTEGER PRIMARY KEY,
    path  TEXT UNIQUE NOT NULL,
    lang  TEXT NOT NULL,
    sha   TEXT NOT NULL,
    lines INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS symbols(
    id         INTEGER PRIMARY KEY,
    file_id    INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    qualname   TEXT NOT NULL,
    kind       TEXT NOT NULL,
    signature  TEXT,
    start_line INTEGER NOT NULL,
    end_line   INTEGER NOT NULL,
    parent_id  INTEGER
);
CREATE INDEX IF NOT EXISTS symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS symbols_file ON symbols(file_id);

-- dst_symbol / confidence ni index.resolve_edges to'ldiradi:
--   same_file  — shu faylda shu nomli yagona symbol
--   unique     — butun repoda shu nomli yagona symbol
--   ambiguous  — repoda bir nechta shu nomli symbol
--   external   — repoda yo'q (kutubxona, builtin)
CREATE TABLE IF NOT EXISTS edges(
    id         INTEGER PRIMARY KEY,
    file_id    INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    src_symbol INTEGER,
    dst_name   TEXT NOT NULL,
    dst_symbol INTEGER,
    kind       TEXT NOT NULL,
    line       INTEGER NOT NULL,
    confidence TEXT
);
CREATE INDEX IF NOT EXISTS edges_dst_name   ON edges(dst_name);
CREATE INDEX IF NOT EXISTS edges_dst_symbol ON edges(dst_symbol);
CREATE INDEX IF NOT EXISTS edges_src        ON edges(src_symbol);
CREATE INDEX IF NOT EXISTS edges_file       ON edges(file_id);

-- fayl → fayl bog'lanishlari (import'lar repo ichidagi faylga ulangani), imports.resolve_imports
CREATE TABLE IF NOT EXISTS file_links(
    src_file INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    dst_file INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    kind     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS file_links_src ON file_links(src_file);
CREATE INDEX IF NOT EXISTS file_links_dst ON file_links(dst_file);

-- git tarixi: birga o'zgarish va o'zgarish chastotasi (history.update_history)
CREATE TABLE IF NOT EXISTS cochange(
    a     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    b     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    score REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS cochange_a ON cochange(a);
CREATE TABLE IF NOT EXISTS churn(
    file_id INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
    score   REAL NOT NULL
);

-- terms: camelCase / snake_case bo'laklarga ajratilgan so'zlar (getUserProfile → get user profile)
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
    path, name, terms, body,
    symbol_id UNINDEXED, file_id UNINDEXED,
    tokenize = 'unicode61'
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA synchronous=NORMAL")
    ver = None
    try:
        row = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        ver = row[0] if row else None
    except sqlite3.OperationalError:
        pass
    if ver not in (None, SCHEMA_VERSION):
        # sxema o'zgargan — indeksni noldan quramiz
        con.close()
        path.unlink()
        return connect(path)
    con.executescript(SCHEMA)
    con.execute("INSERT OR REPLACE INTO meta VALUES('schema_version', ?)", (SCHEMA_VERSION,))
    con.commit()
    return con
