"""Model javobidagi search/replace bloklarini ajratish.

Format (Aider uslubi):

    path/to/file.py
    <<<<<<< SEARCH
    eski qatorlar (aynan fayldagidek)
    =======
    yangi qatorlar
    >>>>>>> REPLACE

Bo'sh SEARCH — yangi fayl yaratish (yoki fayl oxiriga qo'shish).
Parser kichik modellarning odatiy xatolariga chidamli: ``` ichida/tashqarisida, fayl nomi
oldida `###`, `File:` yoki backtick, markerlardagi `<`/`>` soni farqli bo'lishi.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEAD = re.compile(r"^\s*<{5,9}\s*SEARCH\s*$")
_DIV = re.compile(r"^\s*={5,9}\s*$")
_TAIL = re.compile(r"^\s*>{5,9}\s*REPLACE\s*$")
_FENCE = re.compile(r"^\s*```")
_PATH_CLEAN = re.compile(r"^(?:#+\s*|(?:file|fayl|path)\s*:\s*|[*`'\"]+)+|[*`'\":]+$", re.IGNORECASE)


@dataclass
class Block:
    path: str
    search: str
    replace: str

    @property
    def is_create(self) -> bool:
        return not self.search.strip()


@dataclass
class ParseError:
    message: str


def _clean_path(line: str) -> str:
    s = line.strip()
    prev = None
    while prev != s:
        prev = s
        s = _PATH_CLEAN.sub("", s).strip()
    return s.replace("\\", "/")


def _looks_like_path(s: str) -> bool:
    return bool(s) and " " not in s and ("/" in s or "." in s) and len(s) < 200


def parse_fenced(text: str) -> list[tuple[str, str]]:
    """SEARCH/REPLACE'siz kod bloklari: [(yo'l, kod)]. Yo'l — blokdan oldingi qatorda yoki
    blokning birinchi qatoridagi izohda (`# shop/api.py`, `// handlers.go`)."""
    lines = text.splitlines()
    out: list[tuple[str, str]] = []
    i = 0
    while i < len(lines):
        if not _FENCE.match(lines[i]):
            i += 1
            continue
        start = i
        i += 1
        body: list[str] = []
        while i < len(lines) and not _FENCE.match(lines[i]):
            body.append(lines[i])
            i += 1
        i += 1  # yopuvchi ```
        if any(_HEAD.match(l) for l in body):
            continue
        path = None
        j = start - 1
        while j >= 0 and j >= start - 2:
            if lines[j].strip():
                c = _clean_path(lines[j])
                if _looks_like_path(c):
                    path = c
                break
            j -= 1
        if path is None and body:
            m = re.match(r"^\s*(?:#|//)\s*(?:file:\s*)?(\S+\.\w+)\s*$", body[0], re.IGNORECASE)
            if m and _looks_like_path(m.group(1)):
                path, body = m.group(1), body[1:]
        if path is not None:
            out.append((path.replace("\\", "/"), "\n".join(body)))
    return out


def parse_blocks(text: str) -> tuple[list[Block], list[ParseError]]:
    lines = text.splitlines()
    blocks: list[Block] = []
    errors: list[ParseError] = []
    last_path: str | None = None
    i = 0
    while i < len(lines):
        if not _HEAD.match(lines[i]):
            i += 1
            continue
        # fayl nomi: SEARCH dan oldingi bo'sh bo'lmagan, ``` bo'lmagan qator
        path = None
        j = i - 1
        while j >= 0 and j >= i - 3:
            cand = lines[j]
            if cand.strip() and not _FENCE.match(cand):
                c = _clean_path(cand)
                if _looks_like_path(c):
                    path = c
                break
            j -= 1
        if path is None:
            path = last_path
        if path is None:
            errors.append(ParseError(f"{i + 1}-qatordagi SEARCH blokidan oldin fayl yo'li yozilmagan"))
        i += 1
        search: list[str] = []
        while i < len(lines) and not _DIV.match(lines[i]):
            if _HEAD.match(lines[i]) or _TAIL.match(lines[i]):
                break
            search.append(lines[i])
            i += 1
        if i >= len(lines) or not _DIV.match(lines[i]):
            errors.append(ParseError(f"{path}: SEARCH bloki `=======` bilan ajratilmagan"))
            continue
        i += 1
        replace: list[str] = []
        while i < len(lines) and not _TAIL.match(lines[i]):
            if _HEAD.match(lines[i]):
                break
            replace.append(lines[i])
            i += 1
        if i >= len(lines) or not _TAIL.match(lines[i]):
            errors.append(ParseError(f"{path}: blok `>>>>>>> REPLACE` bilan yopilmagan"))
            continue
        i += 1
        if path is not None:
            blocks.append(Block(path, "\n".join(search), "\n".join(replace)))
            last_path = path
    return blocks, errors
