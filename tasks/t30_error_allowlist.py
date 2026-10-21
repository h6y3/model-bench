"""T30 -- the friendly error is an allowlist, not whatever is left over.

Mined from a real first-run failure (professor_turing, 2026-10-20). A learner
with no working key typed a topic and was told "Couldn't make sense of that",
so they rephrased instead of fixing the key. The code special-cased one
provider error and sent everything else to the friendly retry, which hides
every failure nobody had thought to list.

The tempting fix extends the special case with more provider codes. Cases 2
and 3 use codes the prompt never names, so only a fix that inverts the rule
(friendly for the three named no-match codes, honest for everything else)
passes. Case 0 is the control that a genuine no-match stays friendly.
"""
SOURCE = '''import sys

FRIENDLY = "Couldn't make sense of that. Try again, or type a topic key."

def launch_message(code, detail):
    """Text shown to the learner when topic resolution fails."""
    if code == "TUTOR_PROVIDER_UNAVAILABLE":
        return "Can't reach your tutor provider (%s: %s)." % (code, detail)
    return FRIENDLY

if __name__ == "__main__":
    print("MSG:" + launch_message(sys.argv[1], sys.argv[2]))
'''

TASK = {
    "id": "T30",
    "title": "Make the friendly error an allowlist",
    "category": "error-classification",
    "prompt": (
        "A learner whose API key had expired typed a topic, saw \"Couldn't make "
        "sense of that\", and spent ten minutes rephrasing. The friendly "
        "message is meant only for failures where resolution ran and found no "
        "usable match: NO_CANDIDATES, VALIDATION_ERROR and LLM_PARSE_ERROR. "
        "Every other failure, including codes that do not exist yet, must show "
        "the provider message in its existing format with the code and "
        "detail. Fix `launch_message`. Return the complete file in one fenced "
        "Python block.\n\n" + SOURCE),
    "checkers": [
        {"type": "exec_code", "lang": "python", "cases": [
            {"args": ["VALIDATION_ERROR", "no valid candidates"], "expect_exit": 0,
             "expect_stdout_contains": ["MSG:Couldn't make sense of that"]},
            {"args": ["TUTOR_PROVIDER_UNAVAILABLE", "no key"], "expect_exit": 0,
             "expect_stdout_contains": ["(TUTOR_PROVIDER_UNAVAILABLE: no key)"]},
            # Never named in the prompt: only an inverted rule gets these right.
            {"args": ["E_UPSTREAM_502", "bad gateway"], "expect_exit": 0,
             "expect_stdout_contains": ["(E_UPSTREAM_502: bad gateway)"]},
            {"args": ["QUOTA_WINDOW_SPENT", "try later"], "expect_exit": 0,
             "expect_stdout_contains": ["(QUOTA_WINDOW_SPENT: try later)"]},
        ]},
    ],
    "timeout_s": 180,
    "max_tokens": 4000,
    "judge": False,
}
