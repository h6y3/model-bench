"""T27 -- fix one caller of a shared helper without breaking the other.

The tempting fix is inside `normalize`, which is shared. Doing it there makes
`slug` correct and silently breaks `label`, and nothing in the prompt points at
`label` as something to check -- the model has to notice the dependency itself.

This is the axis a latency benchmark cannot reach, and the one that matters most
for delegated work: a subagent that edits a shared function to satisfy its own
task hands back a change whose damage is somewhere it never looked.

⚠️ Purely BEHAVIOURAL, with no text assertion about the helper. Both cases
assert an exact required output, so a model that edits `normalize` fails on the
`label` case by consequence rather than by inspection -- which is stronger than
a regex over the helper's body, and cannot be satisfied by omitting anything.
"""
SOURCE = '''import sys

def normalize(s):
    """Shared by both callers below."""
    return s.strip()

def slug(raw):
    """A URL slug: lowercase, words joined by single hyphens."""
    return normalize(raw)

def label(raw):
    """A display label: trimmed, but otherwise exactly as the user typed it."""
    return normalize(raw)

if __name__ == "__main__":
    mode, value = sys.argv[1], sys.argv[2]
    print(("SLUG:" if mode == "slug" else "LABEL:") +
          (slug(value) if mode == "slug" else label(value)))
'''

TASK = {
    "id": "T27",
    "title": "Fix one caller of a shared helper",
    "category": "shared-dependency-reasoning",
    "prompt": (
        "`slug` is wrong: for the input \"  Hello World  \" it returns "
        "\"Hello World\" when it should return \"hello-world\".\n\n"
        "Fix `slug`. Every other function must keep its current behaviour for "
        "every input -- `label` in particular is correct as written and must "
        "stay correct. Return the complete file in one fenced Python block.\n\n"
        + SOURCE),
    "checkers": [
        {"type": "exec_code", "lang": "python", "cases": [
            {"args": ["slug", "  Hello World  "], "expect_exit": 0,
             "expect_stdout_contains": ["SLUG:hello-world"]},
            # The separator: `label` must be untouched in effect. A model that
            # fixed `slug` by editing the shared `normalize` fails here.
            {"args": ["label", "  Hello World  "], "expect_exit": 0,
             "expect_stdout_contains": ["LABEL:Hello World"]},
        ]},
    ],
    "timeout_s": 180,
    "max_tokens": 4000,
    "judge": False,
}
