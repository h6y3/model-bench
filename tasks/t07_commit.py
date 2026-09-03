DIFF = (" match/base.yml | 14 ++++++-------\n"
        "--- a/match/base.yml\n+++ b/match/base.yml\n"
        '-  - trigger: ":date"\n+  - trigger: ";;date"\n'
        '-  - trigger: ":time"\n+  - trigger: ";;time"\n'
        " (comment lines updated to match)")

TASK = {
    "id": "T07",
    "title": "Write a commit message",
    "category": "git",
    "prompt": ("Write ONE conventional-commit subject line (no body) for this diff. "
               "Reply with only the subject line.\n\n" + DIFF),
    "checkers": [
        {"type": "regex", "pattern": r"\w+(\([\w./-]+\))?!?: .{5,69}"},
        {"type": "contains_all", "values": ["trigger"]},
        {"type": "contains_none", "values": ["\n"]},
    ],
    "timeout_s": 120,
    "max_tokens": 100,
    "judge": False,
}