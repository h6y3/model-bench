"""T32 -- reply with the JSON object and nothing else.

Mined from production cost data (professor_turing BL-108, 2026-10-21). A topic
resolver passes the model's reply straight to a JSON parser. In live runs the
first reply for a new topic routinely failed to parse, so every new topic paid
for a retry: twice the cost and twice the wait. A model that wraps the object
in a fence or a sentence of preamble is the expensive one here, however good
the content is.

The format check is a full match over the whole reply, on purpose; the
content check uses the lenient extractor so a fenced but correct answer fails
on format alone, for the reason it would fail in production.
"""
TASK = {
    "id": "T32",
    "title": "Return only the JSON object",
    "category": "strict-output",
    "prompt": (
        "You resolve a learner's request to topic keys for a tutoring app.\n"
        "Learner's existing topics: ml.gradient-descent, ml.data-preprocessing\n"
        "Request: \"I want to learn about the different forms of database "
        "normalization\"\n\n"
        "Reply with ONLY a JSON object of this shape, with one to three "
        "candidates, best first:\n"
        "{\"candidates\": [{\"topic_key\": \"<domain>.<topic>\", "
        "\"display_name\": \"...\", \"rationale\": \"...\"}]}\n"
        "Your reply is passed directly to JSON.parse. Any character outside "
        "the object, including markdown fences or a sentence before or after "
        "it, makes the parse fail."),
    "checkers": [
        {"type": "regex", "pattern": r"(?s)\s*\{.*\}\s*"},
        {"type": "json_asserts", "asserts": [
            {"path": "candidates.0.topic_key", "op": "contains", "value": "databas"},
        ]},
    ],
    "timeout_s": 120,
    "max_tokens": 3000,
    "judge": False,
}
