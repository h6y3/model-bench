"""T19 - the three-line contract, under an email that invites explanation.

A downstream parser reads line 1 as a routing decision and lines 2-3 as text
it files. A model that prefaces its answer, or explains its reasoning in
prose, is not merely verbose: the parser sees an unrecognised first line and
falls to its safe default, so the failure is silent and looks like a verdict.

This task is deliberately chatty and slightly emotional, because that is what
draws an explanation out of a model that follows the format on dry input.
Content is synthetic; the shape -- a friend reporting progress and asking for
nothing -- is taken from real mail that was triaged on 2026-09-04.
"""
EMAIL = (
    "From: friend@example.com\n"
    "Subject: Re: the trip\n\n"
    "Hi! Thank you so much for inviting me and for all the detail, I really "
    "appreciate it and I'm looking forward to meeting you. So far I'm still "
    "in the middle of buying insurance -- three companies have now told me "
    "they don't sell anything beyond 90 days, which is frustrating. I'll keep "
    "asking around and let you know how it goes. Hope you're well!\n"
)

TASK = {
    "id": "T19",
    "title": "Triage: hold the three-line contract on a chatty email",
    "category": "email-triage-format",
    "prompt": (
        "You are triaging one email for a busy executive who works from home.\n\n"
        + EMAIL +
        "\nAnswer with exactly three lines and nothing else. No preamble, no "
        "explanation, no blank lines.\n\n"
        "Line 1 is one word: drop, draft, or task. Say \"drop\" if nothing is "
        "left for him to DO; an email REPORTING progress on something is not "
        "a task.\n\n"
        "Line 2 is a Todoist title, or the single word \"none\" when line 1 is "
        "not \"task\".\n\n"
        "Line 3 is one sentence addressed to him as \"you\"."
    ),
    "checkers": [
        # Line 1 alone on its line. `^` without MULTILINE anchors to the start
        # of the answer, which is the point: a preamble fails here, and a
        # preamble is what makes the parser mis-read the verdict.
        {"type": "regex", "pattern": r"^\s*(drop|draft|task)\s*\n",
         "search": True, "case_insensitive": True},
        # Three lines means three. A model that writes a fourth is explaining.
        {"type": "length_max", "words": 60},
        {"type": "contains_none", "values": [
            "here is", "here's my", "based on", "i would", "explanation",
        ]},
    ],
    "timeout_s": 120,
    "max_tokens": 6000,
    "judge": False,
}
