# Lokal Coder Agent — Ishlab chiqish rejasi

> Manba: `s.md` (tadqiqot) + suhbatda qabul qilingan yakuniy qarorlar (2026-10-20).
> Bu reja **faqat kod yozish** uchun agentni quradi. Boshqa vazifalar (chat, matn, umumiy yordamchi) bu loyihaga kirmaydi.

---

## 1. Maqsad

To'liq **lokal** ishlaydigan (internetsiz, API'siz) coding agent:

- loyihani o'zi indekslaydi va tushunadi (fayllar, funksiyalar, bog'lanishlar);
- vazifa uchun kerakli kodni **dastur** topib beradi — model taxmin qilmaydi;
- kichik model kod yozadi, dastur uni qo'llaydi va **test/lint bilan tekshiradi**;
- xato bo'lsa, xato matni bilan qayta tuzatadi;
- natijani diff ko'rinishida ko'rsatadi, foydalanuvchi tasdiqlaydi.

**Asosiy tamoyil** (`s.md`dan): *markazda katta model emas, loyiha haqidagi tekshiriladigan bilim va tekshiruv turadi. Modelga dalil tayyorlab beriladi, u hammasini yoddan bilishi talab qilinmaydi.*

**Nima kutilmaydi:** 7B model Opus darajasiga chiqmaydi. Maqsad — mayda/o'rta vazifalarni (funksiya, endpoint, bug fix, test, refaktoring) ishonchli bajaradigan, internet yo'q paytda ham ishlaydigan agent.

---

## 2. Cheklovlar (apparat)

| Resurs | Qiymat | Ta'siri |
|---|---|---|
| GPU | RTX 3050, **8 GB VRAM** | Bir vaqtda bitta 7B model + kichik draft model |
| RAM | **16 GB** | 30B MoE modellar sig'maydi; modellarni RAM'da almashtirib bo'lmaydi |
| CPU | i7-11700 (8 yadro) | Embedding modeli CPU'da ishlaydi |
| Context | **16K token** (amaliy) | Bir vaqtda ~5–15 fayl ko'rinadi → context yig'uvchi juda muhim |

---

## 3. Yakuniy qarorlar

| # | Qaror | Sabab |
|---|---|---|
| 1 | **Bitta asosiy coder model** hamma rolda ishlaydi (coder, planner, reviewer) | Model almashtirish har safar 5–15 s; bir xil o'lchamdagi modellar foyda bermaydi |
| 2 | Asosiyga **0.5B draft model** qo'shiladi (speculative decoding) | Generatsiya ~1.5–2x tez, sifat o'zgarmaydi |
| 3 | **Embedding modeli CPU'da** | GPU'ni band qilmaydi |
| 4 | **Qat'iy pipeline** — qadamlarni dastur boshqaradi, model faqat kod yozadi/tuzatadi | 7B model erkin tool-calling'da ko'p adashadi |
| 5 | Edit formati: **search/replace bloklari** (Aider uslubi) | Kichik model butun faylni qayta yozsa, kodni buzadi |
| 6 | Saqlash: **bitta SQLite** (FTS5 + sqlite-vec + graf jadvallari) | Server kerak emas, bitta fayl |
| 7 | Hech narsa olib tashlanmaydi — **navbat bilan qo'shiladi**, har qadam benchmarkda o'lchanadi | Qaysi qism foyda berayotgani aniq bo'lsin |
| 8 | Avval **4 ta stack**: Python (Django/DRF), Go, TypeScript (Next.js), Dart (Flutter) | O'z loyihalarim shu stacklarda; 35 tilni yuzaki emas, 4 tilni chuqur |
| 9 | Fine-tune **qilinmaydi** (hozircha) | `s.md`: avval kontekst, skill, test, xotira; keyin o'lchab ko'rib qaror |

---

## 4. Modellar

| Model | Rol | Joyi | Hajmi |
|---|---|---|---|
| `Qwen2.5-Coder-7B-Instruct` Q4_K_M (GGUF) | Asosiy: yozish, tuzatish, reja, review | GPU | ~4.7 GB |
| `Qwen2.5-Coder-0.5B-Instruct` Q8_0 (GGUF) | Draft (speculative decoding) | GPU | ~0.5 GB |
| `bge-small-en-v1.5` yoki `Qwen3-Embedding-0.6B` | Semantik qidiruv (7-bosqich) | CPU | 0.1–1 GB |

VRAM byudjeti: 4.7 + 0.5 + ~2 GB KV cache (16K, q8_0) ≈ **7.2 GB** ✅

> Model tanlovi 0-bosqichda benchmark bilan tasdiqlanadi. Yangiroq coder modellar chiqqan bo'lsa (HF'da tekshirish), ular ham sinaladi. Arxitektura modelga bog'liq emas — faqat GGUF fayl almashadi.
> **Kelajak:** RAM 32 GB bo'lsa → `Qwen3-Coder-30B-A3B` (MoE, expertlar RAM'da: `--n-cpu-moe`).

---

## 5. Texnologiyalar

| Qatlam | Texnologiya |
|---|---|
| Model serveri | **llama.cpp** `llama-server` (CUDA build, OpenAI-mos API) |
| Agent tili | **Python 3.11+**, framework'siz (LangGraph va h.k. yo'q) |
| LLM klient | `httpx` yoki `openai` SDK → `http://127.0.0.1:8080/v1` |
| Parsing | `tree-sitter` + `tree-sitter-language-pack` (py, ts/js, go, dart) |
| Aniq bog'lanishlar | SCIP indekserlar: `scip-python`, `scip-typescript`, `scip-go` (8-bosqich) |
| Matn qidiruvi | `ripgrep` + SQLite **FTS5** (BM25) |
| Vektor qidiruvi | **sqlite-vec** (7-bosqich) |
| Graf | SQLite `edges` jadvali + recursive CTE; ranking uchun `networkx` PageRank |
| Token sanash | model tokenizer (`llama-server /tokenize`) |
| Tekshiruv | loyihaning o'z buyruqlari: `pytest`, `ruff`, `go test`, `go vet`, `eslint`, `tsc`, `flutter analyze` |
| Xavfsizlik | `ast-grep`, `semgrep` CE (9-bosqich) |
| MCP | `fastmcp` (5-bosqich) |
| CLI | `typer` + `rich` (diff ko'rsatish) |
| Vizual | Cytoscape.js yoki React Flow (11-bosqich) |
| Test | `pytest` |

---

## 6. Arxitektura

```
                      agent "UserSerializer'ga phone field qo'sh"
                                      │
                                      ▼
┌──────────────────────────── ORCHESTRATOR (Python, qat'iy pipeline) ───────────────────────────┐
│                                                                                               │
│  [1] Indeks yangilash ─── git diff / fayl hash → faqat o'zgargan fayllar qayta parse         │
│        │                                                                                      │
│  [2] Kerakli kodni topish ─── FTS5 + ripgrep + symbol qidiruv + graf (+ embedding, 7-bosq.)  │
│        │                                                                                      │
│  [3] Context yig'ish ─── RepoMap + tanlangan fayllar + qoidalar + xotira (≤ 12K token)       │
│        │                                                                                      │
│  [4] LLM: search/replace bloklari yozadi                     ◄── yagona MODEL qadami #1      │
│        │                                                                                      │
│  [5] Edit qo'llash ─── aniq moslik → fuzzy moslik → topilmasa modelga qaytarish              │
│        │                                                                                      │
│  [6] Tekshiruv ─── lint + type-check + test (.agent.toml dagi buyruqlar)                    │
│        │                                                                                      │
│        ├── o'tdi ──► [8]                                                                      │
│        └── xato  ──► [7] LLM: xato matni + kod → tuzatish   ◄── MODEL qadami #2 (max 3)      │
│                                                                                               │
│  [8] Diff ko'rsatish → foydalanuvchi tasdiqlaydi → commit (yoki rollback)                    │
│  [9] Xotiraga yozish ─── vazifa, xatolar, yechimlar                                          │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
          │                    │                        │                       │
   ┌──────▼──────┐     ┌───────▼───────┐       ┌────────▼────────┐     ┌────────▼────────┐
   │ llama-server│     │ SQLite (index │       │ Verify runner   │     │ Memory (SQLite) │
   │ 7B + 0.5B   │     │ FTS, graf,vec)│       │ subprocess      │     │ 5 qatlam        │
   └─────────────┘     └───────────────┘       └─────────────────┘     └─────────────────┘
```

### Context byudjeti (16K, `s.md`dan moslashtirilgan)

| Qism | Token |
|---|---|
| Tizim qoidalari + vazifa + edit formati | 1.5K |
| RepoMap (imzolar xaritasi) | 1.5K |
| Vazifaga tegishli kod | 7K |
| Xotira + skill + loyiha qoidalari | 2K |
| Model javobi uchun joy | 4K |

> Boshlang'ich konfiguratsiya; benchmark natijalariga qarab o'zgartiriladi.

---

## 7. Papka strukturasi

```
agent/
├── PLAN.md                  ← shu fayl
├── s.md                     ← tadqiqot
├── docs/
│   ├── ARCHITECTURE.md      ← quruvchi qarorlar (1-bosqichdan boshlab)
│   └── PROGRESS.md          ← har o'zgarishda yangilanadi
├── coder/                   ← Python paket
│   ├── cli.py               ← `agent` buyrug'i
│   ├── config.py            ← .agent.toml o'qish
│   ├── llm/                 ← llama-server klient, prompt shablonlar
│   ├── indexer/             ← tree-sitter parse, SQLite yozish, incremental
│   ├── search/              ← FTS, symbol, graf, embedding, RRF
│   ├── context/             ← RepoMap, byudjet, context yig'ish
│   ├── edit/                ← search/replace parse + qo'llash
│   ├── verify/              ← lint/test runner, xato parse
│   ├── memory/              ← 5 qatlamli xotira
│   ├── pipeline.py          ← orchestrator
│   └── mcp_server.py        ← (5-bosqich)
├── skills/                  ← SKILL.md lar (6-bosqich)
├── bench/
│   ├── tasks/               ← benchmark vazifalari (YAML)
│   ├── run.py
│   └── results/
├── scripts/
│   └── start_llm.ps1        ← llama-server ishga tushirish
├── models/                  ← GGUF fayllar (.gitignore)
└── tests/
```

Har bir loyiha ildizida `.agent.toml`:

```toml
[project]
languages = ["python", "dart"]

[verify]
lint  = "ruff check ."
types = ""
test  = "pytest -x -q"

[rules]
# loyiha qoidalari — har promptga qo'shiladi
text = """
- DRF serializerlar serializers.py da
- Har yangi endpointga test yoziladi
"""
```

---

## 8. Bosqichlar (ketma-ketlik)

Har bosqich oxirida: **benchmark ishga tushiriladi → natija `docs/PROGRESS.md`ga yoziladi**. Natija yaxshilanmasa — sababini topmasdan keyingi bosqichga o'tilmaydi.

### 0-bosqich — Muhit va o'lchov asosi (2–3 kun)

- [ ] llama.cpp CUDA build (GitHub releases, Windows `cuda-12` zip) o'rnatish
- [ ] GGUF modellarni yuklab olish (`models/`)
- [ ] `scripts/start_llm.ps1`:
  ```
  llama-server -m models/qwen2.5-coder-7b-q4_k_m.gguf `
               -md models/qwen2.5-coder-0.5b-q8_0.gguf `
               -ngl 99 -ngld 99 -c 16384 -fa on -ctk q8_0 -ctv q8_0 `
               --draft-max 16 --draft-min 1 --port 8080
  ```
  *(flag nomlarini o'rnatilgan versiyaning `--help` bilan tekshirish)*
- [ ] Tezlikni o'lchash: draft bilan va draftsiz (token/s)
- [ ] **Benchmark to'plami**: o'z repolarimdan (Makondosh, ILMINVEST, MyCard, SpeakUp) 15–20 ta vazifa. Har biri:
  ```yaml
  id: mycard-001
  repo: ../my_card
  base_commit: abc123
  task: "Card modeliga is_archived field qo'sh, API'da filtrlash bilan"
  verify: "pytest cards/tests -q"
  ```
  Vazifa turlari: bug fix, kichik feature, test yozish, refaktoring, ko'p faylli o'zgarish.
- [ ] Bazaviy chiziq: **Aider + shu lokal model** bilan benchmark → solishtirish uchun raqam

**Tayyor:** model 8 GB'da ishlaydi, tok/s ma'lum, benchmark + bazaviy natija bor.

### 1-bosqich — Indekser (4–5 kun)

- [ ] Fayllarni yurish (`.gitignore` hisobga olinadi, binar/katta fayllar tashlanadi)
- [ ] tree-sitter bilan parse: funksiya, klass, metod, import, chaqiruvlar (taxminiy)
- [ ] SQLite sxemasi:
  ```sql
  files(id, path, lang, sha, mtime)
  symbols(id, file_id, name, kind, signature, start_line, end_line, parent_id)
  edges(src_symbol, dst_name, dst_symbol NULL, kind, file_id, line, confidence)
       -- kind: imports | calls | inherits | references
       -- confidence: exact | name_match | guess
  fts_code(path, symbol, content)  -- FTS5
  ```
- [ ] Incremental: faqat `sha` o'zgargan fayllar qayta parse
- [ ] `agent index <repo>` buyrug'i

**Tayyor:** 1000+ faylli repo < 1 daqiqada indekslanadi, qayta indeks < 5 s.

### 2-bosqich — Qidiruv + RepoMap + Context yig'uvchi (5–6 kun)

- [ ] Vazifadan kalit so'zlar/identifikatorlar ajratish (regex + model'dan qisqa so'rov)
- [ ] Qidiruv: FTS5 (BM25) + symbol nomi + ripgrep → birlashtirish
- [ ] Graf bo'yicha kengaytirish: topilgan symbol'ning chaqiruvchilari/chaqirilganlari (1–2 qadam)
- [ ] **RepoMap** (Aider g'oyasi): fayl → imzolar ro'yxati, PageRank bilan muhimlari tanlanadi
- [ ] Token byudjeti bo'yicha kesish (yuqoridagi jadval)
- [ ] `agent context "<vazifa>"` — modelga nima yuborilishini ko'rsatadi (debug uchun juda muhim)
- [ ] O'lchov: benchmarkdagi har vazifa uchun "to'g'ri fayllar context'ga tushdimi?" (recall@context)

**Tayyor:** recall@context ≥ 80%.

### 3-bosqich — Edit + Tekshiruv sikli (5–6 kun)

- [ ] Prompt shabloni: qoidalar + context + vazifa + search/replace formati namunasi
- [ ] Javobdan bloklarni parse qilish (noto'g'ri formatga chidamli)
- [ ] Qo'llash: aniq moslik → bo'shliqlarni e'tiborsiz moslik → fuzzy (difflib) → topilmasa modelga "bu blok topilmadi" deb qaytarish
- [ ] Yangi fayl yaratish qo'llab-quvvatlanadi
- [ ] Verify runner: `.agent.toml` buyruqlari, timeout, chiqishni qisqartirish (faqat xato qismi)
- [ ] Tuzatish sikli: xato → model → edit → verify, **max 3 urinish**
- [ ] Xavfsizlik: ish alohida git branch/stash'da; muvaffaqiyatsiz bo'lsa to'liq rollback
- [ ] Diff ko'rsatish (`rich`) + tasdiqlash → commit

**Tayyor:** benchmarkda ≥ bazaviy (Aider) natija.

### 4-bosqich — CLI va MVP (2–3 kun)

- [ ] `agent "<vazifa>"`, `agent index`, `agent context`, `agent bench`
- [ ] `.agent.toml` avtomatik yaratish (`agent init` — tilni va test buyruqlarini aniqlaydi)
- [ ] Har ishga tushirish log'i (prompt, javob, verify natijasi) → `.agent/runs/`

> ✅ **MVP shu yerda tugaydi.** Taxminan 3–4 hafta. Keyin 1–2 hafta o'z loyihalarimda real ishlatib, qayerda sinishini `docs/PROGRESS.md`ga yozib borish.

### 5-bosqich — MCP server (2 kun)

- [ ] `fastmcp` orqali: `search_code`, `find_symbol`, `find_references`, `impact(file|symbol)`, `repo_map`
- [ ] Claude Code / OpenCode'ga ulab sinash → indeks cloud model bilan ham foyda beradi

### 6-bosqich — To'liq xotira (5 qatlam) + Skill'lar (1 hafta)

`s.md` dagi 5 qatlam, bitta SQLite ichida:

| Qatlam | Nima saqlanadi | Jadval |
|---|---|---|
| Working | joriy vazifa holati, qadamlar, xatolar (qayta ishga tushganda davom etadi) | `task_state` |
| Project | arxitektura xulosalari, qoidalar, konfiguratsiya (kod hash'iga bog'langan) | `project_facts` |
| Episodic | bajarilgan vazifalar, uchragan xatolar → yechimlar | `episodes` |
| Skill | tasdiqlangan ish tartiblari | `skills/*/SKILL.md` |
| Knowledge cache | kutubxona hujjatlari (offline nusxa) | `docs_cache` |

Qoidalar:
- har yozuvda `kind: fact | assumption` — kuzatilgan fakt va taxmin ajratiladi;
- xotira kodning o'rnini bosmaydi: bog'langan fayl `sha` o'zgargan bo'lsa → yozuv `stale` deb belgilanadi, kod qayta tekshiriladi;
- skill avtomatik yaratilmaydi — agent **taklif qiladi**, men tasdiqlayman.

Boshlang'ich skill'lar: `add-api-endpoint`, `database-migration`, `add-test`, `debugging`, `refactoring`.
Har bir skill: shartlar, qadamlar, namunalar, tekshiruv buyrug'i.

### 7-bosqich — Embedding + Hybrid qidiruv (3–4 kun)

- [ ] CPU'da embedding modeli (`sentence-transformers` yoki `llama-server --embedding` alohida portda, `-ngl 0`)
- [ ] Symbol darajasida chunk'lash (funksiya/klass = 1 chunk)
- [ ] sqlite-vec'ga yozish, incremental
- [ ] **RRF** bilan birlashtirish: BM25 + symbol + graf + vektor
- [ ] O'lchov: recall@context oshdimi? Oshmasa — o'chirib qo'yiladi

### 8-bosqich — Cross-layer zanjir: FE → API → DB (2–3 hafta)

G'oyaning eng qimmatli va eng qiyin qismi.

- [ ] SCIP indekserlarini ulash → `edges.confidence = exact`
- [ ] Backend route ekstraktorlari: Django `urls.py` + DRF router, Go (chi/gin/net/http)
- [ ] Frontend API chaqiruv ekstraktorlari: Flutter `dio`/`http`, Next.js `fetch`/axios
- [ ] URL pattern moslashtirish: frontend chaqiruv ↔ backend route
- [ ] ORM: Django model ↔ jadval, Go (sqlc/gorm) ↔ jadval
- [ ] Har bog'lanishda `source:line` + `confidence` (`s.md`: dinamik routing taxmin deb belgilanadi)
- [ ] `agent trace "POST /api/login"` → `LoginPage → endpoint → view → service → model → table`
- [ ] Impact analysis shu zanjirdan foydalanadi

### 9-bosqich — Statik tekshiruv (3–4 kun)

- [ ] Verify bosqichiga `ast-grep` qoidalari va `semgrep` (faqat o'zgargan fayllar)
- [ ] Yangi kiritilgan topilmalar → modelga tuzatish uchun qaytariladi
- [ ] (Safia/secureagent loyihasidagi tajribadan qayta foydalanish)

### 10-bosqich — Planner va Reviewer rollari (1 hafta)

Hammasi **o'sha bitta 7B model**, faqat boshqa prompt bilan:

- [ ] **Planner:** katta vazifani 2–6 ta kichik qadamga bo'ladi (har biri alohida pipeline aylanishi)
- [ ] **Reviewer:** yakuniy diff'ni tekshiradi (keraksiz o'zgarishlar, unutilgan joylar, impact'dagi fayllar)
- [ ] O'lchov: ko'p faylli vazifalarda natija oshdimi?

### 11-bosqich — Vizual xarita (1 hafta)

- [ ] `agent serve` → lokal web sahifa: fayl/symbol grafi, FE→API→DB zanjiri, impact ko'rinishi
- [ ] Cytoscape.js yoki React Flow

### Keyinroq (ixtiyoriy)

- RAM 32 GB → `Qwen3-Coder-30B-A3B`
- Reviewer uchun boshqa model (turli "ko'r nuqtalar")
- Internet bo'lsa: rasmiy hujjat qidiruvi (Context7 g'oyasi) → `docs_cache`ga saqlash
- Cloud fallback (faqat xohlansa)

---

## 9. O'lchov (benchmark metrikalari)

`s.md`: *"Kuchli agent"ni katta prompt bilan emas, natija bilan o'lcha.*

| Metrika | Ma'nosi |
|---|---|
| **Pass rate** | vazifa testlari o'tgan % |
| **recall@context** | kerakli fayllar context'ga tushgan % |
| **Edit apply rate** | search/replace bloklari muvaffaqiyatli qo'llangan % |
| **Urinishlar soni** | o'rtacha tuzatish sikllari |
| **Keraksiz o'zgarishlar** | vazifaga aloqasiz o'zgargan qatorlar |
| **Vaqt** | vazifa boshidan oxirigacha (s) |
| **Trace aniqligi** | (8-bosqichdan) FE→API→DB bog'lanishlar to'g'riligi |

Natijalar: `bench/results/<sana>-<bosqich>.json` + qisqacha `docs/PROGRESS.md`da.

---

## 10. Xavflar va yechimlar

| Xavf | Yechim |
|---|---|
| 7B model search/replace formatini buzadi | Formatga chidamli parser + fuzzy moslik + qisqa namunali prompt; kerak bo'lsa llama.cpp grammar (GBNF) |
| Context'ga kerakli fayl tushmaydi | `agent context` bilan ko'rish, recall@context ni doimiy o'lchash |
| Test yo'q loyihalar | Kamida lint + type-check + import/compile tekshiruvi; agent avval test yozishni taklif qiladi |
| Indeks eskiradi | Har ishga tushirishda incremental yangilash (sha) |
| Xotira eski ma'lumot beradi | `sha` bog'lanishi, `stale` belgisi, kodni qayta tekshirish |
| Hamma narsani birdan qurish | Shu reja: har bosqich alohida, o'lchab borish |
| VRAM yetmaydi | KV cache q8_0, context 12K ga tushirish, draft modelni o'chirish |

---

## 11. `s.md` dan nima olindi

| `s.md` g'oyasi | Rejadagi joyi |
|---|---|
| Codebase Intelligence Engine, bilim grafigi | 1, 2, 8-bosqich |
| Aider RepoMap | 2-bosqich |
| 3 xil qidiruv (strukturaviy, matn/semantik, graf) | 2, 7-bosqich |
| Bog'lanishga manba + ishonchlilik | `edges.confidence`, 8-bosqich |
| Planner / ixtisoslashgan rollar (bitta model bilan) | 10-bosqich |
| Engineering skills, o'rganuvchi skills | 6-bosqich |
| 5 qatlamli xotira, fakt vs taxmin | 6-bosqich |
| Semgrep, CodeQL, ast-grep | 9-bosqich (CodeQL — keyinroq, og'ir) |
| Context7 / hujjatlar keshi | Keyinroq + `docs_cache` |
| 16K context byudjeti | 6-bo'lim |
| Avval Python/JS/SQL, keyin boshqa tillar | 4 stack (py, go, ts, dart) |
| Fine-tune'ga shoshilmaslik | 3-qaror |
| Natijani o'lchash | 9-bo'lim |

**Olinmadi:** GRASP, codeGRAPH, Codeknow'ga bog'lanish — ulardan faqat g'oyalar olinadi (kam ma'lum, yosh loyihalar; GRASP litsenziyasi cheklangan). Bir nechta katta modelni navbat bilan ishlatish — 8 GB'da sekin va foydasi kam.

---

## 12. Taxminiy vaqt

| Qism | Vaqt |
|---|---|
| 0–4 (MVP) | 3–4 hafta |
| Real ishlatish va tuzatish | 1–2 hafta |
| 5–7 | 2–3 hafta |
| 8 (cross-layer) | 2–3 hafta |
| 9–11 | 3 hafta |
| **Jami** | **~3 oy** |
