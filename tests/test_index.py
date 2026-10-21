from pathlib import Path

from coder.indexer import index_repo, open_index
from coder.search import basic


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_index_incremental_and_queries(tmp_path: Path):
    _write(tmp_path, "app/services.py", "def login_user(email):\n    return find_user(email)\n\ndef find_user(e):\n    return None\n")
    _write(tmp_path, "app/views.py", "from app.services import login_user\n\ndef login_view(req):\n    return login_user(req.email)\n")
    _write(tmp_path, "node_modules/x/index.js", "function junk() {}\n")

    s = index_repo(tmp_path)
    assert (s.files, s.parsed) == (2, 2)

    con = open_index(tmp_path)
    assert [h.qualname for h in basic.find_symbol(con, "login_user")] == ["login_user"]
    callers = basic.callers(con, "login_user")
    assert [(c[0].qualname, c[3]) for c in callers] == [("login_view", "calls:unique")]
    same = basic.callees(con, "login_user")
    assert same[0][0] == "find_user" and same[0][1] == "calls:same_file"
    assert basic.search_text(con, "user login")[0].qualname in {"login_user", "login_view"}
    con.close()

    # o'zgarishsiz qayta indeks
    s = index_repo(tmp_path)
    assert (s.parsed, s.unchanged) == (0, 2)

    # bitta fayl o'zgardi, bittasi o'chdi
    _write(tmp_path, "app/services.py", "def login_user(email, pw):\n    return None\n")
    (tmp_path / "app/views.py").unlink()
    s = index_repo(tmp_path)
    assert (s.parsed, s.removed) == (1, 1)
    con = open_index(tmp_path)
    assert basic.callers(con, "login_user") == []
    assert basic.find_symbol(con, "login_view") == []
