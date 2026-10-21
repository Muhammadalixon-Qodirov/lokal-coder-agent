"""`agent` buyrug'i."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from coder.context import build_context, est_tokens
from coder.indexer import index_repo, open_index
from coder.search import basic

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Lokal coder agent")
console = Console()

RepoOpt = typer.Option(Path("."), "--repo", "-r", help="Repo papkasi")


def _need_index(repo: Path):
    if not (repo / ".agent" / "index.db").exists():
        console.print(f"[yellow]Indeks yo'q, avval: agent index {repo}[/]")
        raise typer.Exit(1)
    return open_index(repo)


@app.command()
def run(
    task: str,
    repo: Path = RepoOpt,
    yes: bool = typer.Option(False, "--yes", "-y", help="Tasdiqlashsiz qabul qilish"),
    commit: bool = typer.Option(False, "--commit", help="Qabul qilingach git commit qilish"),
    max_fix: int = typer.Option(3, "--max-fix", help="Tuzatish urinishlari soni"),
    no_expand: bool = typer.Option(False, "--no-expand", help="Kalit so'zlarni kengaytirmaslik"),
    no_select: bool = typer.Option(False, "--no-select", help="LLM fayl tanlashsiz"),
    spec: bool = typer.Option(False, "--spec", help="TDD: avval talablardan test yozdirish (python/go)"),
):
    """Vazifani bajarish: context → o'zgarish → tekshiruv → tuzatish → diff."""
    import subprocess

    from rich.syntax import Syntax

    from coder.edit.apply import rollback
    from coder.llm import LLM
    from coder.pipeline import Pipeline

    llm = LLM()
    if not llm.health():
        console.print("[red]llama-server ishlamayapti.[/] Avval: .\\scripts\\start_llm.ps1")
        raise typer.Exit(1)
    pipe = Pipeline(repo, llm, max_fix=max_fix, use_expand=not no_expand, use_select=not no_select, use_spec=spec,
                    on_event=lambda s: console.print(f"[dim]›[/] {s}"))
    console.print(f"[dim]tekshiruv: {pipe.cfg.summary_line()}[/]")
    res = pipe.run(task)

    if res.diff:
        console.print(Syntax(res.diff, "diff", theme="ansi_dark", word_wrap=True))
    status = "[green]✓ tekshiruvdan o'tdi[/]" if res.ok else "[red]✗ tekshiruvdan o'tmadi[/]"
    console.print(f"{status} — {len(res.attempts)} urinish, {res.seconds:.0f} s, log: {res.log_path}")
    if not res.ok and res.verify and res.verify.failure:
        console.print(res.verify.failure.output[-1500:], markup=False, highlight=False)

    if not res.changed:
        raise typer.Exit(0 if res.ok else 1)
    if yes and res.ok:
        keep = True
    else:
        prompt = "O'zgarishlar qabul qilinsinmi?" if res.ok else "Tekshiruvdan o'tmagan o'zgarishlar ham qoldirilsinmi?"
        keep = typer.confirm(prompt, default=res.ok)
    if not keep:
        rollback(pipe.repo, res.originals)
        console.print("[yellow]bekor qilindi — fayllar asl holatiga qaytarildi[/]")
        raise typer.Exit(1)
    if commit:
        subprocess.run(["git", "-C", str(pipe.repo), "add", "--", *res.changed], check=True)
        subprocess.run(["git", "-C", str(pipe.repo), "commit", "-q", "-m", task], check=True)
        console.print("[green]commit qilindi[/]")


@app.command()
def init(repo: Path = typer.Argument(Path("."), help="Repo papkasi")):
    """`.agent.toml` yaratish (tekshiruv buyruqlari avtomatik aniqlanadi)."""
    from coder.config import CONFIG_NAME, detect_config, write_config

    if (repo / CONFIG_NAME).exists():
        console.print(f"[yellow]{CONFIG_NAME} allaqachon bor[/]")
        raise typer.Exit(1)
    p = write_config(repo, detect_config(repo))
    console.print(f"[green]✓[/] {p}\n" + p.read_text(encoding="utf-8"), markup=False)


@app.command()
def index(path: Path = typer.Argument(Path("."), help="Repo papkasi")):
    """Repo'ni indekslash (faqat o'zgargan fayllar qayta o'qiladi)."""
    with Progress(console=console, transient=True) as p:
        task = p.add_task("indekslanmoqda", total=None)

        def cb(done, total, rel):
            p.update(task, completed=done, total=total, description=rel[-60:])

        s = index_repo(path, progress=cb)
    console.print(
        f"[green]✓[/] {s.files} fayl: {s.parsed} parse, {s.unchanged} o'zgarmagan, "
        f"{s.removed} o'chirilgan, {s.skipped} tashlab ketilgan\n"
        f"  {s.symbols} symbol, {s.edges} bog'lanish — {s.seconds:.1f} s"
    )


@app.command()
def find(query: str, repo: Path = RepoOpt, limit: int = typer.Option(15, "--limit", "-n")):
    """Symbol yoki matn bo'yicha qidirish."""
    con = _need_index(repo)
    hits = basic.find_symbol(con, query) or basic.search_text(con, query, limit)
    t = Table(show_header=True, header_style="bold")
    for col in ("joy", "tur", "nom", "signatura"):
        t.add_column(col, overflow="fold")
    for h in hits[:limit]:
        t.add_row(f"{h.path}:{h.line}", h.kind, h.qualname, h.signature[:90])
    console.print(t)


@app.command()
def refs(name: str, repo: Path = RepoOpt):
    """`name` ni kim chaqiradi."""
    con = _need_index(repo)
    t = Table(show_header=True, header_style="bold")
    for col in ("joy", "chaqiruvchi", "ishonch"):
        t.add_column(col, overflow="fold")
    for src, path, line, conf in basic.callers(con, name):
        t.add_row(f"{path}:{line}", src.qualname if src else "<modul>", conf)
    console.print(t)


@app.command()
def calls(qualname: str, repo: Path = RepoOpt):
    """`qualname` ichidan nimalar chaqiriladi."""
    con = _need_index(repo)
    t = Table(show_header=True, header_style="bold")
    for col in ("nom", "ishonch", "qayerda"):
        t.add_column(col, overflow="fold")
    for name, conf, dst in basic.callees(con, qualname):
        t.add_row(name, conf, f"{dst.path}:{dst.line}" if dst else "")
    console.print(t)


@app.command()
def context(
    task: str,
    repo: Path = RepoOpt,
    show: bool = typer.Option(False, "--show", "-s", help="To'liq context matnini chiqarish"),
):
    """Vazifa uchun modelga yuboriladigan context'ni ko'rsatish."""
    con = _need_index(repo)
    pack = build_context(con, repo, task)
    t = Table(show_header=True, header_style="bold")
    for col in ("fayl", "ball", "butun", "~token", "sabab"):
        t.add_column(col, overflow="fold")
    for f in pack.files:
        t.add_row(f.path, f"{f.score:.1f}", "ha" if f.whole else "qisman", str(est_tokens(f.text)), ", ".join(f.reasons[:3]))
    console.print(t)
    n_map = pack.repomap.count(":\n")
    console.print(f"repomap: {n_map} fayl, ~{est_tokens(pack.repomap)} token | jami ~{pack.tokens} token")
    if show:
        console.print(pack.render(), markup=False, highlight=False)


@app.command()
def stats(repo: Path = RepoOpt):
    """Indeks statistikasi."""
    con = _need_index(repo)
    t = Table("til", "fayl", "qator", show_header=True, header_style="bold")
    for r in con.execute("SELECT lang, COUNT(*) n, SUM(lines) l FROM files GROUP BY lang ORDER BY n DESC"):
        t.add_row(r["lang"], str(r["n"]), str(r["l"]))
    console.print(t)
    t = Table("symbol turi", "soni", show_header=True, header_style="bold")
    for r in con.execute("SELECT kind, COUNT(*) n FROM symbols GROUP BY kind ORDER BY n DESC"):
        t.add_row(r["kind"], str(r["n"]))
    console.print(t)
    t = Table("bog'lanish", "ishonch", "soni", show_header=True, header_style="bold")
    for r in con.execute("SELECT kind, confidence, COUNT(*) n FROM edges GROUP BY kind, confidence ORDER BY kind, n DESC"):
        t.add_row(r["kind"], str(r["confidence"]), str(r["n"]))
    console.print(t)


if __name__ == "__main__":
    app()
