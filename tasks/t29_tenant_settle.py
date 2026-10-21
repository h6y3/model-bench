"""T29 -- parked cost must settle only into the session of the learner who caused it.

Mined from a real review (professor_turing BL-105, 2026-10-21). A tutor core
parks the cost of model calls made before any session exists and folds it into
the next session that starts. The code took every parked row, whoever caused
it, which is harmless for one learner on one machine and a billing leak the
moment two learners share a server. The reviewer caught it by reading the
settle function, not from a failing test.

Graded by execution, positively. Case 0 is the discriminator: B starts first,
so a fix that filters by student but clears the whole queue loses A's rows,
and A's session then reports rows=0 instead of rows=2. Case 1 is the control
that a learner's later session gets nothing twice.

MEASURED A UNIVERSAL PASS -- A REGRESSION PIN, NOT A DISCRIMINATOR.
2026-10-21, glm-5.3-flash / deepseek-v4.1-flash / gemma4:31b (control), three
runs each: every model passed. The catch was hard for a builder deep in a long
session; posed alone and single-turn it is easy. Keep it to catch a model that
starts failing it; do not choose between candidates on it.
"""
SOURCE = '''import sys

class Core:
    def __init__(self):
        self.pending = []   # cost rows parked before a session exists
        self.sessions = {}  # session_id -> {"student", "cost", "rows"}

    def park(self, student, cost):
        """Record cost that `student` caused before any session existed."""
        self.pending.append({"cost": cost})

    def start_session(self, session_id, student):
        entry = {"student": student, "cost": 0.0, "rows": []}
        self.sessions[session_id] = entry
        self.settle(entry)
        return entry

    def settle(self, entry):
        """Attach parked cost to the session that just started."""
        parked = self.pending[:]
        self.pending.clear()
        for row in parked:
            entry["rows"].append(row)
            entry["cost"] += row["cost"]

if __name__ == "__main__":
    core = Core()
    for op in sys.argv[1:]:
        kind, a, b = op.split(":")
        if kind == "park":
            core.park(a, float(b))
        else:
            e = core.start_session(a, b)
            print("SESSION %s %s rows=%d cost=%.3f" % (a, b, len(e["rows"]), e["cost"]))
'''

TASK = {
    "id": "T29",
    "title": "Settle parked cost only into the owner's session",
    "category": "tenant-isolation",
    "prompt": (
        "This tutor core is about to run on a shared server for many learners. "
        "Cost that a learner causes before their session exists is parked and "
        "then attached when a session starts. Fix the code so parked cost is "
        "attached only to a session belonging to the same learner who caused "
        "it. Another learner's parked rows must stay parked until that "
        "learner's own next session, and every row a learner parked must land "
        "in their next session. Leave the `__main__` block and its output "
        "format unchanged. Return the complete file in one fenced Python "
        "block.\n\n" + SOURCE),
    "checkers": [
        {"type": "exec_code", "lang": "python", "cases": [
            # The leak: B must not absorb A's rows, and A must get both later.
            {"args": ["park:A:0.010", "park:A:0.020", "park:B:0.050",
                      "start:s1:B", "start:s2:A"], "expect_exit": 0,
             "expect_stdout_contains": ["SESSION s1 B rows=1 cost=0.050",
                                        "SESSION s2 A rows=2 cost=0.030"]},
            # Control: settled rows are consumed, not attached twice.
            {"args": ["park:A:0.010", "start:s1:A", "start:s2:A"], "expect_exit": 0,
             "expect_stdout_contains": ["SESSION s1 A rows=1 cost=0.010",
                                        "SESSION s2 A rows=0 cost=0.000"]},
        ]},
    ],
    "timeout_s": 180,
    "max_tokens": 4000,
    "judge": False,
}
