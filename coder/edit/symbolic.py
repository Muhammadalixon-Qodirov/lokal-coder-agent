"""Funksiya/klass darajasidagi edit — SEARCH/REPLACE'siz javoblar uchun.

Kichik model ko'pincha shunday yozadi:

    shop/services.py
    ```python
    def create_customer(self, name, email):
        ...butun yangi funksiya...
    ```

Bu kod tree-sitter bilan parse qilinadi va har bir ta'rif (funksiya, metod, klass, tip) fayldagi
shu nomli ta'rifning o'rniga qo'yiladi; yangi ta'rif qo'shiladi; yetishmayotgan importlar qo'shiladi.
Klass qisman berilgan bo'lsa (faqat bitta metod) — qolgan a'zolari o'chib ketmaydi, a'zo darajasida birlashtiriladi.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass

from tree_sitter import Node

from coder.indexer.langs import EXTRACTORS, _parser, _text

_PLACEHOLDER = re.compile(r"^\s*(?:#|//)\s*(?:\.\.\.|…|rest of|existing|unchanged|qolgan)", re.IGNORECASE)

IMPORT_TYPES = {
    "python": ("import_statement", "import_from_statement", "future_import_statement"),
    "go": ("import_declaration",),
    "typescript": ("import_statement",),
    "tsx": ("import_statement",),
    "javascript": ("import_statement",),
    "dart": ("import_or_export",),
}
SKIP_TYPES = {"comment", "package_clause", "line_comment", "block_comment", "documentation_comment"}
CLASS_KINDS = {"class", "struct", "interface", "mixin", "extension", "enum"}


@dataclass
class DefBlock:
    path: str
    code: str


# ---------------------------------------------------------------- ta'riflarni topish

@dataclass
class Def:
    kind: str
    name: str
    node: Node        # o'zgartiriladigan oraliq (dekorator / export bilan)
    inner: Node       # ta'rif node'ining o'zi
    qual: str         # Go: Recv.Method


def _wrapped(n: Node) -> Node:
    """Dekorator yoki export bilan o'ralgan bo'lsa — tashqi node."""
    p = n.parent
    while p is not None and p.type in ("decorated_definition", "export_statement"):
        n, p = p, p.parent
    return n


def _definition(lang: str, n: Node) -> tuple[str, str, str] | None:
    ex = EXTRACTORS[lang]
    d = ex.definition(n, None)
    if not d or not d[1]:
        return None
    kind, name = d[0], d[1]
    qual = f"{d[2]}.{name}" if len(d) > 2 and d[2] else name
    return kind, name, qual


def _unwrap_top(n: Node) -> Node:
    """decorated_definition / export_statement / type_declaration → ichidagi ta'rif (bir necha qavat)."""
    for _ in range(4):
        m = _unwrap_once(n)
        if m is n:
            return n
        n = m
    return n


def _unwrap_once(n: Node) -> Node:
    if n.type == "decorated_definition":
        return n.child_by_field_name("definition") or n
    if n.type == "export_statement":
        return n.child_by_field_name("declaration") or next((c for c in n.named_children if c.type != "comment"), n)
    if n.type == "type_declaration":  # Go: type X struct{...}
        return next((c for c in n.named_children if c.type == "type_spec"), n)
    if n.type == "lexical_declaration":  # TS: const f = () => ...
        return next((c for c in n.named_children if c.type == "variable_declarator"), n)
    return n


def _defs_in(lang: str, container: Node) -> list[Def]:
    """Konteyner (modul yoki klass tanasi) ning bevosita ta'riflari."""
    out = []
    for c in container.named_children:
        inner = _unwrap_top(c)
        d = _definition(lang, inner)
        if d:
            out.append(Def(d[0], d[1], c if c is not inner else _wrapped(inner), inner, d[2]))
    return out


def _class_body(n: Node) -> Node | None:
    body = n.child_by_field_name("body")
    if body is not None:
        return body
    for c in n.named_children:
        if c.type in ("class_body", "block", "declaration_list", "field_declaration_list", "enum_body"):
            return c
    return None


def _all_defs(lang: str, root: Node) -> tuple[list[Def], dict[str, list[Def]]]:
    top = _defs_in(lang, root)
    members: dict[str, list[Def]] = {}
    for d in top:
        if d.kind in CLASS_KINDS:
            body = _class_body(d.inner)
            if body is not None:
                members[d.name] = _defs_in(lang, body)
    return top, members


# ---------------------------------------------------------------- qatorlar bilan ishlash

def _indent_of(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _indent(code: str, prefix: str) -> list[str]:
    return [(prefix + l if l.strip() else l) for l in code.splitlines()]


def _span(n: Node) -> tuple[int, int]:
    """[boshlanish, tugash) qator indekslari."""
    return n.start_point[0], n.end_point[0] + 1


def _node_code(src_lines: list[str], n: Node) -> str:
    a, b = _span(n)
    return textwrap.dedent("\n".join(src_lines[a:b]))


# ---------------------------------------------------------------- asosiy funksiya

def apply_definitions(content: str, snippet: str, lang: str) -> tuple[str | None, str]:
    """(yangi matn yoki None, xato/izoh). Placeholder'dan iborat snippet — o'zgarishsiz qaytadi."""
    if lang not in EXTRACTORS or lang == "dart":  # Dart: tana signaturadan alohida node — xavfli
        return None, f"`{lang}` uchun funksiya darajasidagi edit qo'llab-quvvatlanmaydi — SEARCH/REPLACE blok ishlating"
    lines_s = [l for l in snippet.splitlines() if not _PLACEHOLDER.match(l)]
    snippet = textwrap.dedent("\n".join(lines_s)).strip("\n")
    if not snippet.strip():
        return content, "bo'sh"

    parser = _parser(lang)
    s_lines = snippet.splitlines()
    s_root = parser.parse(snippet.encode()).root_node
    if s_root.has_error:
        return None, "kod blokida sintaksis xatosi bor — SEARCH/REPLACE blok ishlating"

    f_lines = content.splitlines()
    f_root = parser.parse(content.encode()).root_node
    f_top, f_members = _all_defs(lang, f_root)
    edits: list[tuple[int, int, list[str]]] = []  # [a, b) → yangi qatorlar
    loose: list[str] = []

    def file_def(name: str, qual: str) -> Def | None:
        cands = [d for d in f_top if d.qual == qual] or [d for d in f_top if d.name == name and d.qual == name]
        return cands[0] if len(cands) == 1 else None

    def member_def(name: str) -> tuple[str, Def] | None:
        hits = [(cls, d) for cls, ms in f_members.items() for d in ms if d.name == name]
        return hits[0] if len(hits) == 1 else None

    def class_insert_point(cls_name: str) -> tuple[int, str]:
        cls = next(d for d in f_top if d.name == cls_name)
        body = _class_body(cls.inner)
        end = cls.node.end_point[0]
        # Python: tananing oxirgi qatoridan keyin; qavsli tillar: yopuvchi `}` dan oldin
        if lang == "python":
            ref = f_lines[body.named_children[0].start_point[0]] if body is not None and body.named_children else "    "
            return end + 1, _indent_of(ref) or "    "
        members = f_members.get(cls_name) or []
        ref = f_lines[members[0].node.start_point[0]] if members else "    "
        return end, _indent_of(ref) or "    "

    imports_needed: list[str] = []
    for n in s_root.named_children:
        if n.type in SKIP_TYPES:
            continue
        if n.type in IMPORT_TYPES.get(lang, ()):
            imports_needed.append(_text(n))
            continue
        inner = _unwrap_top(n)
        d = _definition(lang, inner)
        if not d:
            text = _text(n).strip()
            if text and text not in content:
                loose.append(text)
            continue
        kind, name, qual = d
        code = _node_code(s_lines, n)
        target = file_def(name, qual)
        if target is not None and kind in CLASS_KINDS and lang != "go":
            # klass: to'liq berilganmi yoki faqat bir qismi?
            s_body = _class_body(inner)
            s_members = {m.name for m in _defs_in(lang, s_body)} if s_body is not None else set()
            f_names = {m.name for m in f_members.get(name, [])}
            if f_names <= s_members:
                a, b = _span(target.node)
                edits.append((a, b, _indent(code, _indent_of(f_lines[a]))))
            else:
                err = _merge_class(lang, f_lines, target, f_members.get(name, []), s_lines, inner, edits, class_insert_point)
                if err:
                    return None, err
            continue
        if target is not None:
            a, b = _span(target.node)
            edits.append((a, b, _indent(code, _indent_of(f_lines[a]))))
            continue
        hit = member_def(name) if kind in ("method", "function", "getter", "setter", "constructor") else None
        if hit is not None:
            _, m = hit
            a, b = _span(m.node)
            edits.append((a, b, _indent(code, _indent_of(f_lines[a]))))
            continue
        # yangi ta'rif: metodga o'xshasa (self) va fayldagi yagona klassga — o'sha klassga
        classes = [x for x in f_top if x.kind in CLASS_KINDS and x.name in f_members]
        is_method = lang == "python" and re.match(r"\s*(?:async\s+)?def\s+\w+\s*\(\s*(self|cls)\b", code)
        if is_method and len(classes) == 1:
            at, ind = class_insert_point(classes[0].name)
            edits.append((at, at, [""] + _indent(code, ind)))
        else:
            at = len(f_lines)
            edits.append((at, at, ["", ""] + code.splitlines() if lang == "python" else [""] + code.splitlines()))

    if loose:
        return None, ("kod blokida ta'rif bo'lmagan qatorlar bor (" + "; ".join(l[:40] for l in loose[:3]) +
                      ") — bunday o'zgarish uchun SEARCH/REPLACE blok ishlating")
    if not edits and not imports_needed:
        return content, "o'zgarish yo'q"

    _add_imports(lang, f_lines, f_root, imports_needed, content, edits)
    edits.sort(key=lambda e: (e[0], e[1]))
    for (a1, b1, _), (a2, _b2, _) in zip(edits, edits[1:]):
        if a2 < b1:
            return None, "bir xil joyga bir nechta o'zgarish to'g'ri keldi — SEARCH/REPLACE blok ishlating"
    for a, b, new in reversed(edits):
        f_lines[a:b] = new
    return "\n".join(f_lines) + ("\n" if content.endswith("\n") or not content else ""), ""


def _merge_class(lang, f_lines, target: Def, f_members: list[Def], s_lines, s_inner: Node, edits, insert_point) -> str:
    """Qisman berilgan klass: a'zolarni nom bo'yicha almashtirish/qo'shish, yangi maydonlarni qo'shish."""
    s_body = _class_body(s_inner)
    if s_body is None:
        return "klass tanasi topilmadi"
    by_name = {m.name: m for m in f_members}
    f_body = _class_body(target.inner)
    f_text = "\n".join(f_lines[slice(*_span(target.node))])
    new_fields: list[str] = []
    for c in s_body.named_children:
        if c.type in SKIP_TYPES:
            continue
        inner = _unwrap_top(c)
        d = _definition(lang, inner)
        code = _node_code(s_lines, c)
        if d and d[1] in by_name:
            a, b = _span(by_name[d[1]].node)
            edits.append((a, b, _indent(code, _indent_of(f_lines[a]))))
        elif d:
            at, ind = insert_point(target.name)
            edits.append((at, at, [""] + _indent(code, ind)))
        else:
            if code.strip() and code.strip() not in f_text and not (c.type == "expression_statement" and code.strip().startswith(('"""', "'''"))):
                new_fields.append(code)
    if new_fields:
        # maydonlar: klassdagi oxirgi ta'rif bo'lmagan qatordan keyin (birinchi metoddan oldin)
        first_member = min((m.node.start_point[0] for m in f_members), default=None)
        stmts = [c for c in (f_body.named_children if f_body is not None else [])
                 if first_member is None or c.start_point[0] < first_member]
        stmts = [c for c in stmts if _definition(lang, _unwrap_top(c)) is None]
        if stmts:
            at = stmts[-1].end_point[0] + 1
            ind = _indent_of(f_lines[stmts[-1].start_point[0]])
        else:
            at = (target.inner.start_point[0] + 1)
            ind = "    "
        edits.append((at, at, [l for f in new_fields for l in _indent(f, ind)]))
    return ""


_GO_SPEC = re.compile(r'(?:\b(?!import\b)\w+\s+)?"[^"]+"')  # alias "yo'l" (import kalit so'zisiz)


def _add_imports(lang: str, f_lines: list[str], f_root: Node, imports: list[str], content: str, edits) -> None:
    if not imports:
        return
    if lang == "go":
        specs = []
        for imp in imports:
            specs += _GO_SPEC.findall(imp)
        missing = [s for s in specs if s.split()[-1] not in content]
        if not missing:
            return
        decl = next((c for c in f_root.named_children if c.type == "import_declaration"), None)
        if decl is not None and "(" in _text(decl):
            end = decl.end_point[0]  # `)` qatori
            edits.append((end, end, ["\t" + s for s in missing]))
        elif decl is not None:
            a, b = _span(decl)
            old = _GO_SPEC.findall(_text(decl))
            edits.append((a, b, ["import ("] + ["\t" + s for s in old + missing] + [")"]))
        else:
            pkg = next((c for c in f_root.named_children if c.type == "package_clause"), None)
            at = pkg.end_point[0] + 1 if pkg is not None else 0
            edits.append((at, at, ["", "import ("] + ["\t" + s for s in missing] + [")"]))
        return
    missing = [i for i in imports if i.strip() not in content]
    if not missing:
        return
    existing = [c for c in f_root.named_children if c.type in IMPORT_TYPES.get(lang, ())]
    if existing:
        at = existing[-1].end_point[0] + 1
    else:
        at = 0
        # Python: modul docstring va `from __future__` dan keyin
        for c in f_root.named_children:
            if c.type in ("expression_statement", "future_import_statement", "comment") and c.start_point[0] == at:
                at = c.end_point[0] + 1
            else:
                break
    edits.append((at, at, [m.strip() for m in missing]))
