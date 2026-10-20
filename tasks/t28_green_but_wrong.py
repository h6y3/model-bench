"""T28 -- review a pull request that is green and fixes the reported bug, but is wrong.

The diff fixes the bug report exactly, and CI passes, because the existing
tests never exercise the pre-release half of the documented contract. The
contract is in the docstring the diff leaves in place: `-rcN` pre-releases,
older than the release they precede. The diff crashes on every one of them.

This is the verifier's job and the one a rubber stamp fails: the evidence a
reviewer is handed (bug fixed, CI green) all says approve, and the reason to
reject is in the spec, not in a failing test. Added 2026-10-20, after the
T08/T14 regrade left every recorded model passing the suite's only
code-review tasks.

Graded positively throughout. The verdict line must say REQUEST CHANGES, and
the corrected file is executed: the reported case, release-vs-rc in both
directions, rc-vs-rc, and rc10-vs-rc9, which a fix that compares the suffix as
a string gets wrong. Every case asserts an exact required output.

⚠️ MEASURED A UNIVERSAL PASS -- A REGRESSION PIN, NOT A DISCRIMINATOR.
2026-10-20, glm-5.3-flash / minimax-m3.1-flash / gemma4:31b (control), three
serial repeats each, twice: with a prompt pointing at "the documented
behaviour", 9/9; without it, 8/9, the one miss glm-5.3-flash spending all
6000 tokens reasoning and answering nothing. Every model, control included,
rejected the PR and wrote a correct integer rc parser; nobody fell for
rc10-vs-rc9. A contract visible in the reviewed file is not hard enough to
separate these models. It stays to catch a model that starts approving green
PRs; do not choose between candidates on it.
"""
SOURCE = '''import sys

def is_newer(a, b):
    """True if version a is strictly newer than version b.

    Versions are MAJOR.MINOR.PATCH, optionally followed by a pre-release
    suffix -rcN where N is a positive integer (e.g. 2.0.0-rc1). A pre-release
    is older than the release it precedes: 2.0.0-rc1 < 2.0.0-rc2 < 2.0.0.
    """
    return tuple(int(x) for x in a.split(".")) > tuple(int(x) for x in b.split("."))

if __name__ == "__main__":
    print("RESULT:%s" % is_newer(sys.argv[1], sys.argv[2]))
'''

DIFF = '''-    return a > b
+    return tuple(int(x) for x in a.split(".")) > tuple(int(x) for x in b.split("."))'''

TESTS = '''def test_reported_bug():
    assert is_newer("1.10.0", "1.9.0")

def test_equal_is_not_newer():
    assert not is_newer("1.2.3", "1.2.3")'''


def _case(a, b, want):
    return {"args": [a, b], "expect_exit": 0,
            "expect_stdout_contains": ["RESULT:%s" % want]}


TASK = {
    "id": "T28",
    "title": "Review a green PR that is still wrong",
    "category": "code-review",
    "prompt": (
        "You are reviewing a pull request.\n\n"
        "Bug report: `is_newer(\"1.10.0\", \"1.9.0\")` returns False; it should "
        "return True.\n\n"
        "The PR changes one line of `is_newer`:\n```diff\n" + DIFF + "\n```\n\n"
        "CI is green. These are the project's tests for this function, all "
        "passing:\n```python\n" + TESTS + "\n```\n\n"
        "The file after the PR:\n```python\n" + SOURCE + "```\n\n"
        # No pointer at the docstring: the first draft said "review against the
        # documented behaviour" and the control passed 3/3 (2026-10-20).
        "Review the PR. The first "
        "line of your reply must be exactly `VERDICT: APPROVE` or "
        "`VERDICT: REQUEST CHANGES`. If you request changes, give one sentence "
        "saying why, then the complete corrected file in one fenced Python "
        "block, keeping the `__main__` block unchanged."),
    "checkers": [
        {"type": "regex", "pattern": r"^\W*VERDICT: REQUEST CHANGES", "search": True},
        {"type": "exec_code", "lang": "python", "cases": [
            _case("1.10.0", "1.9.0", True),        # the reported bug
            _case("1.2.3", "1.2.3", False),
            _case("2.0.0", "2.0.0-rc1", True),     # release beats its pre-release
            _case("2.0.0-rc1", "2.0.0", False),
            _case("2.0.0-rc2", "2.0.0-rc1", True),
            _case("2.0.0-rc10", "2.0.0-rc9", True),  # N is an integer, not a string
            _case("2.0.0-rc1", "1.9.9", True),     # a pre-release still beats an older release
        ]},
    ],
    "timeout_s": 180,
    "max_tokens": 6000,
    "judge": False,
}
