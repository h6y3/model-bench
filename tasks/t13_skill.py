TASK = {
    "id": "T13",
    "title": "Author a skill frontmatter",
    "category": "skill-authoring",
    "prompt": ("Write the YAML frontmatter block (between --- fences, nothing else) for a "
               "pi skill named \"send-to-drafts\". The description must contain the trigger "
               "phrases \"send to drafts\" and \"note to me\" so a model can match user intent."),
    "checkers": [
        {"type": "contains_all", "values": ["---", "name: send-to-drafts", "description:", "send to drafts", "note to me"]},
        {"type": "regex", "pattern": r"(?s)^---\n(name|description):.*\n---\s*$"},
    ],
    "timeout_s": 120,
    "max_tokens": 4000,
    "judge": False,
}