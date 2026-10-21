"""Edit'dan keyingi deterministik tuzatishlar (model emas, dastur bajaradi).

Kichik model eng ko'p qiladigan mexanik xato — importni unutish:
  python — ruff F821 (aniqlanmagan nom) → standart kutubxona xaritasi bo'yicha import qo'shiladi
  go     — `strings.X` ishlatilgan, lekin import qilinmagan → qo'shiladi; ishlatilmagan std import → olib
           tashlanadi; so'ng `gofmt -w`
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from coder.indexer.langs import _parser, _text

PY_STD = {
    "datetime": "from datetime import datetime", "timezone": "from datetime import timezone",
    "timedelta": "from datetime import timedelta", "date": "from datetime import date",
    "re": "import re", "json": "import json", "os": "import os", "sys": "import sys", "math": "import math",
    "uuid": "import uuid", "time": "import time", "random": "import random", "hashlib": "import hashlib",
    "itertools": "import itertools", "functools": "import functools", "logging": "import logging",
    "Path": "from pathlib import Path", "Decimal": "from decimal import Decimal",
    "dataclass": "from dataclasses import dataclass", "field": "from dataclasses import field",
    "asdict": "from dataclasses import asdict", "Enum": "from enum import Enum",
    "defaultdict": "from collections import defaultdict", "Counter": "from collections import Counter",
    "OrderedDict": "from collections import OrderedDict", "deque": "from collections import deque",
    "Any": "from typing import Any", "Optional": "from typing import Optional", "Callable": "from typing import Callable",
    "Iterable": "from typing import Iterable", "Iterator": "from typing import Iterator", "Union": "from typing import Union",
    "cast": "from typing import cast", "TypeVar": "from typing import TypeVar", "Generic": "from typing import Generic",
}

GO_STD = {
    "strings": "strings", "strconv": "strconv", "fmt": "fmt", "errors": "errors", "sort": "sort",
    "slices": "slices", "maps": "maps", "time": "time", "os": "os", "io": "io", "bytes": "bytes",
    "sync": "sync", "context": "context", "math": "math", "unicode": "unicode", "regexp": "regexp",
    "json": "encoding/json", "http": "net/http", "utf8": "unicode/utf8", "filepath": "path/filepath",
    "atomic": "sync/atomic", "log": "log", "url": "net/url", "httptest": "net/http/httptest",
}


# ---------------------------------------------------------------- python

def _py_missing(repo: Path, files: list[str]) -> dict[str, set[str]]:
    if not shutil.which("ruff") or not files:
        return {}
    r = subprocess.run(
        ["ruff", "check", "--select", "F821", "--output-format", "json", "--no-cache", *files],
        cwd=repo, capture_output=True, timeout=60,
    )
    try:
        items = json.loads(r.stdout.decode("utf-8", "replace") or "[]")
    except json.JSONDecodeError:
        return {}
    out: dict[str, set[str]] = {}
    for it in items:
        m = re.search(r"`(\w+)`", it.get("message", ""))
        if m and m.group(1) in PY_STD:
            rel = Path(it["filename"]).resolve().relative_to(repo.resolve()).as_posix()
            out.setdefault(rel, set()).add(m.group(1))
    return out


def _py_add_imports(text: str, names: set[str]) -> str:
    lines = text.splitlines()
    root = _parser("python").parse(text.encode()).root_node
    imports = [c for c in root.named_children if c.type in ("import_statement", "import_from_statement", "future_import_statement")]
    for name in sorted(names):
        stmt = PY_STD[name]
        m = re.match(r"from (\S+) import (\w+)", stmt)
        merged = False
        if m:
            mod = m.group(1)
            for i, l in enumerate(lines):  # mavjud `from mod import a, b` ga qo'shish
                mm = re.match(rf"^from {re.escape(mod)} import ([\w, ]+)$", l)
                if mm:
                    names_now = [x.strip() for x in mm.group(1).split(",")]
                    if name not in names_now:
                        lines[i] = f"from {mod} import {', '.join(names_now + [name])}"
                    merged = True
                    break
        if not merged:
            at = imports[-1].end_point[0] + 1 if imports else 0
            lines.insert(at, stmt)
            root = _parser("python").parse("\n".join(lines).encode()).root_node
            imports = [c for c in root.named_children if c.type in ("import_statement", "import_from_statement", "future_import_statement")]
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


# ---------------------------------------------------------------- go

def _go_fix(text: str) -> str:
    root = _parser("go").parse(text.encode()).root_node
    imported: dict[str, str] = {}  # nom → yo'l
    for decl in (c for c in root.named_children if c.type == "import_declaration"):
        stack = [decl]
        while stack:
            n = stack.pop()
            if n.type == "import_spec":
                path = _text(n.child_by_field_name("path")).strip('"')
                alias = n.child_by_field_name("name")
                imported[_text(alias) if alias is not None else path.rsplit("/", 1)[-1]] = path
            stack.extend(n.named_children)
    used: set[str] = set()
    locals_: set[str] = set()
    stack = [root]
    while stack:
        n = stack.pop()
        if n.type == "selector_expression":
            op = n.child_by_field_name("operand")
            if op is not None and op.type == "identifier":
                used.add(_text(op))
        elif n.type == "qualified_type":  # tur pozitsiyasida: http.ResponseWriter
            pkg = n.child_by_field_name("package")
            if pkg is not None:
                used.add(_text(pkg))
        elif n.type in ("parameter_declaration", "short_var_declaration", "var_spec", "range_clause"):
            for c in n.named_children:
                if c.type in ("identifier", "expression_list"):
                    locals_.update(_text(x) for x in ([c] if c.type == "identifier" else c.named_children))
        if n.type != "import_declaration":
            stack.extend(n.named_children)
    missing = sorted(p for p in used - set(imported) - locals_ if p in GO_STD)
    unused = sorted(name for name, path in imported.items() if name not in used and name != "_" and path in GO_STD.values())
    if not missing and not unused:
        return text
    paths = [p for n, p in imported.items() if n not in unused] + [GO_STD[m] for m in missing]
    aliases = {p: n for n, p in imported.items() if n != p.rsplit("/", 1)[-1]}
    block = "import (\n" + "".join(f'\t{aliases[p] + " " if p in aliases else ""}"{p}"\n' for p in sorted(set(paths))) + ")"
    decls = [c for c in root.named_children if c.type == "import_declaration"]
    lines = text.splitlines()
    if decls:
        a, b = decls[0].start_point[0], decls[-1].end_point[0] + 1
        lines[a:b] = block.splitlines() if paths else []
    else:
        pkg = next((c for c in root.named_children if c.type == "package_clause"), None)
        at = pkg.end_point[0] + 1 if pkg is not None else 0
        lines[at:at] = [""] + block.splitlines()
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- umumiy

def autofix(repo: Path, changed: list[str]) -> list[str]:
    """O'zgargan fayllarni tuzatadi; qilingan ishlar ro'yxatini qaytaradi."""
    notes: list[str] = []
    py = [f for f in changed if f.endswith(".py") and (repo / f).exists()]
    for rel, names in _py_missing(repo, py).items():
        p = repo / rel
        p.write_text(_py_add_imports(p.read_text(encoding="utf-8"), names), encoding="utf-8", newline="")
        notes.append(f"{rel}: import qo'shildi ({', '.join(sorted(names))})")
    go = [f for f in changed if f.endswith(".go") and (repo / f).exists()]
    for rel in go:
        p = repo / rel
        old = p.read_text(encoding="utf-8")
        new = _go_fix(old)
        if new != old:
            p.write_text(new, encoding="utf-8", newline="")
            notes.append(f"{rel}: importlar tuzatildi")
    if go and shutil.which("gofmt"):
        subprocess.run(["gofmt", "-w", *go], cwd=repo, capture_output=True, timeout=60)
    return notes
