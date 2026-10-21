"""Git tarixidan "birga o'zgaradigan fayllar" (co-change) signali.

Agar `queries.ts` deyarli har UI o'zgarishida `dictionaries.ts` bilan birga o'zgargan bo'lsa,
ulardan biri tanlanganda ikkinchisi ham context'ga ko'tariladi.
Yangi commitlar og'irroq (eksponensial so'nish). HEAD o'zgarmasa qayta hisoblanmaydi.
"""

from __future__ import annotations

import sqlite3
import subprocess
from collections import defaultdict
from pathlib import Path

MAX_COMMITS = 500
MAX_FILES_PER_COMMIT = 12  # katta (formatlash, rename) commitlar shovqin
DECAY = 0.995


def _git(root: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def update_history(con: sqlite3.Connection, root: Path) -> None:
    if not (root / ".git").exists():
        return
    head = (_git(root, "rev-parse", "HEAD") or "").strip()
    if not head:
        return
    row = con.execute("SELECT value FROM meta WHERE key = 'history_head'").fetchone()
    has_files = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    if row and row[0] == f"{head}:{has_files}":
        return

    log = _git(root, "log", f"-n{MAX_COMMITS}", "--no-merges", "--name-only", "--format=%x00")
    if log is None:
        return
    ids = {r["path"]: r["id"] for r in con.execute("SELECT id, path FROM files")}
    pair: dict[tuple[int, int], float] = defaultdict(float)
    churn: dict[int, float] = defaultdict(float)
    for i, block in enumerate(c for c in log.split("\0") if c.strip()):
        w = DECAY ** i
        fids = sorted({ids[p] for p in block.split("\n") if p in ids})
        for f in fids:
            churn[f] += w
        if 2 <= len(fids) <= MAX_FILES_PER_COMMIT:
            for a in fids:
                for b in fids:
                    if a != b:
                        pair[(a, b)] += w

    con.execute("DELETE FROM cochange")
    con.execute("DELETE FROM churn")
    con.executemany("INSERT INTO cochange(a, b, score) VALUES (?, ?, ?)", [(a, b, s) for (a, b), s in pair.items()])
    con.executemany("INSERT INTO churn(file_id, score) VALUES (?, ?)", list(churn.items()))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('history_head', ?)", (f"{head}:{has_files}",))
