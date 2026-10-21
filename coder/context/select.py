"""LLM bilan nomzod fayllarni qayta saralash.

Heuristik ranking eng yaxshi N ta faylni beradi; model ularning imzolarini ko'rib, vazifa uchun
kerakli fayllarni tanlaydi. JSON sxemadagi `enum` faqat haqiqiy yo'llarga ruxsat beradi —
model mavjud bo'lmagan fayl nomini o'ylab topa olmaydi.
"""

from __future__ import annotations

import json
import sqlite3

from coder.context.rank import Ranking
from coder.llm import LLM

PROMPT = """You are choosing which files of a repository must be read or edited to complete a programming task.
The task may be written in Uzbek, Russian or English.

Task:
{task}

Candidate files (with their main definitions):
{candidates}

Pick the files that most likely must be edited or read to do this task, most important first.
Include the related test file if the task changes tested behaviour. Pick at most {k}.
"""


def _entry(con: sqlite3.Connection, fid: int, path: str, max_syms: int = 6) -> str:
    rows = con.execute(
        "SELECT signature FROM symbols WHERE file_id = ? AND parent_id IS NULL ORDER BY start_line LIMIT ?",
        (fid, max_syms),
    ).fetchall()
    sigs = "; ".join((r["signature"] or "")[:80] for r in rows)
    return f"- {path}" + (f"  — {sigs}" if sigs else "")


def select_files(
    llm: LLM, con: sqlite3.Connection, task: str, r: Ranking, n_candidates: int = 25, k: int = 6
) -> list[str]:
    paths = {row["id"]: row["path"] for row in con.execute("SELECT id, path FROM files")}
    top = [fid for fid, _ in sorted(r.files.items(), key=lambda kv: -kv[1])[:n_candidates] if fid in paths]
    if len(top) <= 1:
        return [paths[f] for f in top]
    cand_paths = [paths[f] for f in top]
    schema = {
        "type": "object",
        "properties": {"files": {"type": "array", "items": {"type": "string", "enum": cand_paths}, "maxItems": k}},
        "required": ["files"],
    }
    prompt = PROMPT.format(task=task.strip(), candidates="\n".join(_entry(con, f, paths[f]) for f in top), k=k)
    c = llm.chat([{"role": "user", "content": prompt}], max_tokens=400, temperature=0.0, json_schema=schema)
    try:
        chosen = json.loads(c.text).get("files", [])
    except json.JSONDecodeError:
        return []
    seen: dict[str, None] = {}
    for p in chosen:
        if p in cand_paths:
            seen.setdefault(p, None)
    return list(seen)


# tanlangan fayl eng yuqori heuristik ballning shuncha ulushini oladi: model tartibni o'zgartiradi,
# lekin heuristika to'g'ri topgan fayllarni butunlay siqib chiqarmaydi
SELECT_BOOST = 0.5


def apply_selection(con: sqlite3.Connection, r: Ranking, chosen: list[str]) -> None:
    """Tanlangan fayllarni reyting boshiga ko'taradi (tartibini saqlagan holda)."""
    if not chosen or not r.files:
        return
    ids = {row["path"]: row["id"] for row in con.execute("SELECT id, path FROM files")}
    top = max(r.files.values())
    for i, p in enumerate(chosen):
        fid = ids.get(p)
        if fid is not None:
            r.files[fid] = r.files.get(fid, 0.0) + top * SELECT_BOOST * (1.0 - 0.1 * i)
            r.reasons[fid].insert(0, f"LLM tanladi #{i + 1}")
