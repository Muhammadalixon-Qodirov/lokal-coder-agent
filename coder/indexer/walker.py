"""Repo ichidagi indekslanadigan fayllar ro'yxati."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from coder.indexer.langs import lang_for

SKIP_DIRS = {
    ".git", ".agent", "node_modules", ".venv", "venv", "env", "__pycache__", ".dart_tool",
    "build", "dist", ".next", "out", "coverage", "vendor", ".idea", ".vscode", ".gradle",
    "Pods", ".pub-cache", "migrations_backup", ".mypy_cache", ".pytest_cache", "site-packages",
}
SKIP_SUFFIXES = (".g.dart", ".freezed.dart", ".gr.dart", ".mocks.dart", ".min.js", "_pb2.py", ".pb.go")
MAX_BYTES = 400_000


def _git_files(root: Path) -> list[str] | None:
    if not (root / ".git").exists():
        return None
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"],
            capture_output=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return [p for p in r.stdout.decode("utf-8", "replace").split("\0") if p]


def _walk_files(root: Path) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        rel_dir = Path(dirpath).relative_to(root)
        for f in filenames:
            out.append((rel_dir / f).as_posix() if str(rel_dir) != "." else f)
    return out


def list_files(root: Path) -> list[str]:
    """Indekslanadigan fayllar (repo ildiziga nisbatan, `/` bilan)."""
    paths = _git_files(root)
    if paths is None:
        paths = _walk_files(root)
    result = []
    for p in paths:
        if lang_for(p) is None or p.endswith(SKIP_SUFFIXES) or "zz_agent_spec" in p:  # vaqtinchalik spec-test
            continue
        if any(part in SKIP_DIRS for part in p.split("/")[:-1]):
            continue
        try:
            if (root / p).stat().st_size > MAX_BYTES:
                continue
        except OSError:
            continue
        result.append(p)
    return sorted(result)


def looks_minified(src: bytes) -> bool:
    lines = src.count(b"\n") + 1
    return len(src) / lines > 300
