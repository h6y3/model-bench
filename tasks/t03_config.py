BROKEN = """matches:
  - triger: ":date"
    word: true
    replace: "{{d}}"
      vars:
      - name: d
        type: date
    word: true
"""

TASK = {
    "id": "T03",
    "title": "Fix broken YAML config",
    "category": "config-edit",
    "prompt": (
        "This espanso match has three errors: a misspelled key, a mis-indented "
        "block, and a duplicated key. The trigger must be the string \";;date\". "
        "Output ONLY the corrected YAML, nothing else.\n\n" + BROKEN
    ),
    "checkers": [
        {"type": "contains_all", "values": ['trigger: ";;date"', "word: true"]},
        {"type": "contains_none", "values": ["triger", "\t"]},
        {"type": "regex", "pattern": r"(?s)^matches:.*replace:.*type: date.*$", "search": True},
    ],
    "timeout_s": 120,
    "max_tokens": 600,
    "judge": False,
}