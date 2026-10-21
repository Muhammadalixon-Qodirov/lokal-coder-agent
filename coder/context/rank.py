"""Vazifa matniga qarab symbol va fayllarni baholash.

Uch manba birlashtiriladi (PLAN.md, 2-bosqich):
  1. aniq nom mosligi   — vazifada `UserSerializer` yoki `cards/models.py` yozilgan bo'lsa
  2. FTS (BM25)         — so'zlar bo'yicha
  3. graf               — topilgan symbollarning chaqiruvchi/chaqiriluvchilari
                          + fayllar grafida personalized PageRank (Aider RepoMap g'oyasi)
"""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field

from coder.search.basic import _fts_query

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_PATHLIKE = re.compile(r"[\w\-./]+\.(?:py|go|ts|tsx|js|jsx|dart)\b|[\w\-]+/[\w\-./]+")


_BACKTICK = re.compile(r"`([^`]+)`")


def _ident_strength(ident: str, quoted: set[str]) -> float:
    """Kodga o'xshagan nom kuchli, oddiy so'z ("add", "date") kuchsiz signal."""
    if ident in quoted or any(ident in q for q in quoted):
        return 10.0
    if "_" in ident or "." in ident or any(c.isupper() for c in ident[1:]):
        return 10.0  # snake_case, a.b, camelCase
    if ident[0].isupper():
        return 4.0
    return 1.5


@dataclass
class Ranking:
    symbols: dict[int, float] = field(default_factory=dict)   # symbol_id → ball
    files: dict[int, float] = field(default_factory=dict)     # file_id → ball
    reasons: dict[int, list[str]] = field(default_factory=lambda: defaultdict(list))  # file_id → sabablar


def _add(d: dict, k, v: float) -> None:
    d[k] = d.get(k, 0.0) + v


GUESS_STRENGTH = 3.0
EXTRA_WEIGHT = 0.5


def rank(
    con: sqlite3.Connection,
    task: str,
    extra_keywords: list[str] | None = None,
    extra_idents: list[str] | None = None,
    fts_limit: int = 40,
) -> Ranking:
    r = Ranking()
    sym_file: dict[int, int] = {}

    def sym(sid: int, fid: int, score: float, why: str) -> None:
        _add(r.symbols, sid, score)
        sym_file[sid] = fid
        if why not in r.reasons[fid]:
            r.reasons[fid].append(why)

    # 1) aniq nomlar (vazifada yozilgan — kuchli; model taxmin qilgan — o'rtacha)
    quoted = set(_BACKTICK.findall(task))
    idents = {m: _ident_strength(m, quoted) for m in _IDENT.findall(task) if len(m) >= 3}
    for guess in extra_idents or []:
        for m in _IDENT.findall(guess):
            if len(m) >= 3 and m not in idents:
                idents[m] = GUESS_STRENGTH
    for ident, strength in idents.items():
        last = ident.rsplit(".", 1)[-1]
        rows = con.execute(
            "SELECT id, file_id, name, qualname FROM symbols "
            "WHERE name = ? COLLATE NOCASE OR qualname = ? COLLATE NOCASE",
            (last, ident),
        ).fetchall()
        if not rows or len(rows) > 25:  # juda umumiy nom (masalan `get`) — foydasiz
            continue
        weight = strength / max(1, len(rows)) ** 0.5
        for row in rows:
            exact = row["name"] == last or row["qualname"] == ident
            sym(row["id"], row["file_id"], weight * (1.0 if exact else 0.6), f"nom: {row['qualname']}")

    extra_text = " ".join([*(extra_keywords or []), *(extra_idents or [])])
    # (matn, og'irlik): asl vazifa ustun, model kengaytmasi — yordamchi signal
    passes = [(task, 1.0)] + ([(extra_text, EXTRA_WEIGHT)] if extra_text else [])

    # 1b) fayl yo'llari
    for p in _PATHLIKE.findall(task):
        p = p.strip("./")
        for row in con.execute("SELECT id, path FROM files WHERE path LIKE ?", (f"%{p}%",)).fetchall()[:10]:
            _add(r.files, row["id"], 8.0)
            r.reasons[row["id"]].append(f"yo'l: {p}")

    # 1b') API marshrutlari: vazifada `/chat/status` → kodda "/status" yoki "/chat/status" satri
    for fid, seg in _route_hits(con, task):
        _add(r.files, fid, 6.0)
        r.reasons[fid].append(f"marshrut: {seg}")

    # 1c) fayl yo'li qismlari: "chat'da", "strategiya" → backend/app/chat/, strategy.py
    for text, w in passes:
        for fid, score, comp in _path_component_hits(con, text):
            _add(r.files, fid, w * score)
            why = f"papka/fayl: {comp}"
            if why not in r.reasons[fid]:
                r.reasons[fid].append(why)

    # 2) FTS
    for text, w in passes:
        q = _fts_query(text)
        if not q:
            continue
        rows = con.execute(
            "SELECT symbol_id, file_id, bm25(fts, 2.0, 10.0, 4.0, 1.0) AS rank FROM fts "
            "WHERE fts MATCH ? ORDER BY rank LIMIT ?",
            (q, fts_limit),
        ).fetchall()
        if rows:
            best = -rows[0]["rank"] or 1.0
            for row in rows:
                norm = (-row["rank"]) / best
                if row["symbol_id"] is None:
                    _add(r.files, row["file_id"], w * 2.0 * norm)
                else:
                    sym(row["symbol_id"], row["file_id"], w * 5.0 * norm, "matn" if w == 1.0 else "kengaytma")

    # 3a) grafdagi qo'shnilar (eng kuchli 10 ta symbol uchun)
    top = sorted(r.symbols.items(), key=lambda kv: -kv[1])[:10]
    for sid, score in top:
        share = 0.15 * score
        for row in con.execute(
            "SELECT s.id, s.file_id, s.qualname FROM edges e JOIN symbols s ON s.id = e.dst_symbol "
            "WHERE e.src_symbol = ? AND e.confidence IN ('same_file', 'unique') LIMIT 15",
            (sid,),
        ):
            sym(row["id"], row["file_id"], share, "chaqiriladi")
        for row in con.execute(
            "SELECT s.id, s.file_id FROM edges e JOIN symbols s ON s.id = e.src_symbol "
            "WHERE e.dst_symbol = ? LIMIT 15",
            (sid,),
        ):
            sym(row["id"], row["file_id"], share, "chaqiruvchi")

    # fayl balli: eng yaxshi symbol + qolganlarining kichik ulushi
    per_file: dict[int, list[float]] = defaultdict(list)
    for sid, score in r.symbols.items():
        per_file[sym_file[sid]].append(score)
    for fid, scores in per_file.items():
        scores.sort(reverse=True)
        _add(r.files, fid, scores[0] + 0.3 * sum(scores[1:4]))

    # 3b) git tarixi: odatda birga o'zgaradigan fayllar
    _add_cochange(con, r)

    # 3c) personalized PageRank — tanlangan fayllarga bog'liq markaziy fayllarni ko'taradi
    if r.files:
        pr = personalized_pagerank(con, r.files)
        top_score = max(r.files.values())
        for fid, val in pr.items():
            _add(r.files, fid, val * top_score * 0.5)
        _add_tests(con, r)
    return r


_ROUTE = re.compile(r"(?<![\w.])/(?:[A-Za-z_][\w\-]*|\{[^}]+\}|:\w+)(?:/(?:[A-Za-z_][\w\-]*|\{[^}]+\}|:\w+))*")


def _route_hits(con: sqlite3.Connection, task: str) -> list[tuple[int, str]]:
    """Marshrutning oxirgi 1–2 bo'lagi kod ichida satr sifatida uchraydigan fayllar."""
    out: list[tuple[int, str]] = []
    for route in _ROUTE.findall(task):
        segs = [s for s in route.strip("/").split("/") if s and not s.startswith(("{", ":"))]
        if not segs:
            continue
        candidates = ["/" + "/".join(segs[-2:])] if len(segs) >= 2 else []
        candidates.append("/" + segs[-1])
        for cand in candidates:
            rows = con.execute(
                "SELECT DISTINCT file_id FROM fts WHERE body LIKE ? OR body LIKE ? OR body LIKE ? LIMIT 12",
                (f'%"{cand}%', f"%'{cand}%", f"%`{cand}%"),
            ).fetchall()
            if rows:
                out.extend((row[0], cand) for row in rows)
                break  # aniqroq (uzunroq) moslik topildi
    return out


COCHANGE_WEIGHT = 0.5
COCHANGE_MIN_RATIO = 0.2


def _add_cochange(con: sqlite3.Connection, r: Ranking, top_n: int = 5) -> None:
    """P(b o'zgaradi | a o'zgardi) ≥ 20% bo'lsa, b ga a ballining ulushi qo'shiladi."""
    delta: dict[int, float] = {}
    for fid, score in sorted(r.files.items(), key=lambda kv: -kv[1])[:top_n]:
        churn = con.execute("SELECT score FROM churn WHERE file_id = ?", (fid,)).fetchone()
        if not churn or churn[0] <= 0:
            continue
        for row in con.execute("SELECT b, score FROM cochange WHERE a = ? ORDER BY score DESC LIMIT 8", (fid,)):
            ratio = min(1.0, row["score"] / churn[0])
            if ratio >= COCHANGE_MIN_RATIO:
                delta[row["b"]] = delta.get(row["b"], 0.0) + COCHANGE_WEIGHT * score * ratio
                r.reasons[row["b"]].append(f"birga o'zgaradi ({ratio:.0%})")
    for fid, d in delta.items():
        _add(r.files, fid, d)


_TEST_PATTERNS = (
    re.compile(r"^test_(.+)$"), re.compile(r"^(.+)_test$"), re.compile(r"^(.+)\.(?:test|spec)$"),
)


def _test_subject(path: str) -> str | None:
    """`tests/test_recommendations.py` → `recommendations`, `auth/service_test.go` → `service`."""
    stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    for p in _TEST_PATTERNS:
        m = p.match(stem)
        if m:
            return m.group(1).lower()
    return None


def _add_tests(con: sqlite3.Connection, r: Ranking, top_n: int = 6) -> None:
    """Eng tegishli fayllarning testlarini ko'tarish: o'zgarish odatda test bilan birga qilinadi."""
    tests = []
    for row in con.execute("SELECT id, path FROM files"):
        subj = _test_subject(row["path"])
        if subj:
            tests.append((row["id"], row["path"], subj))
    if not tests:
        return
    paths = {row["id"]: row["path"] for row in con.execute("SELECT id, path FROM files")}
    top = [(fid, s) for fid, s in sorted(r.files.items(), key=lambda kv: -kv[1]) if _test_subject(paths[fid]) is None]
    for fid, score in top[:top_n]:
        stem = paths[fid].rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
        parts = [stem] + [p for p in re.split(r"[_\-.]", stem) if len(p) >= 4 and p not in _GENERIC_COMPONENTS]
        go_dir = paths[fid].rsplit("/", 1)[0] if paths[fid].endswith(".go") else None
        for tid, tpath, subj in tests:
            same_pkg = go_dir is not None and tpath.rsplit("/", 1)[0] == go_dir
            if any(_stem_match(subj, p) or _stem_match(p, subj) for p in parts) or (same_pkg and subj == stem):
                _add(r.files, tid, 0.6 * score)
                why = f"test: {paths[fid].rsplit('/', 1)[-1]}"
                if why not in r.reasons[tid]:
                    r.reasons[tid].append(why)


_WORDS = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
_GENERIC_COMPONENTS = {"src", "app", "lib", "internal", "pkg", "cmd", "backend", "frontend", "components",
                       "index", "main", "utils", "common", "core", "api", "test", "tests", "versions",
                       "migrations"}
# vazifa matnidagi bu so'zlar fayl nomlariga bog'lanmaydi (commit prefikslari, umumiy fe'llar)
_TASK_STOPWORDS = {"fix", "feat", "chore", "docs", "refactor", "style", "perf", "build", "add", "update",
                   "remove", "delete", "change", "use", "new", "the", "and", "for", "with", "from", "into"}


def _stem_match(word: str, comp: str) -> bool:
    """Aniq moslik yoki umumiy o'zak (o'zbekcha qo'shimchalar: strategiya ~ strategy, chatda ~ chat)."""
    if word == comp:
        return True
    if len(comp) < 4 or len(word) < 4:
        return False
    n = 0
    for a, b in zip(word, comp):
        if a != b:
            break
        n += 1
    return n >= max(4, len(comp) - 1)


def _path_component_hits(con: sqlite3.Connection, task: str) -> list[tuple[int, float, str]]:
    words = {w.lower() for w in _WORDS.findall(task)} - _TASK_STOPWORDS
    if not words:
        return []
    comp_files: dict[str, set[int]] = defaultdict(set)
    for row in con.execute("SELECT id, path FROM files"):
        parts = row["path"].rsplit(".", 1)[0].lower().split("/")
        comps = set(parts)
        for p in parts:
            comps.update(x for x in re.split(r"[_\-.]", p) if x)
        for c in comps:
            if c not in _GENERIC_COMPONENTS and len(c) >= 3:
                comp_files[c].add(row["id"])
    total = max(1, con.execute("SELECT COUNT(*) FROM files").fetchone()[0])
    best: dict[int, tuple[float, str]] = {}
    for comp, fids in comp_files.items():
        if len(fids) > 0.3 * total:
            continue
        if not any(_stem_match(w, comp) for w in words):
            continue
        score = 4.0 / len(fids) ** 0.5
        for fid in fids:
            if fid not in best or best[fid][0] < score:
                best[fid] = (score, comp)
    return [(fid, s, c) for fid, (s, c) in best.items()]


def file_graph(con: sqlite3.Connection) -> dict[int, dict[int, float]]:
    """Fayllar orasidagi og'irlikli graf: chaqiruvlar + import'lar, teskari yo'nalish yarim og'irlikda
    (shunda modulni import qiluvchilar — masalan testlar — ham ko'tariladi)."""
    g: dict[int, dict[int, float]] = defaultdict(dict)

    def add(a: int, b: int, w: float) -> None:
        g[a][b] = g[a].get(b, 0.0) + w
        g[b][a] = g[b].get(a, 0.0) + 0.5 * w

    for row in con.execute(
        """
        SELECT e.file_id AS a, s.file_id AS b, COUNT(*) AS n
        FROM edges e JOIN symbols s ON s.id = e.dst_symbol
        WHERE e.confidence = 'unique' AND e.file_id != s.file_id
        GROUP BY a, b
        """
    ):
        add(row["a"], row["b"], row["n"] ** 0.5)
    for row in con.execute("SELECT src_file AS a, dst_file AS b FROM file_links"):
        add(row["a"], row["b"], 1.0)
    return g


def personalized_pagerank(
    con: sqlite3.Connection, seeds: dict[int, float], damping: float = 0.85, iters: int = 25
) -> dict[int, float]:
    g = file_graph(con)
    nodes = set(g) | {b for out in g.values() for b in out} | set(seeds)
    total = sum(seeds.values()) or 1.0
    pers = {n: seeds.get(n, 0.0) / total for n in nodes}
    rank_ = dict(pers)
    out_w = {a: sum(out.values()) for a, out in g.items()}
    for _ in range(iters):
        nxt = {n: (1 - damping) * pers[n] for n in nodes}
        dangling = 0.0
        for a in nodes:
            ra = rank_.get(a, 0.0)
            if not ra:
                continue
            if a in g and out_w[a] > 0:
                for b, w in g[a].items():
                    nxt[b] += damping * ra * w / out_w[a]
            else:
                dangling += ra
        if dangling:
            for n in nodes:
                nxt[n] += damping * dangling * pers[n]
        rank_ = nxt
    return rank_
