"""T31 -- find the acceptance probe that cannot fail for the reason it claims.

Mined from a real acceptance plan (professor_turing BL-105, 2026-10-21). A
coding agent proposed running a "reuse guard" first, on an empty database, to
prove that a de-biased topic resolver still reuses a learner's existing topic.
With no history there is nothing to reuse: a resolver that never reuses
anything mints the same key and passes. The operator moved the probe after a
seeding step before the run.

The other probes are sound, and probe 4 deliberately looks like the risky one.
Graded positively: the first line names probe 1, and the reason has to touch
the missing history.
"""
PLAN = '''Acceptance plan, run in order against ONE learner on a fresh, empty database:

1. Reuse guard: type "I want to keep going on gradient descent, especially
   learning rates". Expect top candidate ml.gradient-descent, proving that a
   genuine continuation still reuses the learner's existing topic.
2. Seed: start and finish a session on ml.gradient-descent by typing the exact key.
3. Fast path: type the exact key ml.gradient-descent again. Expect it to be used
   directly with no model call.
4. Out of domain: type "database normalization". Expect a databases.* topic, not
   an existing ML topic, proving the resolver no longer stretches history keys.
'''

TASK = {
    "id": "T31",
    "title": "Spot the probe that cannot fail",
    "category": "test-validity",
    "prompt": (
        "A topic resolver turns a learner's free-text request into a topic "
        "key. A prompt change stops it from favouring the learner's existing "
        "topics. Review the acceptance plan below. Is there a probe that "
        "cannot fail for the reason it says it tests? Answer on the first "
        "line exactly `FLAW: <probe number>`, or `FLAW: NONE` if every probe "
        "is sound, then one sentence explaining why.\n\n" + PLAN),
    "checkers": [
        {"type": "regex", "pattern": r"(?m)\A\s*\**FLAW:\s*1\b", "search": True},
        {"type": "regex", "pattern": r"(?i)(histor|empty|no existing|nothing to reuse|fresh)",
         "search": True},
    ],
    "timeout_s": 120,
    "max_tokens": 3000,
    "judge": False,
}
