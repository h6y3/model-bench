"""T23 - can the model infer a voice from examples and hold it?

Every other task in this suite STATES its rule in the prompt, which is why
T17-T22 were passed by all four models and by the deliberately weak control:
they measure careful reading. This one states the convention only by example.

Modeled on a live personal-assistant lane that drafts replies in its owner's
voice. Every exemplar here is invented; no real correspondence is used.
"""
EXEMPLARS = """Hi, Priya.

Yes, ship it Monday. The dock closes at four.

Han

---

Hi, Marcus.

No. The Q2 numbers are not final until audit signs off.

Han

---

Hi, Dana.

Both work. Take the earlier one.

Han"""

TASK = {
    "id": "T23",
    "title": "Match a voice inferred from examples",
    "category": "voice-matching",
    "prompt": (
        "Below are three emails one person wrote. Study how they write.\n\n"
        + EXEMPLARS +
        "\n\nNow write their next email, in the same voice.\n\n"
        "Situation: Dana asked which day the crew should come and where "
        "they should unload. The crew is coming Thursday. They should "
        "unload at the loading dock.\n\n"
        "Write only the email."
    ),
    "checkers": [
        # Models pad. The most reliable discriminator between tiers.
        {"type": "length_max", "words": 60},
        # Answering without answering.
        {"type": "contains_all", "values": ["Thursday", "loading dock"]},
        # The exemplars forbid this register; obeying them IS the skill.
        {"type": "contains_none", "values": [
            "hope this finds you", "looking forward", "don't hesitate",
            "please feel free", "warm regards", "best regards",
        ]},
        # Invention -- the failure that produced a fabricated serial number
        # in a real draft on 2026-08-30. The brief never states a time, so a
        # reply naming one made it up.
        {"type": "contains_none", "values": ["9am", "9:00", "10am", "10:00"]},
        # The structural convention, inferable only from the exemplars.
        {"type": "regex", "pattern": r"^Hi, [A-Z][a-z]+\.", "search": True},
    ],
    "timeout_s": 120,
    "max_tokens": 6000,
    "judge": True,
}
