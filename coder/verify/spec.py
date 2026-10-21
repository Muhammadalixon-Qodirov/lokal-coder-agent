"""Spec-test (TDD): model vazifa talablaridan avval test yozadi, kod shu testdan o'tguncha tuzatiladi.

Nega: ko'rinadigan testlar odatda yangi talabni tekshirmaydi — agent "tayyor" deydi, lekin talabning bir
qismi bajarilmagan bo'ladi (masalan, faqat bo'sh joydan iborat title). Spec-test bu bo'shliqni yopadi.

Himoyalar:
  * test o'zgarishdan OLDIN yiqilishi shart — o'tib ketsa, u hech narsani tekshirmaydi → tashlanadi
  * model testni o'zgartira olmaydi (prompt'da "qabul testi" sifatida ko'rsatiladi)
  * test vaqtinchalik: ish tugagach o'chiriladi
"""

from __future__ import annotations

import posixpath
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from coder.context.builder import ContextPack
from coder.llm import LLM

SPEC_PREFIX = "zz_agent_spec"

PROMPT = """{context}

## Task
{task}

Write an automated {kind} that checks whether the task above is implemented correctly.
- Test the behaviour required by the task through the existing public API shown above (classes, functions, HTTP handlers).
- Check EVERY requirement, edge case and example mentioned in the task, each with its own assertion.
- Do not implement the feature and do not change existing code; only write the test.
{lang_rules}
Answer with exactly one code block containing the whole test file.
"""

PY_RULES = """- Use pytest. Test function names start with `test_agent_spec_`.
- Import from the project's packages exactly as the existing code/tests do."""

GO_RULES = """- Use the standard `testing` package. The file is in package `{pkg}`. Test function names start with `TestAgentSpec`.
- Existing helpers from other `_test.go` files of this package may be used but must NOT be redefined; name any new helper with the prefix `agentSpec`."""


@dataclass
class SpecTest:
    path: str
    command: str
    code: str


def _code_block(text: str) -> str | None:
    m = re.search(r"```[\w+-]*\n(.*?)```", text, re.S)
    return m.group(1) if m else None


def _run(repo: Path, cmd: str, timeout: int = 180) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, cwd=repo, shell=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    return r.returncode == 0, (r.stdout + r.stderr).decode("utf-8", "replace")


def make_spec(llm: LLM, repo: Path, task: str, pack: ContextPack, python_cmd: str = "python") -> tuple[SpecTest | None, str]:
    """(spec-test yoki None, izoh)."""
    langs = [f.lang for f in pack.files if f.lang in ("python", "go")]
    if not langs:
        return None, "spec-test faqat python/go uchun"
    lang = langs[0]
    if lang == "python":
        path = f".agent/spec/test_{SPEC_PREFIX}.py"
        command = f"{python_cmd} -m pytest -q -x -p no:cacheprovider {path}"
        kind, rules = "pytest test file", PY_RULES
    else:
        go_file = next(f.path for f in pack.files if f.lang == "go" and not f.path.endswith("_test.go"))
        d = posixpath.dirname(go_file)
        head = (repo / go_file).read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^package\s+(\w+)", head, re.M)
        pkg = m.group(1) if m else "main"
        path = posixpath.join(d, f"{SPEC_PREFIX}_test.go") if d else f"{SPEC_PREFIX}_test.go"
        command = f"go test -count=1 -run TestAgentSpec ./{d or '.'}"
        kind, rules = "Go test file", GO_RULES.format(pkg=pkg)

    prompt = PROMPT.format(context=pack.render(), task=task.strip(), kind=kind, lang_rules=rules)
    c = llm.chat([{"role": "user", "content": prompt}], max_tokens=1500, temperature=0.1)
    code = _code_block(c.text)
    if not code:
        return None, "model test yozmadi"
    if lang == "python":
        if "def test" not in code:
            return None, "testda test funksiyasi yo'q"
        try:
            compile(code, path, "exec")
        except SyntaxError as e:
            return None, f"testda sintaksis xatosi: {e}"
    else:
        # model prefiksni unutsa ham: barcha TestX → TestAgentSpecX (mavjud testlar bilan to'qnashmasin)
        code = re.sub(r"\bfunc Test(?!AgentSpec)(\w*)\(", r"func TestAgentSpec\1(", code)
        if "func TestAgentSpec" not in code:
            return None, "testda Test funksiyasi yo'q"
        code = re.sub(r"^package\s+\w+", f"package {pkg}", code, count=1, flags=re.M)

    spec = SpecTest(path, command, code)
    p = repo / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(code, encoding="utf-8")
    ok, _ = _run(repo, command)
    if ok:  # o'zgarishsiz o'tdi — hech narsani tekshirmaydi
        p.unlink()
        return None, "spec-test o'zgarishsiz ham o'tdi — tashlandi"
    return spec, "spec-test yozildi (hozircha yiqiladi, kutilganidek)"


def remove_spec(repo: Path, spec: SpecTest | None) -> None:
    if spec is not None:
        p = repo / spec.path
        if p.exists():
            p.unlink()
