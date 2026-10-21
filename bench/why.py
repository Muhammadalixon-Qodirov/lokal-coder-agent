"""Bitta benchmark vazifasini tahlil qilish: gold fayllar reytingda nechanchi o'rinda va nega.

    .venv/Scripts/python bench/why.py <repo> <commit-prefix> [--full]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench.recall import TASKS, clone_for, git  # noqa: E402
from coder.context import build_context  # noqa: E402
from coder.indexer import index_repo, open_index  # noqa: E402


def main() -> None:
    repo, prefix = sys.argv[1], sys.argv[2]
    full = "--full" in sys.argv
    t = next(
        json.loads(l)
        for l in (TASKS / f"{repo}.jsonl").read_text(encoding="utf-8").splitlines()
        if l.startswith("{") and json.loads(l)["commit"].startswith(prefix)
    )
    wt = clone_for(repo)
    git(wt, "checkout", "-q", "--force", "--detach", t["parent"])
    git(wt, "clean", "-qfdx", "-e", ".agent")
    index_repo(wt)
    con = open_index(wt)
    text = t["task"] if full else t["task"].splitlines()[0]
    pack = build_context(con, wt, text)
    r = pack.ranking
    paths = {row["id"]: row["path"] for row in con.execute("SELECT id, path FROM files")}
    order = sorted(r.files.items(), key=lambda kv: -kv[1])
    print("VAZIFA:", text)
    print("GOLD:", t["gold_files"])
    print("\nTOP 15:")
    for i, (fid, s) in enumerate(order[:15], 1):
        mark = "★" if paths[fid] in t["gold_files"] else " "
        print(f"{mark}{i:3d}. {s:6.2f} {paths[fid]}  [{', '.join(r.reasons.get(fid, [])[:4])}]")
    print("\nGOLD o'rinlari:")
    pos = {paths[fid]: i for i, (fid, _) in enumerate(order, 1)}
    for g in t["gold_files"]:
        fid = next((k for k, v in paths.items() if v == g), None)
        print(f"  {g}: o'rin={pos.get(g, '-')}, ball={r.files.get(fid, 0):.2f}, sabab={r.reasons.get(fid, [])[:4]}")
    print("\nCONTEXT:", pack.paths)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
