from pathlib import Path

from coder.edit.apply import apply_fenced
from coder.edit.blocks import parse_fenced
from coder.edit.symbolic import apply_definitions

PY = '''from dataclasses import dataclass


@dataclass
class Order:
    id: int
    status: str = "new"

    @property
    def total(self) -> int:
        return 0

    def to_dict(self) -> dict:
        return {"id": self.id}


class Service:
    def create(self, name):
        return name

    def pay(self, oid):
        return oid
'''


def test_replace_method_given_without_class():
    snippet = "def pay(self, oid):\n    if oid < 0:\n        raise ValueError\n    return oid\n"
    new, err = apply_definitions(PY, snippet, "python")
    assert new is not None, err
    assert "        if oid < 0:" in new  # klass ichidagi chekinish bilan
    assert new.count("def pay") == 1 and "def create" in new


def test_partial_class_merges_members_and_fields():
    snippet = '''from datetime import datetime, timezone

@dataclass
class Order:
    created_at: datetime = None

    def to_dict(self) -> dict:
        return {"id": self.id, "created_at": self.created_at}
'''
    new, err = apply_definitions(PY, snippet, "python")
    assert new is not None, err
    assert "from datetime import datetime, timezone" in new
    assert "    created_at: datetime = None" in new
    assert new.index("created_at: datetime") < new.index("def total")  # maydon metodlardan oldin
    assert '"created_at": self.created_at' in new
    assert "def total" in new  # qisman klass boshqa a'zolarni o'chirmadi


def test_new_method_into_single_class_and_placeholder():
    src = "class Repo:\n    def all(self):\n        return []\n"
    snippet = "# ... existing code ...\ndef search(self, q):\n    return [x for x in self.all() if q in x]\n"
    new, err = apply_definitions(src, snippet, "python")
    assert new is not None, err
    assert "    def search(self, q):" in new and "# ..." not in new


def test_go_method_and_import():
    src = '''package notes

import (
\t"net/http"
)

type Server struct{}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
\tw.WriteHeader(200)
}
'''
    snippet = '''import "strings"

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
\t_ = strings.TrimSpace("")
\tw.WriteHeader(201)
}

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
\tw.WriteHeader(204)
}
'''
    new, err = apply_definitions(src, snippet, "go")
    assert new is not None, err
    assert '\t"strings"' in new and new.count("handleList(") == 1
    assert "WriteHeader(201)" in new and "func (s *Server) handleDelete" in new


def test_ts_function():
    src = "export function a(): number {\n  return 1;\n}\n\nexport const b = () => 2;\n"
    new, err = apply_definitions(src, "export const b = () => 3;\n", "typescript")
    assert new is not None, err
    assert "export const b = () => 3;" in new and "return 1" in new


def test_loose_statement_rejected():
    new, err = apply_definitions(PY, "x = compute()\n", "python")
    assert new is None and "SEARCH/REPLACE" in err


def test_parse_fenced_and_apply(tmp_path: Path):
    (tmp_path / "shop").mkdir()
    (tmp_path / "shop/money.py").write_text('def format_som(a):\n    return f"{a} so\'m"\n')
    reply = '''I will change it.

shop/money.py
```python
def format_som(a):
    return f"{a:,} so'm".replace(",", " ")
```

shop/other.py
```python
# ...
```
'''
    items = parse_fenced(reply)
    assert [p for p, _ in items] == ["shop/money.py", "shop/other.py"]
    out = apply_fenced(tmp_path, items, ["shop/money.py"])
    assert not out.failed and list(out.originals) == ["shop/money.py"]
    assert 'replace(",", " ")' in (tmp_path / "shop/money.py").read_text()
    assert not (tmp_path / "shop/other.py").exists()
