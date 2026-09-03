SNIPPET = (
    "models.json schema rule: the schema requires EVERY cost block to contain all four "
    "keys - input, output, cacheRead, cacheWrite - and any schema error rejects the whole file.\n\n"
    "models.json (one of eight models):\n"
    '"cost": { "input": 0.15, "output": 0.50, "cacheRead": 0.03 }\n\n'
    'settings.json: { "defaultModel": "glm-5.3-flash:cloud", "defaultProvider": "ollama" }\n\n'
    "Symptom: unrelated Gemini 429 RESOURCE_EXHAUSTED quota errors, even though the "
    "config never mentions Gemini."
)

TASK = {
    "id": "T12",
    "title": "Diagnose config schema rejection",
    "category": "config-schema-diagnosis",
    "prompt": ("A coding agent silently fell back to the wrong provider. Given the schema "
               "rule, config snippet, and symptom, explain in at most 80 words which missing "
               "key causes the failure, why the symptom is Gemini-related, and what value "
               "fixes it.\n\n" + SNIPPET),
    "checkers": [
        {"type": "contains_all", "values": ["cachewrite", "fall"]},
        {"type": "contains_none", "values": ["gemini quota", "rate limit bug"]},
        {"type": "length_max", "words": 110},
    ],
    "timeout_s": 180,
    "max_tokens": 8000,
    "judge": False,
}