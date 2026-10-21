"""Import'larni repo ichidagi fayllarga ulash → `file_links` jadvali.

Tilga xos qoidalar (heuristik, lekin statik):
  python  — `a.b.c` modul nomi, `.x` / `..x` nisbiy importlar
  ts/js   — `./x`, `../x` nisbiy; `@/x`, `~/x` alias (src/ ostida suffiks bo'yicha)
  go      — paket yo'li → repo ichidagi papka (suffiks bo'yicha), papkadagi barcha fayllar
  dart    — `package:<nom>/x.dart` → lib/x.dart; nisbiy yo'llar
"""

from __future__ import annotations

import posixpath
import sqlite3
from collections import defaultdict

GO_MAX_FILES = 30


class _Maps:
    def __init__(self, files: list[sqlite3.Row]):
        self.by_noext: dict[str, list[int]] = defaultdict(list)
        self.suffix: dict[str, list[int]] = defaultdict(list)
        self.py_mod: dict[str, list[int]] = defaultdict(list)
        self.dir_files: dict[str, list[int]] = defaultdict(list)
        self.dir_suffix: dict[str, set[str]] = defaultdict(set)
        for f in files:
            fid, path, lang = f["id"], f["path"], f["lang"]
            noext = path.rsplit(".", 1)[0]
            self.by_noext[noext].append(fid)
            parts = noext.split("/")
            keys = ["/".join(parts[i:]) for i in range(len(parts))]
            if parts[-1] in ("index", "__init__") and len(parts) > 1:
                keys += ["/".join(parts[i:-1]) for i in range(len(parts) - 1)]
            for k in keys:
                self.suffix[k].append(fid)
            if lang == "python":
                mod = noext.removesuffix("/__init__").replace("/", ".")
                mp = mod.split(".")
                for i in range(len(mp)):
                    self.py_mod[".".join(mp[i:])].append(fid)
            d = posixpath.dirname(path)
            self.dir_files[d].append(fid)
            dp = d.split("/") if d else []
            for i in range(len(dp)):
                self.dir_suffix["/".join(dp[i:])].add(d)


def _unique(ids: list[int] | None, limit: int = 1) -> list[int]:
    return list(ids) if ids and len(ids) <= limit else []


def _resolve(m: _Maps, lang: str, path: str, spec: str) -> list[int]:
    here = posixpath.dirname(path)
    if lang == "python":
        if spec.startswith("."):
            level = len(spec) - len(spec.lstrip("."))
            base = here
            for _ in range(level - 1):
                base = posixpath.dirname(base)
            rest = spec.lstrip(".").replace(".", "/")
            full = posixpath.join(base, rest) if rest else base
            return m.by_noext.get(full) or m.by_noext.get(full + "/__init__") or []
        return _unique(m.py_mod.get(spec), limit=2)

    if lang in ("typescript", "tsx", "javascript"):
        if spec.startswith("."):
            full = posixpath.normpath(posixpath.join(here, spec))
            return m.by_noext.get(full) or m.by_noext.get(full + "/index") or []
        for prefix in ("@/", "~/", "src/"):
            if spec.startswith(prefix):
                key = spec[len(prefix):]
                return _unique(m.suffix.get("src/" + key)) or _unique(m.suffix.get(key))
        return []  # tashqi paket (react, axios, ...)

    if lang == "go":
        parts = spec.split("/")
        for i in range(len(parts) - 1):  # eng uzun mos suffiksdan boshlab, kamida 2 qism
            dirs = m.dir_suffix.get("/".join(parts[i:]))
            if dirs and len(dirs) == 1:
                d = next(iter(dirs))
                return m.dir_files[d][:GO_MAX_FILES]
        return []

    if lang == "dart":
        spec = spec.removesuffix(".dart")
        if spec.startswith("package:"):
            rest = spec[len("package:"):].split("/", 1)
            if len(rest) < 2:
                return []
            return _unique(m.suffix.get("lib/" + rest[1])) or _unique(m.suffix.get(rest[1]))
        if spec.startswith("dart:"):
            return []
        full = posixpath.normpath(posixpath.join(here, spec))
        return m.by_noext.get(full) or []
    return []


def resolve_imports(con: sqlite3.Connection) -> None:
    con.execute("DELETE FROM file_links")
    files = con.execute("SELECT id, path, lang FROM files").fetchall()
    maps = _Maps(files)
    meta = {f["id"]: f for f in files}
    links: set[tuple[int, int]] = set()
    for e in con.execute("SELECT file_id, dst_name FROM edges WHERE kind = 'imports'"):
        f = meta[e["file_id"]]
        for dst in _resolve(maps, f["lang"], f["path"], e["dst_name"]):
            if dst != f["id"]:
                links.add((f["id"], dst))
    con.executemany("INSERT INTO file_links(src_file, dst_file, kind) VALUES (?, ?, 'imports')", sorted(links))
