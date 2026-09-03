TASK = {
    "id": "T01",
    "title": "Instruction precision",
    "category": "instruction-precision",
    "prompt": "Reply with exactly: OK\n\nThen, on a new line, write the word: BANANA",
    "checkers": [
        {"type": "exact", "value": "OK BANANA"},
    ],
    "timeout_s": 60,
    "max_tokens": 100,
    "judge": False,
}