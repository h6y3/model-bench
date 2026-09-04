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
        {"type": "contains_all", "values": ["range", "last"]},
        {"type": "length_max", "words": 100},
    ],
    "timeout_s": 180,
    "max_tokens": 4000,
    "judge": True,
}