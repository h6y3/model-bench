TASK = {
    "id": "T09",
    "title": "sed one-liner",
    "category": "regex-tooling",
    "prompt": ("Write a POSIX sed one-liner that reads lines on stdin and converts every "
               "ISO date YYYY-MM-DD to MM/DD/YYYY. Reply with only the command in one "
               "fenced code block."),
    "checkers": [
        {"type": "exec_code", "lang": "bash", "cases": [
            {"args": [], "stdin": "due 2026-09-03 and 2027-01-15", "expect_exit": 0,
             "expect_stdout_contains": ["09/03/2026", "01/15/2027", "and"],
             "expect_stdout_not_contains": ["2026-09-03"]},
        ]},
    ],
    "timeout_s": 120,
    "max_tokens": 500,
    "judge": False,
}