PACKAGES = (
    "pi-packs  installed 1.2.0  required ^1.3.0\n"
    "pi-linter installed 0.9.4  required ^0.9.4\n"
    "pi-bar    installed 2.0.1  required ^2.1.0\n"
    "pi-qq     installed 0.3.0  required ^0.3.0"
)

TASK = {
    "id": "T11",
    "title": "Reconcile package versions",
    "category": "dependency-reconcile",
    "prompt": ("Given this installed-vs-required package listing, return ONLY a JSON object "
               '{"needs_update": ["<package name>", ...], "count": <number of packages needing update>} '
               "listing packages whose installed version does not satisfy the required range. No prose.\n\n" + PACKAGES),
    "checkers": [
        {"type": "json_asserts", "asserts": [
            {"path": "needs_update", "op": "eq", "value": ["pi-packs", "pi-bar"]},
            {"path": "count", "op": "eq", "value": 2},
        ]},
    ],
    "timeout_s": 120,
    "max_tokens": 4000,
    "judge": False,
}