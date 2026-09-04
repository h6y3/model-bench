"""T20 - the notice dressed as a request.

The discriminating case, and the reason T17 alone is not enough. T17's parcel
notice can be dropped by pattern-matching the sender as machine-generated.
This one cannot: the subject says "Action Required", the body says "review",
the sender is a real financial institution, and there is a date. Every
surface signal says act. The only thing that says otherwise is the verb tense
-- the payment has ALREADY been applied -- which requires reading rather than
matching.

A trained importance classifier scored the real version of this at
p(important) = 0.9970 and it was filed as a task. A model that drops T17 and
files T20 has learned "ignore robots", not "ignore what is finished".

Content is synthetic; the shape is real.
"""
EMAIL = (
    "From: notifications@example-mortgage.com\n"
    "Subject: Action Required: your payment has been applied\n\n"
    "Review your payment details.\n"
    "On September 3 we applied your scheduled monthly payment of $2,140.00 "
    "to your loan. No further action is needed to complete this payment.\n"
    "Review the details in your account: https://example-mortgage.com/account\n"
    "If you did not authorise this payment, contact us within 60 days.\n"
)

TASK = {
    "id": "T20",
    "title": "Triage: a completed action wearing an urgent subject line",
    "category": "email-triage-actionability",
    "prompt": (
        "You are triaging one email for a busy executive who works from home.\n\n"
        + EMAIL +
        "\nAnswer with exactly three lines and nothing else.\n\n"
        "Line 1 is one word: drop, draft, or task.\n\n"
        'Say "drop" if nothing is left for him to DO. An email that reports '
        "something already finished is \"drop\" even when the subject line "
        "says action is required and even when it says \"review\". Being "
        "informed is not a task.\n\n"
        'Say "draft" if writing a reply FINISHES this.\n\n'
        'Say "task" only if something is genuinely LEFT UNDONE that only he '
        "can do, with a real consequence if skipped.\n\n"
        "If you are torn between drop and task, say drop.\n\n"
        "Line 2 is a Todoist title, or the single word \"none\" when line 1 is "
        "not \"task\".\n\n"
        "Line 3 is one sentence addressed to him as \"you\"."
    ),
    "checkers": [
        {"type": "regex", "pattern": r"^\s*drop\b", "search": True,
         "case_insensitive": True},
        {"type": "length_max", "words": 80},
    ],
    "timeout_s": 120,
    "max_tokens": 6000,
    "judge": False,
}
