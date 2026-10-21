"""recall@context: kerakli fayllar modelga yuboriladigan context'ga tushdimi?

Har vazifa uchun repo `parent` commit holatiga keltiriladi (foydalanuvchi repo'siga
tegmaslik uchun alohida lokal clone'da), incremental indekslanadi va context yig'iladi.

Ishlatish:
    .venv/Scripts/python bench/recall.py [--label baseline] [repo_nomi ...]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coder.context import build_context  # noqa: E402
from coder.context.expand import expand  # noqa: E402
from coder.context.rank import rank  # noqa: E402
from coder.context.select import apply_selection, select_files  # noqa: E402
from coder.indexer import index_repo, open_index  # noqa: E402
from coder.llm import LLM  # noqa: E402

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks" / "context"
WORK = Path(os.environ.get("CODER_BENCH_WORK", r"D:\llm\bench_wt"))
REPOS_ROOT = HERE.parent.parent  # "New folder (5)"
REPO_PATHS = {
    "my_card": REPOS_ROOT / "my_card",
    "hudud1": REPOS_ROOT / "hudud1",
    "hackaton_finder": REPOS_ROOT / "hackaton_finder",
    "cyber": REPOS_ROOT / "cyber",
    "ilm_invest": REPOS_ROOT / "ilm_invst" / "ilm-backend" / "ilm_invest",
}


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)


def clone_for(name: str) -> Path:
    dst = WORK / name
    if not (dst / ".git").exists():
        WORK.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--no-checkout", str(REPO_PATHS[name]), str(dst)], check=True)
    return dst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repos", nargs="*")
    ap.add_argument("--label", default="run")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--subject", action="store_true", help="faqat commit sarlavhasi (qiyinroq, realroq)")
    ap.add_argument("--expand", action="store_true", help="LLM bilan qidiruvni kengaytirish (keshlanadi)")
    ap.add_argument("--select", action="store_true", help="LLM nomzod fayllarni qayta saralaydi (keshlanadi)")
    args = ap.parse_args()

    llm = None
    cache_path = HERE / "results" / "expand-cache.json"
    cache: dict = {}
    if args.expand or args.select:
        llm = LLM()
        if not llm.health():
            sys.exit("llama-server ishlamayapti")
        if cache_path.exists():
            cache = json.loads(cache_path.read_text(encoding="utf-8"))

    files = sorted(TASKS.glob("*.jsonl"))
    if args.repos:
        files = [f for f in files if f.stem in args.repos]

    results = []
    t0 = time.perf_counter()
    for tf in files:
        tasks = [json.loads(l) for l in tf.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not tasks:
            continue
        wt = clone_for(tf.stem)
        for t in tasks:
            git(wt, "checkout", "-q", "--force", "--detach", t["parent"])
            git(wt, "clean", "-qfdx", "-e", ".agent")
            index_repo(wt)
            con = open_index(wt)
            text = "\n".join(l for l in t["task"].splitlines() if not l.startswith("Co-Authored-By"))
            if args.subject:
                text = text.splitlines()[0]
            kw = ids = None
            if args.expand:
                key = f"{t['commit']}:{int(args.subject)}"
                if key not in cache:
                    e = expand(llm, con, text)
                    cache[key] = {"keywords": e.keywords, "identifiers": e.identifiers}
                    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
                kw, ids = cache[key]["keywords"], cache[key]["identifiers"]
            ranking = rank(con, text, kw, ids)
            if args.select:
                key = f"sel:{t['commit']}:{int(args.subject)}:{int(args.expand)}"
                if key not in cache:
                    cache[key] = select_files(llm, con, text, ranking)
                    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
                apply_selection(con, ranking, cache[key])
            pack = build_context(con, wt, text, ranking=ranking)
            con.close()

            gold = set(t["gold_files"])
            in_code = gold & set(pack.paths)
            map_paths = {line[:-1] for line in pack.repomap.splitlines() if line and not line.startswith(" ")}
            in_map = (gold - in_code) & map_paths
            ranked = [p for p in pack.paths]
            res = {
                "repo": tf.stem,
                "commit": t["commit"][:8],
                "gold": len(gold),
                "recall_code": len(in_code) / len(gold),
                "recall_any": (len(in_code) + len(in_map)) / len(gold),
                "top1": bool(ranked) and ranked[0] in gold,
                "tokens": pack.tokens,
                "task": t["task"].splitlines()[0][:70],
                "missed": sorted(gold - in_code - in_map),
            }
            results.append(res)
            if args.verbose:
                mark = "✓" if res["recall_code"] == 1 else ("~" if res["recall_any"] > 0 else "✗")
                print(f"{mark} {res['repo']:16} {res['commit']} rc={res['recall_code']:.2f} {res['task']}")
                for m in res["missed"]:
                    print(f"      o'tkazib yuborildi: {m}")

    if not results:
        sys.exit("vazifa yo'q — avval bench/mine.py")

    def summary(rows: list[dict]) -> str:
        n = len(rows)
        rc = sum(r["recall_code"] for r in rows) / n
        ra = sum(r["recall_any"] for r in rows) / n
        full = sum(r["recall_code"] == 1 for r in rows) / n
        top1 = sum(r["top1"] for r in rows) / n
        tok = sum(r["tokens"] for r in rows) / n
        return f"n={n:3d}  recall@code={rc:.1%}  to'liq={full:.1%}  recall@code+map={ra:.1%}  top1={top1:.1%}  ~{tok:.0f} tok"

    print()
    for repo in sorted({r["repo"] for r in results}):
        print(f"{repo:16} {summary([r for r in results if r['repo'] == repo])}")
    print(f"{'JAMI':16} {summary(results)}   ({time.perf_counter() - t0:.0f} s)")

    out = HERE / "results" / f"recall-{args.label}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
