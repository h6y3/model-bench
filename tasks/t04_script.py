TASK = {
    "id": "T04",
    "title": "Write a small bash script",
    "category": "script-writing",
    "prompt": ("Write a bash script that prints the number of command-line arguments "
               "passed to it (just the number, nothing else). Reply with the script "
               "in a single fenced code block."),
    "checkers": [
        {"type": "exec_code", "lang": "bash", "cases": [
            {"args": ["a", "b", "c"], "expect_exit": 0, "expect_stdout_contains": ["3"]},
            {"args": [], "expect_exit": 0, "expect_stdout_contains": ["0"]},
        ]},
    ],
    "timeout_s": 120,
    "max_tokens": 4000,
    "judge": False,
}