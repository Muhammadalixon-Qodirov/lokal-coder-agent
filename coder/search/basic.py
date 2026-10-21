"""Indeks ustidagi asosiy so'rovlar: symbol qidirish, FTS, kim chaqiradi / nimani chaqiradi."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from coder.indexer.index import split_words


@dataclass
class Hit:
    path: str
    line: int
    end_line: int
    kind: str
    qualname: str
    signature: str
    score: float = 0.0


def _hit(r: sqlite3.Row, score: float = 0.0) -> Hit:
    return Hit(r["path"], r["start_line"], r["end_line"], r["kind"], r["qualname"], r["signature"] or "", score)


_SYMBOL_SQL = """
    SELECT f.path, s.start_line, s.end_line, s.kind, s.qualname, s.signature
    FROM symbols s JOIN files f ON f.id = s.file_id
"""


def find_symbol(con: sqlite3.Connection, name: str, limit: int = 50) -> list[Hit]:
    """Aniq nom yoki `Class.method` bo'yicha."""
    rows = con.execute(
        _SYMBOL_SQL + " WHERE s.name = ? OR s.qualname = ? OR s.qualname LIKE ? ORDER BY f.path, s.start_line LIMIT ?",
        (name, name, f"%.{name}", limit),
    ).fetchall()
    return [_hit(r) for r in rows]


def _fts_query(text: str) -> str | None:
    words: dict[str, None] = {}
    for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+", text):
        words.setdefault(tok.lower(), None)
        for w in split_words(tok):
            if len(w) > 1:
                words.setdefault(w, None)
    if not words:
        return None
    return " OR ".join(f'"{w}"' for w in words)


def search_text(con: sqlite3.Connection, text: str, limit: int = 20) -> list[Hit]:
    """BM25 bo'yicha: nom > terms > path > body."""
    q = _fts_query(text)
    if not q:
        return []
    rows = con.execute(
        """
        SELECT fts.path, fts.symbol_id, bm25(fts, 2.0, 10.0, 4.0, 1.0) AS rank,
               s.start_line, s.end_line, s.kind, s.qualname, s.signature
        FROM fts LEFT JOIN symbols s ON s.id = fts.symbol_id
        WHERE fts MATCH ?
        ORDER BY rank LIMIT ?
        """,
        (q, limit),
    ).fetchall()
    out = []
    for r in rows:
        if r["symbol_id"] is None:
            out.append(Hit(r["path"], 1, 1, "file", r["path"], "", -r["rank"]))
        else:
            out.append(_hit(r, -r["rank"]))
    return out


def callers(con: sqlite3.Connection, name: str, limit: int = 100) -> list[tuple[Hit | None, str, int, str]]:
    """`name` ni kim chaqiradi / meros oladi: (chaqiruvchi symbol, fayl, qator, ishonch)."""
    rows = con.execute(
        """
        SELECT f.path AS ref_path, e.line AS ref_line, e.confidence, e.kind AS edge_kind,
               s.start_line, s.end_line, s.kind, s.qualname, s.signature, f.path
        FROM edges e
        JOIN files f ON f.id = e.file_id
        LEFT JOIN symbols s ON s.id = e.src_symbol
        WHERE e.dst_name = ? AND e.kind != 'imports'
        ORDER BY f.path, e.line LIMIT ?
        """,
        (name.rsplit(".", 1)[-1], limit),
    ).fetchall()
    return [
        (_hit(r) if r["qualname"] else None, r["ref_path"], r["ref_line"], f"{r['edge_kind']}:{r['confidence']}")
        for r in rows
    ]


def callees(con: sqlite3.Connection, qualname: str) -> list[tuple[str, str, Hit | None]]:
    """`qualname` symbol ichidan nima chaqiriladi: (nom, ishonch, topilgan symbol)."""
    rows = con.execute(
        """
        SELECT e.dst_name, e.confidence, e.kind AS edge_kind,
               f2.path, d.start_line, d.end_line, d.kind, d.qualname, d.signature
        FROM symbols s
        JOIN edges e ON e.src_symbol = s.id
        LEFT JOIN symbols d ON d.id = e.dst_symbol
        LEFT JOIN files f2 ON f2.id = d.file_id
        WHERE s.qualname = ? AND e.kind != 'imports'
        ORDER BY e.line
        """,
        (qualname,),
    ).fetchall()
    return [(r["dst_name"], f"{r['edge_kind']}:{r['confidence']}", _hit(r) if r["qualname"] else None) for r in rows]
