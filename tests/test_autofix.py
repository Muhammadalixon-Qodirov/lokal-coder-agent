import shutil
from pathlib import Path

import pytest

from coder.edit.autofix import _go_fix, _py_add_imports, autofix


def test_go_adds_missing_and_removes_unused():
    src = 'package x\n\nimport (\n\t"fmt"\n\t"net/http"\n)\n\nfunc f(w http.ResponseWriter) {\n\t_ = strings.TrimSpace("")\n}\n'
    out = _go_fix(src)
    assert '"strings"' in out and '"net/http"' in out and '"fmt"' not in out


def test_go_local_variable_not_import():
    src = 'package x\n\nfunc f() {\n\ttime := 3\n\t_ = time\n}\n'
    assert _go_fix(src) == src


def test_py_merge_from_import():
    src = "from datetime import datetime\n\nx = datetime.now(timezone.utc)\n"
    out = _py_add_imports(src, {"timezone"})
    assert out.startswith("from datetime import datetime, timezone\n")


@pytest.mark.skipif(not shutil.which("ruff"), reason="ruff yo'q")
def test_autofix_python(tmp_path: Path):
    (tmp_path / "m.py").write_text("from dataclasses import dataclass\n\n@dataclass\nclass A:\n    x: int = field(default=1)\n    t: datetime = None\n")
    notes = autofix(tmp_path, ["m.py"])
    text = (tmp_path / "m.py").read_text()
    assert "from dataclasses import dataclass, field" in text and "from datetime import datetime" in text
    assert notes
