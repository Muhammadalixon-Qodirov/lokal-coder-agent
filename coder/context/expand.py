"""Vazifa matnini qidiruv uchun kengaytirish (LLM yordamida).

Muammo: vazifa o'zbekcha ("tavsiyada ustun nomi"), kod inglizcha (`recommendation_service.py`).
Model vazifani repo lug'ati (papka/modul nomlari) bilan birga ko'rib, inglizcha kalit so'zlar va
ehtimoliy identifikatorlarni qaytaradi. Javob JSON sxema bilan cheklangan — format buzilmaydi.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass, field

from coder.llm import LLM

SCHEMA = {
    "type": "object",
    "properties": {
        "keywords": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        "identifiers": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
    },
    "required": ["keywords", "identifiers"],
}

PROMPT = """You help locate code in a repository for a programming task.
The task may be written in Uzbek, Russian or English. The code is in English.

Repository vocabulary (directory and module names that exist):
{vocab}

Task:
{task}

Return JSON with:
- "keywords": English words describing what code must be found (translate from Uzbek if needed), 4-12 items
- "identifiers": likely names of files, modules, functions or classes involved, preferably from the vocabulary above, up to 10 items
"""


@dataclass
class Expansion:
    keywords: list[str] = field(default_factory=list)
    identifiers: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        return " ".join(self.keywords + self.identifiers)


def repo_vocab(con: sqlite3.Connection, limit: int = 220) -> str:
    """Eng ko'p uchraydigan papka va fayl nomlari (generic'lardan tashqari)."""
    c: Counter[str] = Counter()
    for (path,) in con.execute("SELECT path FROM files"):
        parts = path.rsplit(".", 1)[0].split("/")
        for p in parts:
            if len(p) >= 3 and not p.startswith(("test_", "_")) and not re.match(r"^\d", p):
                c[p] += 1
    generic = {"src", "app", "lib", "internal", "components", "index", "__init__", "tests", "test"}
    words = [w for w, _ in c.most_common() if w not in generic][:limit]
    return ", ".join(sorted(words))


def expand(llm: LLM, con: sqlite3.Connection, task: str) -> Expansion:
    prompt = PROMPT.format(vocab=repo_vocab(con), task=task.strip())
    c = llm.chat([{"role": "user", "content": prompt}], max_tokens=200, temperature=0.0, json_schema=SCHEMA)
    try:
        data = json.loads(c.text)
    except json.JSONDecodeError:
        return Expansion()
    clean = lambda xs: [x.strip() for x in xs if isinstance(x, str) and 2 <= len(x.strip()) <= 60]  # noqa: E731
    return Expansion(clean(data.get("keywords", [])), clean(data.get("identifiers", [])))
