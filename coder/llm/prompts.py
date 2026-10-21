"""Model uchun prompt shablonlari. Ingliz tilida — 7B coder modeli shunda barqarorroq ishlaydi;
vazifa matni esa istalgan tilda bo'lishi mumkin."""

SYSTEM_EDIT = """You are a senior software engineer working inside an existing repository. You make precise, minimal code changes.

How to answer:
1. In 1-3 sentences say what you will change.
2. Then write every change as a SEARCH/REPLACE block. The first line is the file path exactly as shown in the context:

app/users/service.py
<<<<<<< SEARCH
exact existing lines from the file
=======
new lines
>>>>>>> REPLACE

Rules:
- ALWAYS use SEARCH/REPLACE blocks. Never answer with a plain code block or a whole function without SEARCH/REPLACE markers.
- SEARCH must copy existing lines EXACTLY (indentation, comments, blank lines) from the code shown to you.
- Keep each SEARCH short: the lines that change plus 1-3 unchanged lines around them, so it is unique in the file.
- Never put "⋮..." into SEARCH: it marks code that was omitted and you cannot see.
- To create a new file, leave the SEARCH part empty.
- Use several blocks for several places. Edit only files shown to you, or create new files.
- Follow the repository's existing style, naming, imports and framework conventions.
- Most tasks need changes in only 1-2 files. Write blocks ONLY for files that really change; never repeat unchanged code.
- Do not touch unrelated code. No TODOs, no placeholders, no "rest of code" comments.
"""

# Namunaviy suhbat (few-shot): 7B model formatni quruq qoidadan ko'ra namunadan yaxshiroq o'rganadi
EXAMPLE = [
    {
        "role": "user",
        "content": """## Code

### lib/cart.py
```python
class Cart:
    def __init__(self):
        self.items = []

    def add(self, name, price):
        self.items.append((name, price))
```

## Task
Narx manfiy bo'lsa add() ValueError chiqarsin va savatdagi umumiy summani qaytaradigan total() metodini qo'sh.
""",
    },
    {
        "role": "assistant",
        "content": """I will validate the price in `add` and add a `total` method.

lib/cart.py
<<<<<<< SEARCH
    def add(self, name, price):
        self.items.append((name, price))
=======
    def add(self, name, price):
        if price < 0:
            raise ValueError("price must not be negative")
        self.items.append((name, price))

    def total(self):
        return sum(price for _, price in self.items)
>>>>>>> REPLACE
""",
    },
]

USER_EDIT = """{context}

{rules}## Task
{task}
"""

RULES = "## Project rules\n{rules}\n\n"

SPEC = """## Acceptance test (already written, it currently FAILS)
`{path}` — your change must make this test pass. Do NOT edit this test; change the code.
```
{code}
```

"""

RETRY_EDIT_FAILED = """## Your previous answer could not be applied
{problems}

That answer was discarded completely. The files above show their CURRENT content.
Write the change again as correct SEARCH/REPLACE blocks, copying SEARCH lines exactly from the files above.
"""

RETRY_VERIFY_FAILED = """## Your change was applied, but verification failed
Changes made so far (already in the files):
```diff
{diff}
```

`{step}` failed{command}:
```
{output}
```

The files above show their CURRENT (already changed) content. Do NOT repeat the changes that are already there.
Write only the SEARCH/REPLACE blocks that fix this error.
"""

NO_BLOCKS = """## Your previous answer contained no SEARCH/REPLACE blocks
Write the change as SEARCH/REPLACE blocks exactly in the required format.
"""
