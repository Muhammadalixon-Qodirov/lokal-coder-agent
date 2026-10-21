"""Har bir til uchun tree-sitter daraxtidan symbol va bog'lanishlarni ajratish.

Natija ataylab oddiy: symbol (funksiya, klass, metod, tip) va reference
(calls / imports / inherits). Reference faqat nom bo'yicha yoziladi —
qaysi symbolga tegishli ekanini keyin `index.resolve_edges` aniqlaydi.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from functools import cache

from tree_sitter import Node, Parser
from tree_sitter_language_pack import get_parser

sys.setrecursionlimit(20_000)

EXT_LANG = {
    ".py": "python",
    ".go": "go",
    ".ts": "typescript",
    ".mts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".dart": "dart",
}


def lang_for(path: str) -> str | None:
    dot = path.rfind(".")
    return EXT_LANG.get(path[dot:].lower()) if dot != -1 else None


@dataclass
class Symbol:
    name: str
    qualname: str
    kind: str
    signature: str
    start_line: int  # 1 dan boshlanadi
    end_line: int
    parent: int | None  # FileFacts.symbols ichidagi indeks


@dataclass
class Ref:
    src: int | None  # o'rab turgan symbol indeksi (None — modul darajasi)
    dst_name: str
    kind: str  # calls | imports | inherits
    line: int


@dataclass
class FileFacts:
    symbols: list[Symbol] = field(default_factory=list)
    refs: list[Ref] = field(default_factory=list)


# ---------------------------------------------------------------- yordamchilar

def _text(n: Node | None) -> str:
    return n.text.decode("utf-8", "replace") if n is not None else ""


def _field(n: Node, name: str) -> str | None:
    c = n.child_by_field_name(name)
    return _text(c) if c is not None else None


def _first(n: Node, types: tuple[str, ...]) -> Node | None:
    for c in n.named_children:
        if c.type in types:
            return c
    return None


def _squash(s: str, limit: int = 200) -> str:
    s = re.sub(r"\s+", " ", s).strip().rstrip("{:").strip()
    return s[:limit]


def _head(n: Node, body: Node | None) -> str:
    """Node matnining body'gacha bo'lgan qismi (signatura)."""
    end = body.start_byte if body is not None else n.end_byte
    return _squash(n.text[: end - n.start_byte].decode("utf-8", "replace"))


_NAME_NODES = {"identifier", "field_identifier", "property_identifier", "type_identifier",
               "private_property_identifier", "shorthand_property_identifier"}


def _callee(n: Node | None) -> str | None:
    """`a.b.c(...)` → `c`, `foo(...)` → `foo`. Murakkab ifodalar uchun None."""
    if n is None:
        return None
    if n.type in _NAME_NODES:
        return _text(n)
    for f in ("attribute", "property", "field", "name"):  # py, ts, go, generic_type
        c = n.child_by_field_name(f)
        if c is not None and c.type in _NAME_NODES:
            return _text(c)
    return None


def _strip_quotes(s: str) -> str:
    return s.strip().strip("'\"`")


# ---------------------------------------------------------------- tillar

class Extractor:
    # Dart: funksiya tanasi signaturaning ichida emas, keyingi qo'shni node'da
    body_sibling: str | None = None

    def definition(self, n: Node, parent: Symbol | None) -> tuple[str, str] | tuple[str, str, str] | None:
        """(kind, name) yoki (kind, name, qual_prefix)."""
        return None

    def refs(self, n: Node) -> list[tuple[str, str]]:
        return []

    def signature(self, n: Node) -> str:
        return _head(n, n.child_by_field_name("body"))


class PythonEx(Extractor):
    def definition(self, n, parent):
        if n.type == "function_definition":
            kind = "method" if parent is not None and parent.kind == "class" else "function"
            return kind, _field(n, "name")
        if n.type == "class_definition":
            return "class", _field(n, "name")
        return None

    def refs(self, n):
        t = n.type
        if t == "call":
            name = _callee(n.child_by_field_name("function"))
            return [("calls", name)] if name else []
        if t == "import_from_statement":
            mod = _field(n, "module_name")
            return [("imports", mod)] if mod else []
        if t == "import_statement":
            out = []
            for c in n.children_by_field_name("name"):
                if c.type == "aliased_import":
                    c = c.child_by_field_name("name")
                out.append(("imports", _text(c)))
            return out
        if t == "class_definition":
            sup = n.child_by_field_name("superclasses")
            if sup is not None:
                return [("inherits", x) for x in map(_callee, sup.named_children) if x]
        return []


class GoEx(Extractor):
    def definition(self, n, parent):
        t = n.type
        if t == "function_declaration":
            return "function", _field(n, "name")
        if t == "method_declaration":
            recv = n.child_by_field_name("receiver")
            rtype = None
            if recv is not None:
                stack = [recv]
                while stack and rtype is None:
                    x = stack.pop()
                    if x.type == "type_identifier":
                        rtype = _text(x)
                    stack.extend(reversed(x.named_children))
            return ("method", _field(n, "name"), rtype) if rtype else ("method", _field(n, "name"))
        if t == "type_spec":
            ty = n.child_by_field_name("type")
            kind = {"struct_type": "struct", "interface_type": "interface"}.get(ty.type if ty else "", "type")
            return kind, _field(n, "name")
        return None

    def signature(self, n):
        if n.type == "type_spec":
            ty = n.child_by_field_name("type")
            return f"type {_field(n, 'name')} {ty.type.removesuffix('_type') if ty else ''}".strip()
        return _head(n, n.child_by_field_name("body"))

    def refs(self, n):
        if n.type == "call_expression":
            name = _callee(n.child_by_field_name("function"))
            return [("calls", name)] if name else []
        if n.type == "import_spec":
            return [("imports", _strip_quotes(_field(n, "path") or ""))]
        return []


class TsEx(Extractor):
    """TypeScript, TSX va JavaScript uchun umumiy."""

    _DEFS = {
        "function_declaration": "function",
        "generator_function_declaration": "function",
        "class_declaration": "class",
        "abstract_class_declaration": "class",
        "interface_declaration": "interface",
        "type_alias_declaration": "type",
        "enum_declaration": "enum",
        "method_definition": "method",
    }
    _FN_VALUES = {"arrow_function", "function_expression", "function"}

    def definition(self, n, parent):
        kind = self._DEFS.get(n.type)
        if kind:
            name = _field(n, "name")
            return (kind, name) if name else None
        if n.type == "variable_declarator":
            v = n.child_by_field_name("value")
            name_node = n.child_by_field_name("name")
            if v is not None and v.type in self._FN_VALUES and name_node is not None and name_node.type == "identifier":
                return "function", _text(name_node)
        return None

    def signature(self, n):
        if n.type == "variable_declarator":
            v = n.child_by_field_name("value")
            return _head(n, v.child_by_field_name("body") if v is not None else None)
        return _head(n, n.child_by_field_name("body"))

    def refs(self, n):
        t = n.type
        if t == "call_expression":
            name = _callee(n.child_by_field_name("function"))
            return [("calls", name)] if name else []
        if t == "new_expression":
            name = _callee(n.child_by_field_name("constructor"))
            return [("calls", name)] if name else []
        if t == "import_statement":
            src = _field(n, "source")
            return [("imports", _strip_quotes(src))] if src else []
        if t in ("extends_clause", "implements_clause", "extends_type_clause"):
            return [("inherits", x) for x in map(_callee, n.named_children) if x]
        return []


class DartEx(Extractor):
    body_sibling = "function_body"

    _SIGS = ("function_signature", "getter_signature", "setter_signature", "constructor_signature",
             "factory_constructor_signature", "operator_signature", "redirecting_factory_constructor_signature",
             "constant_constructor_signature")
    _TYPES = {"class_definition": "class", "enum_declaration": "enum", "mixin_declaration": "mixin",
              "extension_declaration": "extension"}

    @staticmethod
    def _name(n: Node) -> str | None:
        name = _field(n, "name")
        if name:
            return name
        c = _first(n, ("identifier", "type_identifier"))
        return _text(c) if c is not None else None

    def _sig_kind(self, sig: Node, parent: Symbol | None) -> str:
        if "constructor" in sig.type:
            return "constructor"
        if sig.type == "getter_signature":
            return "getter"
        if sig.type == "setter_signature":
            return "setter"
        return "method" if parent is not None and parent.kind in ("class", "mixin", "extension", "enum") else "function"

    def definition(self, n, parent):
        t = n.type
        if t in self._TYPES:
            name = self._name(n)
            return (self._TYPES[t], name) if name else None
        if t == "method_signature":
            sig = _first(n, self._SIGS)
            if sig is not None:
                name = self._name(sig)
                return (self._sig_kind(sig, parent), name) if name else None
            return None
        if t in self._SIGS and n.parent is not None and n.parent.type != "method_signature":
            name = self._name(n)
            return (self._sig_kind(n, parent), name) if name else None
        return None

    def signature(self, n):
        if n.type in self._TYPES:
            return _head(n, n.child_by_field_name("body"))
        return _squash(_text(n))

    def refs(self, n):
        t = n.type
        if t == "selector" and _first(n, ("argument_part",)) is not None:
            prev = n.prev_named_sibling
            if prev is None:
                return []
            if prev.type == "identifier":
                return [("calls", _text(prev))]
            if prev.type == "selector":
                acc = _first(prev, ("unconditional_assignable_selector", "conditional_assignable_selector"))
                ident = _first(acc, ("identifier",)) if acc is not None else None
                if ident is not None:
                    return [("calls", _text(ident))]
            return []
        if t in ("new_expression", "const_object_expression"):
            ty = _first(n, ("type_identifier",))
            return [("calls", _text(ty))] if ty is not None else []
        if t == "import_specification":
            uri = _first(n, ("configurable_uri", "uri"))
            if uri is not None:
                return [("imports", _strip_quotes(_text(uri)))]
            return []
        if t in ("superclass", "interfaces", "mixins"):
            return [("inherits", _text(c)) for c in n.named_children if c.type == "type_identifier"]
        return []


EXTRACTORS: dict[str, Extractor] = {
    "python": PythonEx(),
    "go": GoEx(),
    "typescript": TsEx(),
    "tsx": TsEx(),
    "javascript": TsEx(),
    "dart": DartEx(),
}


@cache
def _parser(lang: str) -> Parser:
    return get_parser(lang)


def extract(lang: str, src: bytes) -> FileFacts:
    ex = EXTRACTORS[lang]
    tree = _parser(lang).parse(src)
    facts = FileFacts()
    _walk(tree.root_node, None, ex, facts)
    return facts


def _walk(node: Node, scope: int | None, ex: Extractor, facts: FileFacts) -> None:
    pending: int | None = None  # Dart: oldingi signatura, keyingi body unga tegishli
    for child in node.children:
        child_scope = scope
        if ex.body_sibling and child.type == ex.body_sibling and pending is not None:
            child_scope = pending
            facts.symbols[pending].end_line = child.end_point[0] + 1
        pending = None

        parent = facts.symbols[scope] if scope is not None else None
        d = ex.definition(child, parent)
        if d and d[1]:
            kind, name = d[0], d[1]
            prefix = d[2] if len(d) > 2 else (parent.qualname if parent else None)
            facts.symbols.append(Symbol(
                name=name,
                qualname=f"{prefix}.{name}" if prefix else name,
                kind=kind,
                signature=ex.signature(child),
                start_line=child.start_point[0] + 1,
                end_line=child.end_point[0] + 1,
                parent=scope,
            ))
            child_scope = pending = len(facts.symbols) - 1

        for kind, dst in ex.refs(child):
            if dst:
                facts.refs.append(Ref(child_scope, dst, kind, child.start_point[0] + 1))

        if child.child_count:
            _walk(child, child_scope, ex, facts)
