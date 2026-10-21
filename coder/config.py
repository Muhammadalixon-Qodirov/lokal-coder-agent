"""Loyiha konfiguratsiyasi: `<repo>/.agent.toml`.

    [verify]
    lint  = "ruff check {files}"     # {files} — o'zgargan fayllar (shu tilda)
    types = ""
    test  = "pytest -x -q"
    timeout = 300

    [rules]
    text = \"\"\"
    - loyiha qoidalari, har promptga qo'shiladi
    \"\"\"
"""

from __future__ import annotations

import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_NAME = ".agent.toml"


@dataclass
class Config:
    lint: str = ""
    types: str = ""
    test: str = ""
    timeout: int = 300
    rules: str = ""
    languages: list[str] = field(default_factory=list)

    def summary_line(self) -> str:
        parts = ["syntax"] + [f"{n}=`{c}`" for n, c in self.commands]
        return ", ".join(parts)

    @property
    def commands(self) -> list[tuple[str, str]]:
        return [(name, cmd) for name, cmd in (("lint", self.lint), ("types", self.types), ("test", self.test)) if cmd]


def load_config(repo: Path) -> Config:
    p = repo / CONFIG_NAME
    if not p.exists():
        return detect_config(repo)
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    v = data.get("verify", {})
    return Config(
        lint=v.get("lint", ""),
        types=v.get("types", ""),
        test=v.get("test", ""),
        timeout=int(v.get("timeout", 300)),
        rules=data.get("rules", {}).get("text", "").strip(),
        languages=data.get("project", {}).get("languages", []),
    )


def detect_config(repo: Path) -> Config:
    """Konfiguratsiya yo'q bo'lsa — ildizdagi fayllarga qarab taxminiy buyruqlar."""
    c = Config()
    has = lambda name: (repo / name).exists()  # noqa: E731
    if has("go.mod"):
        c.languages.append("go")
        c.types = "go build ./..."
        c.lint = "go vet ./..."
        c.test = "go test ./..."
    if has("pyproject.toml") or has("setup.py") or has("requirements.txt") or has("manage.py"):
        c.languages.append("python")
        if shutil.which("ruff"):
            c.lint = c.lint or "ruff check --select E9,F63,F7,F82 {files}"
        if has("manage.py"):
            c.test = c.test or "python manage.py test"
        elif has("tests") or has("pytest.ini") or has("conftest.py"):
            c.test = c.test or "pytest -x -q"
    if has("tsconfig.json"):
        c.languages.append("typescript")
        c.types = c.types or "npx tsc --noEmit"
    if has("pubspec.yaml"):
        c.languages.append("dart")
        c.lint = c.lint or "dart analyze {files}"
    return c


def write_config(repo: Path, c: Config) -> Path:
    p = repo / CONFIG_NAME
    p.write_text(
        "[project]\n"
        f"languages = {c.languages!r}\n\n"
        "[verify]\n"
        "# {files} — o'zgargan fayllar ro'yxati bilan almashtiriladi\n"
        f'lint  = "{c.lint}"\n'
        f'types = "{c.types}"\n'
        f'test  = "{c.test}"\n'
        f"timeout = {c.timeout}\n\n"
        "[rules]\n"
        "# loyiha qoidalari — har promptga qo'shiladi\n"
        'text = """\n"""\n',
        encoding="utf-8",
    )
    return p
