"""Search/replace bloklarini fayllarga qo'llash.

Moslik bosqichma-bosqich yumshatiladi:
  1. aniq moslik (yagona bo'lishi shart)
  2. qator oxiridagi bo'shliqlarni e'tiborsiz qoldirish
  3. chekinish (indent) farqi — butun blok bir xil siljigan bo'lsa, REPLACE ham shunga moslanadi
  4. fuzzy (difflib, o'xshashlik ≥ 0.92)
Topilmasa — modelga fayldagi eng yaqin joy ko'rsatiladigan xato qaytariladi.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path

from coder.edit.blocks import Block
from coder.edit.symbolic import _PLACEHOLDER, apply_definitions
from coder.indexer.langs import lang_for

FUZZY_MIN = 0.92
ELIDE_MARKERS = ("⋮...", "⋮")


@dataclass
class EditOutcome:
    applied: list[Block] = field(default_factory=list)
    failed: list[tuple[Block, str]] = field(default_factory=list)
    originals: dict[str, str | None] = field(default_factory=dict)  # yo'l → asl matn (None — yangi fayl)

    @property
    def changed_paths(self) -> list[str]:
        return list(self.originals)


def _find_unique(hay: list[str], needle: list[str], key) -> tuple[int | None, int]:
    """(boshlanish indeksi, topilganlar soni)."""
    n = len(needle)
    if n == 0 or n > len(hay):
        return None, 0
    nk = [key(x) for x in needle]
    hk = [key(x) for x in hay]
    hits = [i for i in range(len(hay) - n + 1) if hk[i : i + n] == nk]
    return (hits[0] if len(hits) == 1 else None), len(hits)


def _indent(s: str) -> str:
    return s[: len(s) - len(s.lstrip())]


def _reindent(lines: list[str], src_ref: str, dst_ref: str) -> list[str]:
    """SEARCH'ning birinchi qatori chekinishi fayldagidan farq qilsa, REPLACE'ni ham siljitish."""
    a, b = _indent(src_ref), _indent(dst_ref)
    if a == b:
        return lines
    out = []
    for line in lines:
        if line.startswith(a):
            out.append(b + line[len(a):])
        elif not line.strip():
            out.append(line)
        else:
            out.append(line)
    return out


def _closest(hay: list[str], needle: list[str]) -> tuple[int, float]:
    n = len(needle)
    best_i, best_r = 0, 0.0
    target = "\n".join(needle)
    for i in range(max(1, len(hay) - n + 1)):
        r = difflib.SequenceMatcher(None, "\n".join(hay[i : i + n]), target, autojunk=False).ratio()
        if r > best_r:
            best_i, best_r = i, r
    return best_i, best_r


def replace_in(content: str, search: str, replace: str) -> tuple[str | None, str]:
    """(yangi matn yoki None, xato/izoh)."""
    if any(m in search for m in ELIDE_MARKERS):
        return None, "SEARCH ichida `⋮...` bor — bu context'dagi qisqartirish belgisi, faylda yo'q. Faqat haqiqiy qatorlarni yozing."
    trailing_nl = content.endswith("\n")
    hay = content.splitlines()
    needle = search.splitlines()
    while needle and not needle[0].strip():
        needle = needle[1:]
    while needle and not needle[-1].strip():
        needle = needle[:-1]
    rep = replace.splitlines()
    if not needle:
        return None, "SEARCH bo'sh"

    def done(i: int, new: list[str]) -> str:
        out = hay[:i] + new + hay[i + len(needle):]
        return "\n".join(out) + ("\n" if trailing_nl else "")

    # 1–2: aniq / qator oxiri bo'shliqlarisiz
    for key in (lambda s: s, lambda s: s.rstrip()):
        i, n = _find_unique(hay, needle, key)
        if i is not None:
            return done(i, rep), ""
        if n > 1:
            return None, f"SEARCH faylda {n} marta uchraydi — yagona bo'lishi uchun atrofidagi qatorlarni ham qo'shing"

    # 3: chekinish farqi
    i, n = _find_unique(hay, needle, lambda s: s.strip())
    if i is not None:
        return done(i, _reindent(rep, needle[0], hay[i])), ""
    if n > 1:
        return None, f"SEARCH (chekinishsiz) faylda {n} marta uchraydi — atrofidagi qatorlarni ham qo'shing"

    # 4: fuzzy
    i, ratio = _closest(hay, needle)
    if ratio >= FUZZY_MIN:
        return done(i, _reindent(rep, needle[0], hay[i])), f"fuzzy ({ratio:.2f})"
    snippet = "\n".join(hay[i : i + len(needle) + 2])
    return None, (
        f"SEARCH faylda topilmadi (eng yaqin moslik {ratio:.0%}). Faylning shu joyi aslida:\n"
        f"```\n{snippet}\n```\nSEARCH'ni aynan fayldagi qatorlar bilan qayta yozing."
    )


def _resolve_path(repo: Path, path: str, known: list[str]) -> str:
    """Model yo'lni qisqartirib yozgan bo'lsa (`views.py`), repo'dagi yagona mos faylni topish."""
    p = path.strip().lstrip("./")
    if (repo / p).exists():
        return p
    # `path/to/shop/services.py`, `services.py` → oldingi qismlarni tashlab, yagona mos faylni qidirish
    parts = p.split("/")
    for i in range(len(parts)):
        suffix = "/".join(parts[i:])
        matches = [k for k in known if k == suffix or k.endswith("/" + suffix)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            break
    return p


_DEF_PATTERNS = {
    "python": re.compile(r"^\s*(?:async\s+)?def\s+(\w+)|^\s*class\s+(\w+)", re.M),
    "go": re.compile(r"^func\s+(?:\([^)]*\)\s*)?(\w+)|^type\s+(\w+)", re.M),
    "typescript": re.compile(r"\bfunction\s+(\w+)|\bclass\s+(\w+)", re.M),
    "tsx": re.compile(r"\bfunction\s+(\w+)|\bclass\s+(\w+)", re.M),
    "javascript": re.compile(r"\bfunction\s+(\w+)|\bclass\s+(\w+)", re.M),
}


def removed_definitions(path: str, search: str, replace: str) -> set[str]:
    """SEARCH'da bor, REPLACE'da yo'q bo'lgan funksiya/klasslar (model tasodifan o'chirib yuborganlari)."""
    pat = _DEF_PATTERNS.get(lang_for(path) or "")
    if pat is None:
        return set()
    names = lambda s: {a or b for a, b in pat.findall(s)}  # noqa: E731
    return names(search) - names(replace)


def apply_blocks(
    repo: Path, blocks: list[Block], known_files: list[str] | None = None, allow_delete: bool = True
) -> EditOutcome:
    out = EditOutcome()
    known = known_files or []
    for b in blocks:
        if not allow_delete:
            gone = removed_definitions(b.path, b.search, b.replace)
            if gone:
                out.failed.append((b, f"{b.path}: REPLACE mavjud `{'`, `'.join(sorted(gone))}` ni o'chirib yuboradi, "
                                      "vazifa esa buni so'ramagan. Uni saqlab qoling: yangi kodni uning yoniga qo'shing."))
                continue
        rel = _resolve_path(repo, b.path, known)
        target = repo / rel
        if not _safe_target(repo, rel):
            out.failed.append((b, f"{b.path}: repo tashqarisidagi yo'l"))
            continue
        exists = target.exists()
        current = target.read_text(encoding="utf-8", errors="replace") if exists else None
        if rel not in out.originals:
            out.originals[rel] = current

        if b.is_create:
            if exists and current and current.strip():
                new = current.rstrip("\n") + "\n" + b.replace.rstrip("\n") + "\n"  # oxiriga qo'shish
            else:
                new = b.replace.rstrip("\n") + "\n"
        else:
            if not exists:
                out.failed.append((b, f"{rel}: fayl mavjud emas (yangi fayl uchun SEARCH bo'sh bo'lishi kerak)"))
                continue
            new, note = replace_in(current, b.search, b.replace)
            if new is None:
                out.failed.append((b, f"{rel}: {note}"))
                continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new, encoding="utf-8", newline="")
        out.applied.append(Block(rel, b.search, b.replace))
    _drop_unchanged(repo, out)
    return out


def _drop_unchanged(repo: Path, out: EditOutcome) -> None:
    """Haqiqatda o'zgarmagan fayllarni originals'dan olib tashlash."""
    for rel in list(out.originals):
        p, orig = repo / rel, out.originals[rel]
        now = p.read_text(encoding="utf-8", errors="replace") if p.exists() else None
        if now == orig:
            del out.originals[rel]


def _safe_target(repo: Path, rel: str) -> bool:
    return ".." not in Path(rel).parts and (repo / rel).resolve().is_relative_to(repo.resolve())


def apply_fenced(repo: Path, items: list[tuple[str, str]], known_files: list[str] | None = None) -> EditOutcome:
    """SEARCH/REPLACE'siz kod bloklari: yangi fayl yoki funksiya/klass darajasida almashtirish."""
    out = EditOutcome()
    known = known_files or []
    for path, code in items:
        rel = _resolve_path(repo, path, known)
        block = Block(rel, "", code)
        if not _safe_target(repo, rel):
            out.failed.append((block, f"{path}: repo tashqarisidagi yo'l"))
            continue
        target = repo / rel
        exists = target.exists()
        current = target.read_text(encoding="utf-8", errors="replace") if exists else None
        lang = lang_for(rel)
        if not exists:
            if not code.strip() or all(_PLACEHOLDER.match(l) or not l.strip() for l in code.splitlines()):
                continue
            new = code.rstrip("\n") + "\n"
        else:
            if lang is None:
                out.failed.append((block, f"{rel}: bu fayl turi uchun SEARCH/REPLACE blok ishlating"))
                continue
            new, note = apply_definitions(current, code, lang)
            if new is None:
                out.failed.append((block, f"{rel}: {note}"))
                continue
            if new == current:
                continue
        out.originals.setdefault(rel, current)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new, encoding="utf-8", newline="")
        out.applied.append(block)
    _drop_unchanged(repo, out)
    return out


def rollback(repo: Path, originals: dict[str, str | None]) -> None:
    for rel, orig in originals.items():
        p = repo / rel
        if orig is None:
            if p.exists():
                p.unlink()
        else:
            p.write_text(orig, encoding="utf-8", newline="")


def unified_diff(repo: Path, originals: dict[str, str | None]) -> str:
    parts = []
    for rel, orig in originals.items():
        p = repo / rel
        new = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        old = orig or ""
        if old == new:
            continue
        parts.extend(difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile=f"a/{rel}" if orig is not None else "/dev/null", tofile=f"b/{rel}",
        ))
    return "".join(parts)
