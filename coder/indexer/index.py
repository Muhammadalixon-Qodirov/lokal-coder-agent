"""Repo'ni incremental indekslash: faqat sha o'zgargan fayllar qayta parse qilinadi."""

from __future__ import annotations

import hashlib
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from coder.indexer import db
from coder.indexer.history import update_history
from coder.indexer.imports import resolve_imports
from coder.indexer.langs import FileFacts, extract, lang_for
from coder.indexer.walker import list_files, looks_minified

BODY_LIMIT = 6000

_WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def split_words(s: str) -> list[str]:
    """`getUserProfile_v2` → ['get', 'user', 'profile', 'v', '2']"""
    return [w.lower() for w in _WORD.findall(s)]


def _terms(*parts: str) -> str:
    seen: dict[str, None] = {}
    for p in parts:
        for ident in _IDENT.findall(p):
            for w in split_words(ident):
                if len(w) > 1:
                    seen.setdefault(w, None)
    return " ".join(seen)


@dataclass
class IndexStats:
    files: int = 0
    parsed: int = 0
    unchanged: int = 0
    removed: int = 0
    skipped: int = 0
    symbols: int = 0
    edges: int = 0
    seconds: float = 0.0


def db_path(root: Path) -> Path:
    return root / ".agent" / "index.db"


def open_index(root: Path) -> sqlite3.Connection:
    root = root.resolve()
    agent_dir = root / ".agent"
    agent_dir.mkdir(exist_ok=True)
    gi = agent_dir / ".gitignore"
    if not gi.exists():
        gi.write_text("*\n")
    return db.connect(db_path(root))


def _delete_file(con: sqlite3.Connection, file_id: int) -> None:
    con.execute("DELETE FROM fts WHERE file_id = ?", (file_id,))
    con.execute("DELETE FROM files WHERE id = ?", (file_id,))  # symbols/edges — CASCADE


def _store(con: sqlite3.Connection, rel: str, lang: str, sha: str, src: bytes, facts: FileFacts) -> None:
    text = src.decode("utf-8", "replace")
    lines = text.splitlines()
    cur = con.execute(
        "INSERT INTO files(path, lang, sha, lines) VALUES (?, ?, ?, ?)",
        (rel, lang, sha, len(lines)),
    )
    file_id = cur.lastrowid

    ids: list[int] = []
    for s in facts.symbols:
        parent_id = ids[s.parent] if s.parent is not None else None
        cur = con.execute(
            "INSERT INTO symbols(file_id, name, qualname, kind, signature, start_line, end_line, parent_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (file_id, s.name, s.qualname, s.kind, s.signature, s.start_line, s.end_line, parent_id),
        )
        ids.append(cur.lastrowid)
        body = "\n".join(lines[s.start_line - 1 : s.end_line])[:BODY_LIMIT]
        con.execute(
            "INSERT INTO fts(path, name, terms, body, symbol_id, file_id) VALUES (?, ?, ?, ?, ?, ?)",
            (rel, s.qualname, _terms(s.qualname, rel, body), body, ids[-1], file_id),
        )

    # fayl darajasidagi yozuv: modul kodi (importlar, global o'zgaruvchilar) ham topilsin
    head = text[:BODY_LIMIT]
    con.execute(
        "INSERT INTO fts(path, name, terms, body, symbol_id, file_id) VALUES (?, ?, ?, ?, NULL, ?)",
        (rel, "", _terms(rel, head), head, file_id),
    )

    con.executemany(
        "INSERT INTO edges(file_id, src_symbol, dst_name, kind, line) VALUES (?, ?, ?, ?, ?)",
        [(file_id, ids[r.src] if r.src is not None else None, r.dst_name, r.kind, r.line) for r in facts.refs],
    )


def resolve_edges(con: sqlite3.Connection) -> None:
    """calls/inherits bog'lanishlarini nom bo'yicha symbol'larga ulash (taxminiy)."""
    con.executescript(
        """
        UPDATE edges SET dst_symbol = NULL, confidence = NULL WHERE kind != 'imports';

        -- 1) shu faylning o'zida yagona shu nomli symbol
        UPDATE edges SET
            dst_symbol = (SELECT MIN(s.id) FROM symbols s WHERE s.file_id = edges.file_id AND s.name = edges.dst_name),
            confidence = 'same_file'
        WHERE kind != 'imports'
          AND (SELECT COUNT(*) FROM symbols s WHERE s.file_id = edges.file_id AND s.name = edges.dst_name) = 1;

        -- 2) butun repoda yagona
        DROP TABLE IF EXISTS temp._uniq;
        CREATE TEMP TABLE _uniq AS
            SELECT name, MIN(id) AS id, COUNT(*) AS n FROM symbols GROUP BY name;
        CREATE INDEX temp._uniq_name ON _uniq(name);

        UPDATE edges SET
            dst_symbol = (SELECT id FROM _uniq WHERE _uniq.name = edges.dst_name),
            confidence = 'unique'
        WHERE kind != 'imports' AND confidence IS NULL
          AND (SELECT n FROM _uniq WHERE _uniq.name = edges.dst_name) = 1;

        UPDATE edges SET confidence = 'ambiguous'
        WHERE kind != 'imports' AND confidence IS NULL
          AND EXISTS (SELECT 1 FROM _uniq WHERE _uniq.name = edges.dst_name);

        UPDATE edges SET confidence = 'external'
        WHERE kind != 'imports' AND confidence IS NULL;

        DROP TABLE temp._uniq;
        """
    )


def index_repo(root: Path, progress=None) -> IndexStats:
    """`progress(done, total, path)` — ixtiyoriy callback."""
    t0 = time.perf_counter()
    root = root.resolve()
    con = open_index(root)
    stats = IndexStats()

    existing = {r["path"]: (r["id"], r["sha"]) for r in con.execute("SELECT id, path, sha FROM files")}
    files = list_files(root)
    stats.files = len(files)
    seen: set[str] = set()

    with con:
        for i, rel in enumerate(files):
            if progress:
                progress(i, len(files), rel)
            try:
                src = (root / rel).read_bytes()
            except OSError:
                stats.skipped += 1
                continue
            seen.add(rel)
            sha = hashlib.sha1(src).hexdigest()
            old = existing.get(rel)
            if old and old[1] == sha:
                stats.unchanged += 1
                continue
            if old:
                _delete_file(con, old[0])
            if looks_minified(src):
                stats.skipped += 1
                continue
            lang = lang_for(rel)
            try:
                facts = extract(lang, src)
            except Exception:  # noqa: BLE001 — bitta buzuq fayl butun indeksni to'xtatmasin
                stats.skipped += 1
                continue
            _store(con, rel, lang, sha, src, facts)
            stats.parsed += 1

        for rel, (file_id, _) in existing.items():
            if rel not in seen:
                _delete_file(con, file_id)
                stats.removed += 1

        if stats.parsed or stats.removed:
            resolve_edges(con)
            resolve_imports(con)
        update_history(con, root)

    stats.symbols = con.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
    stats.edges = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    con.close()
    stats.seconds = time.perf_counter() - t0
    return stats
