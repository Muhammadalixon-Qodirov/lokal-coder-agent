"""Orchestrator — qat'iy pipeline (PLAN.md, 6-bo'lim):

  indeks → qidiruv/context → LLM edit → qo'llash → tekshiruv → (xato bo'lsa) LLM tuzatadi … → natija

Model faqat ikki joyda qatnashadi: o'zgarishni yozish va xatoni tuzatish (+ ixtiyoriy yordamchi
qadamlar: query expansion va fayl tanlash). Qolgan hammasini oddiy kod bajaradi.

Har urinishda context qaytadan yig'iladi (o'zgargan fayllarning joriy holati bilan) —
xabarlar to'planib 16K context'ni to'ldirib yubormaydi.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from coder.config import Config, load_config
from coder.context.builder import ContextPack, build_context
from coder.context.expand import Expansion, expand
from coder.context.rank import rank
from coder.context.select import apply_selection, select_files
from coder.edit.apply import apply_blocks, apply_fenced, rollback, unified_diff
from coder.edit.autofix import autofix
from coder.edit.blocks import parse_blocks, parse_fenced
from coder.indexer import index_repo, open_index
from coder.llm import LLM
from coder.llm import prompts
from coder.verify import VerifyResult, verify
from coder.verify.spec import SPEC_PREFIX, SpecTest, make_spec, remove_spec

MAX_DIFF_CHARS = 3500
# vazifa o'chirishni so'rasagina REPLACE mavjud funksiyani olib tashlashi mumkin
_DELETE_WORDS = re.compile(r"\b(remove|delete|drop|rename|replace|o'chir|olib tashla|nomini)", re.IGNORECASE)
MAX_OUTPUT_CHARS = 3000


@dataclass
class Attempt:
    n: int
    reply: str
    applied: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    verify: str = ""
    seconds: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class RunResult:
    ok: bool
    task: str
    originals: dict[str, str | None] = field(default_factory=dict)
    attempts: list[Attempt] = field(default_factory=list)
    verify: VerifyResult | None = None
    context_files: list[str] = field(default_factory=list)
    diff: str = ""
    seconds: float = 0.0
    log_path: Path | None = None
    spec: SpecTest | None = None
    spec_note: str = ""

    @property
    def changed(self) -> list[str]:
        return list(self.originals)


Event = Callable[[str], None]


def _clip(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n // 2] + "\n...\n" + s[-n // 2 :]


class Pipeline:
    def __init__(
        self,
        repo: Path,
        llm: LLM,
        cfg: Config | None = None,
        max_fix: int = 3,
        use_expand: bool = True,
        use_select: bool = True,
        use_spec: bool = False,
        spec_python: str = "python",
        on_event: Event | None = None,
    ):
        self.repo = repo.resolve()
        self.llm = llm
        self.cfg = cfg or load_config(self.repo)
        self.max_fix = max_fix
        self.use_expand = use_expand
        self.use_select = use_select
        self.use_spec = use_spec
        self.spec_python = spec_python
        self.emit = on_event or (lambda s: None)

    # ------------------------------------------------------------ context

    def _context(self, task: str, exp: Expansion, chosen: list[str], pinned: list[str]) -> tuple[ContextPack, list[str]]:
        index_repo(self.repo)  # o'zgargan fayllar qayta indekslanadi (tez)
        con = open_index(self.repo)
        try:
            r = rank(con, task, exp.keywords, exp.identifiers)
            apply_selection(con, r, list(dict.fromkeys(pinned + chosen)))
            if pinned:  # o'zgartirilgan fayllar har doim context'da
                ids = {row["path"]: row["id"] for row in con.execute("SELECT id, path FROM files")}
                top = max(r.files.values(), default=1.0)
                for p in pinned:
                    if p in ids:
                        r.files[ids[p]] = r.files.get(ids[p], 0.0) + 10 * top
            pack = build_context(con, self.repo, task, ranking=r)
            known = [row[0] for row in con.execute("SELECT path FROM files")]
        finally:
            con.close()
        return pack, known

    def _messages(self, pack: ContextPack, task: str, extra: str = "", spec: SpecTest | None = None) -> list[dict]:
        rules = prompts.RULES.format(rules=self.cfg.rules) if self.cfg.rules else ""
        if spec is not None:
            rules += prompts.SPEC.format(path=spec.path, code=spec.code)
        user = prompts.USER_EDIT.format(context=pack.render(), rules=rules, task=task.strip())
        if extra:
            user += "\n" + extra
        return [{"role": "system", "content": prompts.SYSTEM_EDIT}, *prompts.EXAMPLE, {"role": "user", "content": user}]

    # ------------------------------------------------------------ run

    def run(self, task: str) -> RunResult:
        t0 = time.perf_counter()
        res = RunResult(ok=False, task=task)

        self.emit("indekslash")
        index_repo(self.repo)
        exp, chosen = Expansion(), []
        con = open_index(self.repo)
        try:
            if self.use_expand:
                self.emit("vazifani tahlil qilish (kalit so'zlar)")
                exp = expand(self.llm, con, task)
            if self.use_select:
                self.emit("kerakli fayllarni tanlash")
                chosen = select_files(self.llm, con, task, rank(con, task, exp.keywords, exp.identifiers))
        finally:
            con.close()

        # Har urinish — tranzaksiya: bloklardan biri qo'llanmasa, SHU urinish to'liq bekor qilinadi
        # (qisman qo'llangan bloklar qayta yuborilganda kod takrorlanmasin). Tekshiruv xatosida esa
        # o'zgarish saqlanadi va model faqat xatoni tuzatadi (forward-fix).
        extra = ""
        for n in range(1, self.max_fix + 2):
            pack, known = self._context(task, exp, chosen, res.changed)
            if n == 1:
                res.context_files = pack.paths
                self.emit(f"context: {len(pack.files)} fayl, ~{pack.tokens} token")
                if self.use_spec:
                    self.emit("spec-test yozilmoqda (TDD)")
                    res.spec, res.spec_note = make_spec(self.llm, self.repo, task, pack, self.spec_python)
                    self.emit(res.spec_note)
            self.emit(f"{n}-urinish: model yozmoqda")
            ta = time.perf_counter()
            c = self.llm.chat(self._messages(pack, task, extra, res.spec), max_tokens=3000, temperature=0.1)
            att = Attempt(n, c.text, prompt_tokens=c.prompt_tokens, completion_tokens=c.completion_tokens)
            res.attempts.append(att)

            blocks, perrs = parse_blocks(c.text)
            blocks = [b for b in blocks if SPEC_PREFIX not in b.path]  # qabul testini o'zgartirish mumkin emas
            att.problems += [e.message for e in perrs]
            if blocks:
                out = apply_blocks(self.repo, blocks, known, allow_delete=bool(_DELETE_WORDS.search(task)))
            else:
                fenced = parse_fenced(c.text)
                out = apply_fenced(self.repo, fenced, known) if fenced else None
            if out is None or (not out.applied and not out.failed):
                att.seconds = time.perf_counter() - ta
                extra = prompts.NO_BLOCKS if not att.problems else prompts.RETRY_EDIT_FAILED.format(
                    problems="\n".join(f"- {p}" for p in att.problems))
                self.emit("javobda o'zgarish yo'q")
                continue

            att.applied = [b.path for b in out.applied]
            att.problems += [msg for _, msg in out.failed]
            self.emit(f"qo'llandi: {len(out.applied)} blok" + (f", xato: {len(out.failed)}" if out.failed else ""))

            if att.problems:
                rollback(self.repo, out.originals)  # faqat shu urinishni bekor qilish
                att.seconds = time.perf_counter() - ta
                extra = prompts.RETRY_EDIT_FAILED.format(problems="\n".join(f"- {p}" for p in att.problems))
                continue

            for rel, orig in out.originals.items():
                res.originals.setdefault(rel, orig)  # asl (vazifadan oldingi) holat saqlanadi
            for note in autofix(self.repo, res.changed):
                self.emit(f"autofix: {note}")
            self._drop_unchanged(res)

            self.emit("tekshiruv")
            if res.spec is not None:  # model tegib ketgan bo'lsa ham asl holatda
                (self.repo / res.spec.path).write_text(res.spec.code, encoding="utf-8")
            vr = verify(self.repo, self.cfg, res.changed, [("spec", res.spec.command)] if res.spec else None)
            res.verify = vr
            att.verify = vr.summary()
            att.seconds = time.perf_counter() - ta
            self.emit(vr.summary())
            if vr.ok:
                res.ok = True
                break
            f = vr.failure
            extra = prompts.RETRY_VERIFY_FAILED.format(
                diff=_clip(unified_diff(self.repo, res.originals), MAX_DIFF_CHARS),
                step=f.name,
                command=f" (`{f.command}`)" if f.command else "",
                output=_clip(f.output, MAX_OUTPUT_CHARS),
            )

        remove_spec(self.repo, res.spec)
        res.diff = unified_diff(self.repo, res.originals)
        res.seconds = time.perf_counter() - t0
        res.log_path = self._log(res, exp, chosen)
        return res

    def _drop_unchanged(self, res: RunResult) -> None:
        for rel in list(res.originals):
            p = self.repo / rel
            now = p.read_text(encoding="utf-8", errors="replace") if p.exists() else None
            if now == res.originals[rel]:
                del res.originals[rel]

    def _log(self, res: RunResult, exp: Expansion, chosen: list[str]) -> Path:
        d = self.repo / ".agent" / "runs"
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
        p.write_text(json.dumps({
            "task": res.task,
            "ok": res.ok,
            "seconds": round(res.seconds, 1),
            "expansion": asdict(exp),
            "selected": chosen,
            "context_files": res.context_files,
            "changed": res.changed,
            "attempts": [asdict(a) for a in res.attempts],
            "diff": res.diff,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        return p
