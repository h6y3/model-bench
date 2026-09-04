"""T17 - the notification that everything calls important.

Modeled on a live failure, 2026-09-04: a personal-email triage lane filed
eleven useless tasks in six days because the trained priority classifier
gating it scored shipping notices at p(important) = 0.9994. The classifier was
right about its own question -- the owner does read those mails -- and useless
for the question actually being asked. "Worth reading" and "needs doing" are
different axes, and this task measures the second one.

Content here is synthetic. The structure is not: a completed action, a link
that reads like an instruction ("Track your package"), and no request.
"""
EMAIL = (
    "From: shipment-tracking@example-retail.com\n"
    "Subject: Shipped: 3 Candy, Tools, and other items\n\n"
    "Your order has shipped and is expected to arrive Friday.\n"
    "Track your package: https://example-retail.com/orders\n"
    "Manage your account: https://example-retail.com/account\n"
)

TASK = {
    "id": "T17",
    "title": "Triage: a completed-action notice needs no action",
    "category": "email-triage-actionability",
    "prompt": (
        "You are triaging one email for a busy executive who works from home.\n\n"
        + EMAIL +
        "\nAnswer with exactly three lines and nothing else.\n\n"
        "Line 1 is one word: drop, draft, or task.\n\n"
        'Say "drop" if nothing is left for him to DO. An email that reports '
        "something already finished is \"drop\" even when it is worth reading "
        "and even when it links to an account page. Being informed is not a "
        "task. He works from home, so a delivery arriving needs nothing from "
        "him.\n\n"
        'Say "draft" if writing a reply FINISHES this.\n\n'
        'Say "task" only if something is genuinely LEFT UNDONE that only he '
        "can do.\n\n"
        "Line 2 is a Todoist title, or the single word \"none\" when line 1 is "
        "not \"task\".\n\n"
        "Line 3 is one sentence addressed to him as \"you\"."
    ),
    "checkers": [
        {"type": "regex", "pattern": r"^\s*drop\b", "search": True,
         "case_insensitive": True},
        # A model that drops for the wrong reason -- because it judged the
        # sender promotional rather than the action complete -- gets the same
        # verdict here and a different one on T20. Checked there, not here.
        {"type": "length_max", "words": 80},
    ],
    "timeout_s": 120,
    "max_tokens": 6000,
    "judge": False,
}
