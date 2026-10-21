"""Git tarixidan context-benchmark vazifalarini yig'ish.

Har bir mos commit → vazifa:
  task       = commit xabari
  parent     = vazifa bajarilishidan oldingi holat
  gold_files = commit o'zgartirgan (oldin mavjud bo'lgan) kod fayllari

Ishlatish:
    .venv/Scripts/python bench/mine.py ../my_card ../hudud1 ...
Natija: bench/tasks/context/<repo>.jsonl
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coder.indexer.langs import lang_for  # noqa: E402
from coder.indexer.walker import SKIP_SUFFIXES  # noqa: E402

OUT = Path(__file__).resolve().parent / "tasks" / "context"
MIN_MSG = 15
MAX_FILES = 4
MAX_LINES = 400


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=True
    ).stdout.decode("utf-8", "replace")


def mine(repo: Path) -> list[dict]:
    tasks = []
    shas = git(repo, "rev-list", "--no-merges", "HEAD").split()
    for sha in shas:
        parents = git(repo, "rev-list", "--parents", "-n", "1", sha).split()[1:]
        if len(parents) != 1:
            continue
        msg = git(repo, "log", "-1", "--format=%B", sha).strip()
        if len(msg) < MIN_MSG:
            continue
        modified, added, lines = [], [], 0
        for row in git(repo, "diff", "--numstat", "--diff-filter=AM", parents[0], sha).splitlines():
            a, d, path = row.split("\t", 2)
            if lang_for(path) is None or path.endswith(SKIP_SUFFIXES) or a == "-":
                continue
            lines += int(a) + int(d)
            modified.append(path)
        for path in git(repo, "diff", "--name-only", "--diff-filter=A", parents[0], sha).splitlines():
            if path in modified:
                modified.remove(path)
                added.append(path)
        if not modified or len(modified) + len(added) > MAX_FILES or lines > MAX_LINES:
            continue
        tasks.append({
            "repo": repo.name,
            "commit": sha,
            "parent": parents[0],
            "task": msg,
            "gold_files": sorted(modified),
            "added_files": sorted(added),
            "diff_lines": lines,
        })
    return tasks


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for arg in sys.argv[1:]:
        repo = Path(arg).resolve()
        tasks = mine(repo)
        out = OUT / f"{repo.name}.jsonl"
        out.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks), encoding="utf-8")
        print(f"{repo.name}: {len(tasks)} vazifa → {out}")


if __name__ == "__main__":
    main()
