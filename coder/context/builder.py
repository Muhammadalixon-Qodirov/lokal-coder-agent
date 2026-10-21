"""Vazifa uchun modelga yuboriladigan context'ni yig'ish (token byudjeti bilan).

Natija ikki qismdan iborat:
  * code     — eng tegishli fayllar: kichigi butunligicha, kattasidan faqat kerakli symbollar
  * repomap  — keyingi tegishli fayllarning faqat imzolari (Aider RepoMap)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from coder.context.rank import Ranking, rank

ELIDE = "⋮..."
LANG_FENCE = {"python": "python", "go": "go", "typescript": "ts", "tsx": "tsx", "javascript": "js", "dart": "dart"}


def est_tokens(text: str) -> int:
    """Taxminiy token soni (Qwen tokenizer kodda ~3–3.5 belgi/token)."""
    return len(text) // 3 + 1


@dataclass
class FileChunk:
    path: str
    lang: str
    text: str
    whole: bool
    score: float
    reasons: list[str]

    def render(self) -> str:
        note = "" if self.whole else " (qisman)"
        return f"### {self.path}{note}\n```{LANG_FENCE.get(self.lang, '')}\n{self.text}\n```"


@dataclass
class ContextPack:
    task: str
    files: list[FileChunk] = field(default_factory=list)
    repomap: str = ""
    ranking: Ranking | None = None

    def render(self) -> str:
        parts = []
        if self.repomap:
            parts.append("## Repo xaritasi (boshqa tegishli fayllar, faqat imzolar)\n" + self.repomap)
        if self.files:
            parts.append("## Kod\n\n" + "\n\n".join(f.render() for f in self.files))
        return "\n\n".join(parts)

    @property
    def tokens(self) -> int:
        return est_tokens(self.render())

    @property
    def paths(self) -> list[str]:
        return [f.path for f in self.files]


def _spans_for_file(con: sqlite3.Connection, file_id: int, chosen: dict[int, float], n_lines: int) -> list[tuple[int, int]]:
    """Fayldan qaysi qatorlar kiritiladi (1 dan boshlanadi, ikkala chegara ham kiradi)."""
    rows = con.execute(
        "SELECT id, parent_id, start_line, end_line FROM symbols WHERE file_id = ?", (file_id,)
    ).fetchall()
    by_id = {r["id"]: r for r in rows}
    picked = [by_id[sid] for sid in chosen if sid in by_id]
    picked_ids = {r["id"] for r in picked}

    spans: list[tuple[int, int]] = [(1, min(12, n_lines))]  # importlar
    for r in picked:
        has_child = any(c["parent_id"] == r["id"] for c in rows if c["id"] in picked_ids)
        size = r["end_line"] - r["start_line"]
        if has_child and size > 60:
            spans.append((r["start_line"], r["start_line"] + 2))  # katta klass: faqat sarlavha
        else:
            spans.append((r["start_line"], r["end_line"]))
        # ota klass sarlavhasi — metod qaysi klassga tegishli ekani ko'rinsin
        p = by_id.get(r["parent_id"]) if r["parent_id"] else None
        if p is not None:
            spans.append((p["start_line"], p["start_line"] + 1))

    spans.sort()
    merged: list[tuple[int, int]] = []
    for a, b in spans:
        a, b = max(1, a - 1), min(n_lines, b + 1)
        if merged and a <= merged[-1][1] + 3:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def _render_spans(lines: list[str], spans: list[tuple[int, int]]) -> str:
    out: list[str] = []
    prev_end = 0
    for a, b in spans:
        if a > prev_end + 1:
            out.append(ELIDE)
        out.extend(lines[a - 1 : b])
        prev_end = b
    if prev_end < len(lines):
        out.append(ELIDE)
    return "\n".join(out)


def _repomap_entry(con: sqlite3.Connection, file_id: int, path: str, max_syms: int = 25) -> str:
    rows = con.execute(
        "SELECT kind, signature, parent_id FROM symbols WHERE file_id = ? ORDER BY start_line LIMIT ?",
        (file_id, max_syms),
    ).fetchall()
    if not rows:
        return ""
    body = "\n".join(("    " if r["parent_id"] else "  ") + (r["signature"] or "") for r in rows)
    return f"{path}:\n{body}"


def build_context(
    con: sqlite3.Connection,
    repo: Path,
    task: str,
    code_budget: int = 7000,
    map_budget: int = 1500,
    whole_file_tokens: int = 1500,
    max_file_tokens: int = 2000,
    max_files: int = 10,
    extra_keywords: list[str] | None = None,
    extra_idents: list[str] | None = None,
    ranking: Ranking | None = None,
) -> ContextPack:
    r = ranking if ranking is not None else rank(con, task, extra_keywords, extra_idents)
    pack = ContextPack(task=task, ranking=r)
    files = sorted(r.files.items(), key=lambda kv: -kv[1])
    if not files:
        return pack

    meta = {row["id"]: row for row in con.execute("SELECT id, path, lang FROM files")}
    sym_by_file: dict[int, dict[int, float]] = {}
    for row in con.execute(
        f"SELECT id, file_id FROM symbols WHERE id IN ({','.join('?' * len(r.symbols))})", list(r.symbols)
    ) if r.symbols else []:
        sym_by_file.setdefault(row["file_id"], {})[row["id"]] = r.symbols[row["id"]]

    used = 0
    in_code: set[int] = set()
    for fid, score in files:
        if len(pack.files) >= max_files or used >= code_budget:
            break
        m = meta.get(fid)
        if m is None:
            continue
        try:
            text = (repo / m["path"]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        whole = est_tokens(text) <= whole_file_tokens
        if whole:
            chunk_text = text.rstrip("\n")
        else:
            chosen = dict(sorted(sym_by_file.get(fid, {}).items(), key=lambda kv: -kv[1])[:6])
            chunk_text = _render_spans(lines, _spans_for_file(con, fid, chosen, len(lines)))
        cost = est_tokens(chunk_text) + 20
        if used + cost > code_budget or cost > max_file_tokens:
            # sig'masa — faqat eng kuchli 2 symbol bilan urinib ko'ramiz
            chosen = dict(sorted(sym_by_file.get(fid, {}).items(), key=lambda kv: -kv[1])[:2])
            if not chosen:
                continue
            chunk_text = _render_spans(lines, _spans_for_file(con, fid, chosen, len(lines)))
            whole = False
            cost = est_tokens(chunk_text) + 20
            if used + cost > code_budget:
                continue
        pack.files.append(FileChunk(m["path"], m["lang"], chunk_text, whole, score, list(r.reasons.get(fid, []))))
        in_code.add(fid)
        used += cost

    map_used = 0
    entries = []
    for fid, _ in files:
        if fid in in_code or fid not in meta:
            continue
        entry = _repomap_entry(con, fid, meta[fid]["path"])
        if not entry:
            continue
        cost = est_tokens(entry)
        if map_used + cost > map_budget:
            continue
        entries.append(entry)
        map_used += cost
    pack.repomap = "\n".join(entries)
    return pack
