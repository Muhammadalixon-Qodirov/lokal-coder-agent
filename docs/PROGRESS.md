# PROGRESS

Reja: [../PLAN.md](../PLAN.md)

| Sana | Bosqich | Nima qilindi | Natija |
|---|---|---|---|
| 2026-10-20 | — | Tadqiqot (`s.md`) tahlil qilindi, yakuniy qarorlar, `PLAN.md` | — |
| 2026-10-20 | 0 | llama.cpp b11756 (CUDA 12.4) + Qwen2.5-Coder-7B Q4_K_M + 0.5B Q8_0 → `D:\llm` | ✅ |
| 2026-10-20 | 0 | Skelet: git, `.venv` (py3.11), `pyproject.toml`, `scripts/start_llm.ps1`, `scripts/bench_speed.py`, `coder/llm/client.py` (json_schema qo'llab-quvvatlanadi) | ✅ |
| 2026-10-20 | 0 | Tezlik o'lchovi (quyida) | ✅ |
| 2026-10-20 | 1 | Indekser: tree-sitter (py, go, ts/tsx/js, dart) → SQLite; incremental (sha1); edge resolution | 5/5 test ✓ |
| 2026-10-20 | 1 | CLI: `agent index / find / refs / calls / stats / context` | ✅ |
| 2026-10-20 | 2 | Import → fayl bog'lanishlari (`file_links`), git co-change (`cochange`, `churn`) — sxema v3 | ✅ |
| 2026-10-20 | 2 | Context yig'uvchi: aniq nom + yo'l + marshrut + FTS + graf qo'shnilari + co-change + personalized PageRank + testlarni ko'tarish; token byudjeti; RepoMap | ✅ |
| 2026-10-20 | 2 | LLM yordamchilari: query expansion (o'zbekcha → inglizcha kalit so'zlar), nomzod fayllarni qayta saralash (JSON `enum` — faqat haqiqiy yo'llar) | ✅ |
| 2026-10-20 | 2 | Benchmark: git tarixidan 106 vazifa (`bench/mine.py`), `bench/recall.py`, `bench/why.py` | ✅ |

## 0-bosqich: tezlik (RTX 3050 8 GB, 16K context, KV q8_0, flash-attn)

| Rejim | tok/s | VRAM |
|---|---|---|
| speculative'siz | 41.4 | 5.5 GB |
| **0.5B draft** (`--spec-type draft-simple`, n_max 16) | **61.7** (~1.5x), qabul 25–50% | 6.3 GB |

> Eslatma: yangi llama.cpp'da `-md` yetarli emas — `--spec-type draft-simple` ham kerak. `--draft-max` → `--spec-draft-n-max`.
> ngram rejimi (`-Spec ngram`) edit vazifalarida (mavjud kod qayta yoziladi) sinaladi — 3-bosqich.

## 1-bosqich: indekser

| Repo | Fayl | Symbol | Bog'lanish | To'liq indeks | Qayta indeks |
|---|---|---|---|---|---|
| my_card (Django) | 145 | 730 | 3 845 | 0.4 s | — |
| ilm_invst (Go + Next.js) | 275 | 2 683 | 18 785 | 1.6 s | 0.3 s |
| hudud1 | 361 | 3 236 | 22 783 | 2.4 s | — |

## 2-bosqich: recall@context

Benchmark: 5 repo, 106 commit. Vazifa = commit sarlavhasi (qiyin rejim), gold = commit o'zgartirgan mavjud fayllar.
`recall@code` — gold fayllar kod qismiga tushgan ulush; `+map` — kod yoki RepoMap'da.

| Versiya | O'zgarish | recall@code | to'liq | +map | top1 |
|---|---|---|---|---|---|
| v1 | FTS + aniq nom + graf qo'shnilari | 56.2% | 41.5% | 75.0% | 44.3% |
| v2 | import → fayl, ikki tomonlama graf, yo'l qismlari | 57.9% | 41.5% | 76.6% | 44.3% |
| v3 | testlarni ko'tarish, stopword'lar, fayl hajmi chegarasi | 60.5% | 46.2% | 75.6% | 35.8% |
| v4 | + LLM expansion (bir xil og'irlik) | 57.2% | 38.7% | 76.9% | 34.0% |
| v5 | expansion alohida o'tishda, 0.5 og'irlik | 63.4% | 47.2% | 76.2% | 37.7% |
| v6 | + git co-change | 64.3% | 47.2% | 79.7% | 35.8% |
| v7 | + API marshrut satrlari | 64.8% | 47.2% | 80.2% | 35.8% |
| **v9** | + LLM fayl tanlash (boost 0.5) | **65.0%** | **50.0%** | **80.0%** | **40.6%** |

Repo bo'yicha (v7): my_card 93%, cyber 81%, hackaton_finder 79%, ilm_invest 70%, **hudud1 37%**.

Maqsad (recall@context ≥ 80%) — kod qismida **bajarilmadi (65%)**, kod+map'da 80%.
hudud1 sababi: commit xabarlari o'zbekcha, kod inglizcha, *va* backend kodida o'zbekcha prompt matnlari ko'p — o'zbekcha so'zlar ular bilan mos tushib, FTS'ni chalg'itadi.
Commit to'plami ideal emas: gold'ga yondosh (tasodifiy) fayllar ham kiradi — haqiqiy vazifalarda recall yuqoriroq bo'lishi kutiladi.

## 3-bosqich: edit + tekshiruv sikli

Qurilgan: `coder/edit/blocks.py` (SEARCH/REPLACE parser), `apply.py` (aniq → bo'shliqsiz → indent → fuzzy moslik,
rollback, diff, o'chirishdan himoya), `symbolic.py` (butun funksiya/klass yozilsa — tree-sitter bilan nom bo'yicha
almashtirish, qisman klassni a'zo darajasida birlashtirish), `autofix.py` (py: ruff F821 → std import; go: import
qo'shish/olib tashlash + gofmt), `verify/runner.py` (tree-sitter sintaksis → lint → types → test), `verify/spec.py`
(TDD spec-test), `pipeline.py`, CLI `agent run` / `agent init`.

Edit benchmark (`bench/edit_bench.py`): 2 fixture (Python do'kon, Go notes), 12 vazifa (7 o'zbekcha), YASHIRIN testlar.

| Versiya | O'zgarish | Yashirin testlar | "Tayyor" dedi | Noto'g'ri "tayyor" | s/vazifa |
|---|---|---|---|---|---|
| v1 | SEARCH/REPLACE + few-shot + verify sikli | 3/12 | 6 | 3 | 28 |
| v2 | har urinish asl holatdan + funksiya darajasidagi edit | 2/12 | 3 | 1 | 39 |
| v3 | tranzaksion urinish + forward-fix + autofix (importlar) | 3/12 | 9 | 6 | 19 |
| v4 | + o'chirishdan himoya | 3/12 | 8 | 5 | 27 |
| **v4 + spec** | + TDD spec-test (`--spec`) | **6/12** (py 5/8, go 1/4) | 5 | 4 | 32 |

Xulosalar:
- Mexanik muammolar (format, import, takrorlanish) asosan hal qilindi: v3'da 12 dan 9 tasida o'zgarish qo'llanib, tekshiruvdan o'tdi.
- Asosiy to'siq endi **mantiqiy to'g'rilik**: model talabning bir qismini o'tkazib yuboradi (faqat bo'sh joyli title, tartib yo'nalishi, vergul o'rniga bo'sh joy).
- Spec-test yashirin natijani ikki baravar oshirdi, lekin modelning testi ham ba'zan xato → to'g'ri yechimni "o'tmadi" deb belgilaydi.
- Benchmark kichik (12) va temperature 0.1 → ±1–2 vazifa tebranish normal.

## Ma'lum kamchiliklar / keyingi g'oyalar

- Spec-test xato bo'lsa: model testni tahlil qilib "test noto'g'ri" deyishi (reviewer, 10-bosqich).
- Go spec-test: ba'zan test funksiyasi yozilmaydi; mavjud helper bilan to'qnashuv.
- Benchmark'ni kengaytirish (TS fixture, ko'proq vazifa) — natijalar barqarorroq bo'lsin.

- Embedding qidiruvi (7-bosqich) — o'zbekcha↔inglizcha semantik moslik uchun eng katta kutilgan yaxshilanish.
- Model "qaysi faylni ochay?" deb so'rashi (RepoMap'dan) — 3-bosqich pipeline'iga.
- Go: struct embedding `inherits` emas; `ambiguous` chaqiruvlar (receiver tipi bo'yicha aniqlash — 8-bosqich, SCIP).

## Hozirgi holat

- Server: `.\scripts\start_llm.ps1` (draft bilan).
- Ishlatish: `agent init <repo>` → `agent run "vazifa" -r <repo> [--spec]`.
- 3-bosqich ishlaydi (MVP darajasida). Keyingi: spec-test sifatini oshirish, so'ng 4-bosqich (real loyihalarda sinash).
