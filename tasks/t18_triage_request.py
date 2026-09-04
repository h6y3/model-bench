"""T18 - the real request, and a title that names it.

The other half of T17. A lane tuned only to drop is not useful; it has to keep
the one email in ten that needs something and SAY what that something is.

Modeled on the same 2026-09-04 failure. Titles were selected from a table of
eight canned phrases keyed on rule tags, so ten of twelve filed tasks read
"Reply by deadline" alike -- on a shipping notice, a bank consent notice, and
a travel agent asking for a document. A label chosen by a tag cannot name the
work, because the tag has not read the email. The banned list below is that
exact table: a model that emits one of those has produced a phrase that would
fit any email, which is the defect.
"""
EMAIL = (
    "From: agent@example-travel.com\n"
    "Subject: RE: December safari booking, 2 travellers\n\n"
    "Hello, that's good news. It is best to buy the insurance and pay one "
    "after the other, because you need to fill in a form with your passport "
    "details and it will ask for the policy provider and policy number.\n"
    "You can send me the flight details by Friday morning at the latest, as "
    "I am off next week.\n"
)

TASK = {
    "id": "T18",
    "title": "Triage: keep a real request and name it specifically",
    "category": "email-triage-actionability",
    "prompt": (
        "You are triaging one email for a busy executive who works from home.\n\n"
        + EMAIL +
        "\nAnswer with exactly three lines and nothing else.\n\n"
        "Line 1 is one word: drop, draft, or task.\n\n"
        'Say "drop" if nothing is left for him to DO.\n\n'
        'Say "draft" if writing a reply FINISHES this -- confirming, '
        "declining, acknowledging, or answering from what is already in the "
        "message.\n\n"
        'Say "task" if something is genuinely LEFT UNDONE that only he can '
        "do: sending someone a document or detail they asked him for, or work "
        "outside the mail client.\n\n"
        "Line 2 is the Todoist title. Write it as an instruction to him: "
        "start with a verb, name the specific thing and the specific person "
        "or company, at most twelve words. Never a phrase that would fit a "
        "different email.\n\n"
        "Line 3 is one sentence addressed to him as \"you\", saying who wants "
        "what."
    ),
    "checkers": [
        {"type": "regex", "pattern": r"^\s*task\b", "search": True,
         "case_insensitive": True},
        # The email names two deliverables. Either is a correct title; naming
        # neither means the title is generic.
        {"type": "regex", "pattern": r"flight|passport", "search": True,
         "case_insensitive": True},
        # The tag table that caused the incident. Any of these is a phrase
        # that would fit any email in the corpus.
        {"type": "contains_none", "values": [
            "reply by deadline", "confirm attendance", "review and approve",
            "reply needed", "review when free", "complete account action",
        ]},
    ],
    "timeout_s": 120,
    "max_tokens": 6000,
    "judge": False,
}
