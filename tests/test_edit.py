from pathlib import Path

from coder.edit.apply import apply_blocks, replace_in, rollback, unified_diff
from coder.edit.blocks import parse_blocks

REPLY = '''Mana o'zgarish:

app/models.py
```python
<<<<<<< SEARCH
class Card(models.Model):
    title = models.CharField(max_length=100)
=======
class Card(models.Model):
    title = models.CharField(max_length=100)
    is_archived = models.BooleanField(default=False)
>>>>>>> REPLACE
```

### `app/new.py`
```python
<<<<<<< SEARCH
=======
def hello():
    return 1
>>>>>>> REPLACE
```
'''


def test_parse():
    blocks, errors = parse_blocks(REPLY)
    assert not errors
    assert [b.path for b in blocks] == ["app/models.py", "app/new.py"]
    assert "is_archived" in blocks[0].replace
    assert blocks[1].is_create


def test_parse_missing_tail():
    _, errors = parse_blocks("a.py\n<<<<<<< SEARCH\nx\n=======\ny\n")
    assert errors


def test_replace_exact_and_whitespace():
    src = "def f():\n    return 1   \n"
    new, _ = replace_in(src, "def f():\n    return 1", "def f():\n    return 2")
    assert new == "def f():\n    return 2\n"


def test_replace_indent_shift():
    src = "class A:\n    def f(self):\n        return 1\n"
    # model chekinishsiz yozdi
    new, _ = replace_in(src, "def f(self):\n    return 1", "def f(self):\n    return 2")
    assert new == "class A:\n    def f(self):\n        return 2\n"


def test_replace_ambiguous_and_missing():
    src = "x = 1\ny = 2\nx = 1\n"
    new, err = replace_in(src, "x = 1", "x = 3")
    assert new is None and "2 marta" in err
    new, err = replace_in(src, "z = 9\nw = 8", "q")
    assert new is None and "topilmadi" in err


def test_replace_rejects_elision():
    new, err = replace_in("a\nb\n", "a\n⋮...\nb", "c")
    assert new is None and "⋮" in err


def test_apply_and_rollback(tmp_path: Path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app/models.py").write_text(
        "from django.db import models\n\nclass Card(models.Model):\n    title = models.CharField(max_length=100)\n"
    )
    blocks, _ = parse_blocks(REPLY)
    out = apply_blocks(tmp_path, blocks)
    assert not out.failed
    assert "is_archived" in (tmp_path / "app/models.py").read_text()
    assert (tmp_path / "app/new.py").exists()
    diff = unified_diff(tmp_path, out.originals)
    assert "+    is_archived" in diff and "+++ b/app/new.py" in diff
    rollback(tmp_path, out.originals)
    assert "is_archived" not in (tmp_path / "app/models.py").read_text()
    assert not (tmp_path / "app/new.py").exists()


def test_delete_guard(tmp_path: Path):
    (tmp_path / "s.py").write_text("class S:\n    def pay(self):\n        return 1\n")
    reply = "s.py\n<<<<<<< SEARCH\n    def pay(self):\n        return 1\n=======\n    def cancel(self):\n        return 2\n>>>>>>> REPLACE\n"
    blocks, _ = parse_blocks(reply)
    out = apply_blocks(tmp_path, blocks, allow_delete=False)
    assert out.failed and "pay" in out.failed[0][1]
    assert "def pay" in (tmp_path / "s.py").read_text()


def test_apply_short_path(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg/views.py").write_text("a = 1\n")
    blocks, _ = parse_blocks("views.py\n<<<<<<< SEARCH\na = 1\n=======\na = 2\n>>>>>>> REPLACE\n")
    out = apply_blocks(tmp_path, blocks, known_files=["pkg/views.py"])
    assert not out.failed and (tmp_path / "pkg/views.py").read_text() == "a = 2\n"
