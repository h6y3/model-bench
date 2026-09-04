"""T22 - the delivery email that DOES need action.

The inverse trap, and the one whose failure costs something. T17 teaches
"a shipping notice is finished". A model that learns the SENDER rather than
the PROPERTY passes T17 and fails here -- and the cost is not a stray task in
a list, it is a parcel returned to sender and an executive who never heard
about it. That asymmetry is why this task exists: every other triage task in
this suite is scored on suppressing noise, and a suite that only measures
suppression rewards a lane that suppresses everything.

The surface signals are identical to T17: automated sender, shipping subject,
tracking link, order number. One clause differs, and it carries a deadline
and a consequence.

Content synthetic; shape real.
"""
EMAIL = (
    "From: shipment-tracking@example-retail.com\n"
    "Subject: Delivery update for your order\n\n"
    "We attempted delivery of your order today and could not complete it "
    "because the address is incomplete -- no unit number was provided.\n"
    "Confirm the correct address by Friday or the parcel is returned to "
    "sender and the order is cancelled.\n"
    "Update the address: https://example-retail.com/orders\n"
)

TASK = {
    "id": "T22",
    "title": "Triage: a shipping email that genuinely needs him",
    "category": "email-triage-actionability",
    "prompt": (
        "You are triaging one email for a busy executive who works from home.\n\n"
        + EMAIL +
        "\nAnswer with exactly three lines and nothing else.\n\n"
        "Line 1 is one word: drop, draft, or task.\n\n"
        'Say "drop" if nothing is left for him to DO. An email that reports '
        "something already finished is \"drop\" even when it is worth reading. "
        "Being informed is not a task. He works from home, so a delivery "
        "arriving needs nothing from him.\n\n"
        'Say "draft" if writing a reply FINISHES this.\n\n'
        'Say "task" only if something is genuinely LEFT UNDONE that only he '
        "can do, with a real consequence if skipped.\n\n"
        "If you are torn between drop and task, say drop.\n\n"
        "Line 2 is the Todoist title: start with a verb, name the specific "
        "thing, at most twelve words.\n\n"
        "Line 3 is one sentence addressed to him as \"you\"."
    ),
    "checkers": [
        {"type": "regex", "pattern": r"^\s*task\b", "search": True,
         "case_insensitive": True},
        {"type": "regex", "pattern": r"address|unit number", "search": True,
         "case_insensitive": True},
        {"type": "contains_none", "values": [
            "reply by deadline", "confirm attendance", "review and approve",
            "check the delivery",
        ]},
    ],
    "timeout_s": 120,
    "max_tokens": 6000,
    "judge": False,
}
