RAMBLE = ("So basically what happened is that the backup thing ran last night, I think "
          "around 02:00 or so, and it did its whole thing and there were no "
          "errors which was nice, and honestly I was worried because last time it "
          "failed halfway, but this time it went all the way through and finished "
          "cleanly, so the backup succeeded.")

TASK = {
    "id": "T10",
    "title": "Constrained rewrite",
    "category": "constrained-writing",
    "prompt": ("Rewrite the paragraph below in at most 25 words, no adjectives, keeping "
               "the exact time and the outcome. Reply with only the rewrite.\n\n" + RAMBLE),
    "checkers": [
        {"type": "length_max", "words": 27},
        {"type": "contains_all", "values": ["02:00"]},
    ],
    "timeout_s": 180,
    "max_tokens": 4000,
    "judge": True,
}