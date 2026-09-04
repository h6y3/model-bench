"""T21 - the same judgement with the rule NOT spelled out.

T17 and T20 enumerate the categories that count as finished ("a package
shipped, a payment applied, a receipt, a statement"). Every model tested on
2026-09-04 passed them, including the deliberately weak control -- which by
this suite's own doctrine means those tasks measure the prompt, not the model.

They were still worth writing: they pin the behaviour against a regression.
But the capability question underneath is different, and this task asks it.
Here the prompt states the PRINCIPLE and no examples. A model that needs the
list is one whose accuracy is really its prompt's accuracy, and shortening
that prompt -- or moving to a model with a smaller effective instruction
window -- would silently cost the behaviour.

Content synthetic; shape real.
"""
EMAIL = (
    "From: service@example-bank.com\n"
    "Subject: Your consent to share information with a third party\n\n"
    "We are letting you know that on September 1 we submitted a request on "
    "your behalf asking that your account information stop being shared with "
    "the app you disconnected. The change takes effect within 30 days.\n"
    "You can review your sharing settings at any time in online banking.\n"
)

TASK = {
    "id": "T21",
    "title": "Triage: actionability from the principle alone, no examples",
    "category": "email-triage-actionability",
    "prompt": (
        "Triage one email for a busy executive who works from home.\n\n"
        + EMAIL +
        "\nAnswer with exactly three lines and nothing else.\n\n"
        "Line 1 is one word: drop, draft, or task. The only question is "
        "whether anything is LEFT UNDONE that only he can do.\n\n"
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
