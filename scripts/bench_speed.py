"""Ishlab turgan llama-server tezligini o'lchaydi.

Ishlatish:
    .venv/Scripts/python scripts/bench_speed.py [--label draft]

Draft bilan va draftsiz solishtirish uchun serverni ikki marta
(start_llm.ps1 va start_llm.ps1 -NoDraft) ishga tushirib, ikkalasida ham yurgiziladi.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coder.llm import LLM  # noqa: E402

PROMPTS = [
    "Write a Python function `merge_intervals(intervals)` that merges overlapping intervals. Include type hints and a docstring.",
    "Write a Django REST Framework ModelSerializer and ModelViewSet for a model `Card(owner FK User, title str, is_archived bool, created_at datetime)`. Filter by is_archived query param.",
    "Write a Go HTTP handler using net/http that accepts JSON {\"email\",\"password\"}, validates both fields, and returns 400 with a JSON error on failure.",
    "Refactor this to be idiomatic and fix the bug:\n```python\ndef avg(xs):\n    s = 0\n    for i in range(len(xs)+1):\n        s += xs[i]\n    return s / len(xs)\n```",
    "Write a Flutter StatelessWidget `ProfileCard` showing avatar, name and email, with a Material 3 Card and an edit IconButton callback.",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="run")
    ap.add_argument("--max-tokens", type=int, default=512)
    args = ap.parse_args()

    llm = LLM()
    if not llm.health():
        sys.exit("llama-server ishlamayapti (http://127.0.0.1:8080). Avval scripts/start_llm.ps1 ni ishga tushiring.")

    # isitish
    llm.chat([{"role": "user", "content": "hi"}], max_tokens=8)

    rows = []
    for i, p in enumerate(PROMPTS, 1):
        t0 = time.perf_counter()
        c = llm.chat([{"role": "user", "content": p}], max_tokens=args.max_tokens, temperature=0.0)
        dt = time.perf_counter() - t0
        acc = f"{c.draft_accepted:.0%}" if c.draft_accepted is not None else "-"
        print(f"[{i}] {c.completion_tokens:4d} tok  {c.tokens_per_sec:6.1f} tok/s  draft={acc:>4}  {dt:5.1f}s")
        rows.append({"tokens": c.completion_tokens, "tps": c.tokens_per_sec, "draft": c.draft_accepted, "sec": dt})

    tps = statistics.mean(r["tps"] for r in rows)
    print(f"\n{args.label}: o'rtacha {tps:.1f} tok/s")

    out = Path(__file__).resolve().parent.parent / "bench" / "results" / f"speed-{args.label}.json"
    out.write_text(json.dumps({"label": args.label, "mean_tps": tps, "rows": rows}, indent=2))
    print(f"saqlandi: {out}")


if __name__ == "__main__":
    main()
