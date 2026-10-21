# Lokal Coder Agent

To'liq **lokal** ishlaydigan coding agent: internet ham, cloud API ham kerak emas. 8 GB VRAM'li oddiy GPU'da (RTX 3050) 7B coder model bilan ishlaydi.

Asosiy g'oya: kichik modeldan hamma narsani bilishni talab qilmaslik. Kodni topish, o'zgarishni qo'llash va tekshirish — oddiy, aniq dastur ishi; model faqat kod yozadi va xatoni tuzatadi.

```
vazifa → indeks → kerakli kodni topish → model o'zgarish yozadi → qo'llash → autofix
       → sintaksis / lint / build / test → (xato bo'lsa) model tuzatadi … → diff → tasdiqlash
```

## Imkoniyatlar

- **Indekser** — tree-sitter (Python, Go, TypeScript/JS, Dart) → SQLite: symbollar, chaqiruvlar, importlar, FTS5, git co-change. Incremental.
- **Context yig'uvchi** — aniq nomlar, fayl yo'llari, API marshrutlari, BM25, graf qo'shnilari, personalized PageRank (Aider RepoMap g'oyasi), testlarni ko'tarish, token byudjeti. O'zbekcha vazifalar uchun LLM orqali kalit so'z kengaytirish va fayl tanlash (JSON sxema bilan cheklangan).
- **Edit** — SEARCH/REPLACE bloklari (aniq → bo'shliqsiz → indent → fuzzy moslik); model butun funksiya yozsa — tree-sitter bilan nom bo'yicha almashtirish; tasodifiy o'chirishdan himoya; tranzaksion urinishlar.
- **Autofix** — unutilgan importlar (Python: ruff F821, Go: std paketlar + gofmt).
- **Tekshiruv** — tree-sitter sintaksis → lint → build → test; ixtiyoriy TDD spec-test (`--spec`).

## O'rnatish

```powershell
py -3.11 -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
```

Model serveri — [llama.cpp](https://github.com/ggml-org/llama.cpp) (`llama-server`) va GGUF modellar:
`Qwen2.5-Coder-7B-Instruct-Q4_K_M` + draft `Qwen2.5-Coder-0.5B-Instruct-Q8_0` (standart joy `D:\llm`, `LLM_HOME` bilan o'zgartiriladi).

```powershell
.\scripts\start_llm.ps1          # 0.5B draft bilan ~62 tok/s (RTX 3050)
```

## Ishlatish

```powershell
agent init  C:\path\to\repo                       # .agent.toml: lint/build/test buyruqlari
agent index C:\path\to\repo
agent context "login validatsiyasi" -r C:\path\to\repo   # modelga nima yuborilishini ko'rish
agent run   "POST /notes da bo'sh title uchun 400 qaytarilsin" -r C:\path\to\repo --spec
```

`agent run` oxirida diff ko'rsatadi; rad etilsa fayllar asl holatiga qaytariladi.

## Holat

Ish jarayonida, natijalar va o'lchovlar — [docs/PROGRESS.md](docs/PROGRESS.md), reja — [PLAN.md](PLAN.md).

Qisqacha (12 vazifali edit benchmark, yashirin testlar): spec-test bilan **6/12**. Mexanik muammolar (format, importlar) asosan hal qilingan; asosiy chegara — 7B modelning mantiqiy aniqligi. Diff'ni har doim ko'zdan kechiring.
