"""O'zgarishlarni tekshirish: sintaksis (tree-sitter) → lint → types → test.

Birinchi xato topilgan bosqichda to'xtaydi — modelga bitta aniq xato beriladi, uzun ro'yxat emas.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from coder.config import Config
from coder.indexer.langs import _parser, lang_for

MAX_OUTPUT_LINES = 60


@dataclass
class StepResult:
    name: str
    ok: bool
    output: str = ""
    command: str = ""


@dataclass
class VerifyResult:
    steps: list[StepResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps)

    @property
    def failure(self) -> StepResult | None:
        return next((s for s in self.steps if not s.ok), None)

    def summary(self) -> str:
        return " → ".join(f"{s.name}:{'✓' if s.ok else '✗'}" for s in self.steps) or "tekshiruv yo'q"


def syntax_errors(repo: Path, paths: list[str]) -> list[str]:
    """tree-sitter bilan: o'zgargan fayllarda sintaksis xatolari (ERROR / MISSING node'lar)."""
    out = []
    for rel in paths:
        lang = lang_for(rel)
        p = repo / rel
        if lang is None or not p.exists():
            continue
        src = p.read_bytes()
        tree = _parser(lang).parse(src)
        if not tree.root_node.has_error:
            continue
        lines = src.decode("utf-8", "replace").splitlines()
        stack = [tree.root_node]
        found = 0
        while stack and found < 3:
            n = stack.pop()
            if n.type == "ERROR" or n.is_missing:
                ln = n.start_point[0]
                ctx = "\n".join(f"{i + 1:4d} | {lines[i]}" for i in range(max(0, ln - 2), min(len(lines), ln + 3)))
                what = f"yetishmayapti: `{n.type}`" if n.is_missing else "sintaksis xatosi"
                out.append(f"{rel}:{ln + 1}: {what}\n{ctx}")
                found += 1
                continue
            if n.has_error:
                stack.extend(reversed(n.children))
        if not found:
            out.append(f"{rel}: sintaksis xatosi")
    return out


def _tail(text: str, n: int = MAX_OUTPUT_LINES) -> str:
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) <= n:
        return "\n".join(lines)
    return "...\n" + "\n".join(lines[-n:])


def run_command(repo: Path, name: str, cmd: str, files: list[str], timeout: int) -> StepResult:
    if "{files}" in cmd:
        if not files:
            return StepResult(name, True, "o'zgargan fayl yo'q", cmd)
        # cmd.exe ham, sh ham tushunadigan qo'shtirnoq
        cmd = cmd.replace("{files}", " ".join(f'"{f}"' if " " in f else f for f in files))
    try:
        r = subprocess.run(cmd, cwd=repo, shell=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return StepResult(name, False, f"vaqt tugadi ({timeout} s)", cmd)
    output = (r.stdout + b"\n" + r.stderr).decode("utf-8", "replace")
    return StepResult(name, r.returncode == 0, _tail(output), cmd)


def verify(repo: Path, cfg: Config, changed: list[str], extra: list[tuple[str, str]] | None = None) -> VerifyResult:
    res = VerifyResult()
    errs = syntax_errors(repo, changed)
    res.steps.append(StepResult("syntax", not errs, "\n\n".join(errs)))
    if errs:
        return res
    for name, cmd in [*cfg.commands, *(extra or [])]:
        step = run_command(repo, name, cmd, [p for p in changed if (repo / p).exists()], cfg.timeout)
        res.steps.append(step)
        if not step.ok:
            break
    return res
