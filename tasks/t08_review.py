SNIPPET = ('```python\n'
           'import os\n'
           'def summarize(rows):\n'
           '    out = []\n'
           '    for i in range(len(rows) - 1):\n'
           '        out.append(rows[i]["name"])\n'
           '    return out\n'
           '```')

TASK = {
    "id": "T08",
    "title": "Find the bug",
    "category": "code-review",
    "prompt": ("Review this snippet. Name the bug class and what it does to the output, "
               "in at most 80 words.\n\n" + SNIPPET),
    "checkers": [
        # Grade the two things the prompt asks for, the bug class and what it
        # does to the output, in any wording. This used to require the literal
        # words "range" and "last": the prompt asks for neither, and it failed
        # correct answers saying "the final row" or never quoting the loop
        # (2026-10-20 regrade of every stored answer).
        # \W, not [- ]: models write U+2011 non-breaking hyphens ("off‑by‑one").
        {"type": "regex", "pattern": r"off\W{0,2}by\W{0,2}one|fencepost", "search": True,
         "case_insensitive": True},
        {"type": "regex", "pattern": r"\b(last|final)\b", "search": True,
         "case_insensitive": True},
        {"type": "length_max", "words": 100},
    ],
    "timeout_s": 180,
    "max_tokens": 4000,
    "judge": True,
}