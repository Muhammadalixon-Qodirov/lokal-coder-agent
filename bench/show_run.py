"""Edit benchmark natijasidagi bitta vazifaning urinishlarini ko'rsatish.

    .venv/Scripts/python bench/show_run.py <label> <id> [--full]
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
label, tid = sys.argv[1], sys.argv[2]
full = "--full" in sys.argv
rows = json.loads((Path(__file__).parent / "results" / f"edit-{label}.json").read_text(encoding="utf-8"))
row = next(r for r in rows if r["id"] == tid)
log = json.loads(Path(row["log"]).read_text(encoding="utf-8"))
print("VAZIFA:", log["task"])
print("CONTEXT:", log["context_files"], "| tanlangan:", log["selected"])
for a in log["attempts"]:
    print(f"\n=== {a['n']}-urinish | verify={a['verify']} | muammolar={a['problems']}")
    print(a["reply"] if full else a["reply"][:1200])
print("\n=== YASHIRIN TEST:\n", row["hidden_output"][-1200:])
