"""Edit benchmark: agent vazifani bajaradi → yashirin testlar bilan tekshiriladi.

    .venv/Scripts/python bench/edit_bench.py [--label v1] [--max-fix 3] [--no-expand] [--no-select] [id ...]

Har vazifa fixture'ning toza nusxasida (D:\\llm\\edit_wt\\<id>) bajariladi.
Agent o'z tekshiruvida faqat ko'rinadigan testlarni ishlatadi; yashirin test agent tugagach qo'shiladi.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coder.config import Config  # noqa: E402
from coder.llm import LLM  # noqa: E402
from coder.pipeline import Pipeline  # noqa: E402

HERE = Path(__file__).resolve().parent / "edit"
WORK = Path(os.environ.get("CODER_EDIT_WORK", r"D:\llm\edit_wt"))
PY = f'"{sys.executable}" -m pytest'

FIXTURE_CONFIG = {
    "shop": Config(lint="ruff check --select E9,F63,F7,F82 {files}", test=f"{PY} -q tests/test_services.py", timeout=120),
    "notes": Config(types="go build ./...", lint="go vet ./...", test="go test ./...", timeout=180),
}


def prepare(task: dict) -> Path:
    dst = WORK / task["id"]
    if dst.exists():
        def force(func, path, _exc):  # Windows: git obyektlari read-only
            os.chmod(path, stat.S_IWRITE)
            func(path)

        shutil.rmtree(dst, onerror=force)
    shutil.copytree(HERE / "fixtures" / task["fixture"], dst, ignore=shutil.ignore_patterns(".agent", "__pycache__", ".pytest_cache"))
    for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.name=bench", "-c", "user.email=b@b", "commit", "-qm", "init"]):
        subprocess.run(["git", "-C", str(dst), *cmd], check=True, capture_output=True)
    return dst


def hidden_check(dst: Path, task: dict) -> tuple[bool, str]:
    (dst / task["hidden_file"]).write_text(task["hidden"], encoding="utf-8")
    cmd = task["test"].replace("pytest", PY, 1) if task["test"].startswith("pytest") else task["test"]
    r = subprocess.run(cmd, cwd=dst, shell=True, capture_output=True, timeout=300)
    out = (r.stdout + r.stderr).decode("utf-8", "replace")
    return r.returncode == 0, out[-1500:]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--label", default="run")
    ap.add_argument("--max-fix", type=int, default=3)
    ap.add_argument("--no-expand", action="store_true")
    ap.add_argument("--no-select", action="store_true")
    ap.add_argument("--spec", action="store_true", help="TDD: avval spec-test yozdirish")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    llm = LLM()
    if not llm.health():
        sys.exit("llama-server ishlamayapti")
    tasks = yaml.safe_load((HERE / "tasks.yaml").read_text(encoding="utf-8"))
    if args.ids:
        tasks = [t for t in tasks if t["id"] in args.ids]

    rows = []
    t0 = time.perf_counter()
    for t in tasks:
        dst = prepare(t)
        pipe = Pipeline(dst, llm, cfg=FIXTURE_CONFIG[t["fixture"]], max_fix=args.max_fix,
                        use_expand=not args.no_expand, use_select=not args.no_select,
                        use_spec=args.spec, spec_python=f'"{sys.executable}"',
                        on_event=(lambda s: print(f"    › {s}")) if args.verbose else None)
        res = pipe.run(t["task"])
        passed, out = hidden_check(dst, t)
        row = {
            "id": t["id"],
            "hidden_pass": passed,
            "agent_ok": res.ok,
            "attempts": len(res.attempts),
            "seconds": round(res.seconds, 1),
            "changed": res.changed,
            "completion_tokens": sum(a.completion_tokens for a in res.attempts),
            "problems": [p for a in res.attempts for p in a.problems],
            "spec": res.spec_note,
            "verify": [a.verify for a in res.attempts],
            "hidden_output": "" if passed else out,
            "log": str(res.log_path),
        }
        rows.append(row)
        mark = "✓" if passed else "✗"
        print(f"{mark} {t['id']:24} agent_ok={res.ok!s:5} urinish={row['attempts']} {row['seconds']:5.0f}s  {', '.join(res.changed)}")
        if args.verbose and not passed:
            print("    " + out.strip().replace("\n", "\n    ")[-800:])

    n = len(rows)
    passed = sum(r["hidden_pass"] for r in rows)
    agent_ok = sum(r["agent_ok"] for r in rows)
    false_ok = sum(r["agent_ok"] and not r["hidden_pass"] for r in rows)
    print(f"\n{args.label}: yashirin testlar {passed}/{n} ({passed / n:.0%}), agent 'tayyor' dedi {agent_ok}/{n}, "
          f"noto'g'ri 'tayyor' {false_ok}, o'rtacha {sum(r['seconds'] for r in rows) / n:.0f} s/vazifa, "
          f"jami {time.perf_counter() - t0:.0f} s")
    out = Path(__file__).resolve().parent / "results" / f"edit-{args.label}.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
