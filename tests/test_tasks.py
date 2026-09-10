import re
import unittest
from pathlib import Path

from tasks import load_tasks

REQUIRED = {"id", "title", "category", "prompt", "checkers", "timeout_s", "max_tokens", "judge"}
VALID_TYPES = {"exact", "contains_all", "contains_none", "regex",
               "json_asserts", "length_max", "length_min", "exec_code"}


class TestTasks(unittest.TestCase):
    def setUp(self):
        self.tasks = load_tasks()

    # Explicit, not derived from the directory: a count read off the files it
    # is checking cannot notice a task that failed to load, and a range read
    # off len() cannot notice a gap. Bump both deliberately when adding a task.
    # T17-T22 (email triage) arrived 2026-09-04. T23 (voice matching from
    # exemplars) arrived 2026-09-04. T24-T27 (subagent fitness) arrived
    # 2026-09-10, after the existing suite SATURATED: four candidates for the
    # subagent chain all scored 1.00 on a coding task, so the suite ranked them
    # by latency and tokens and said nothing about judgement. The four new
    # tasks target what actually makes a delegated agent dangerous -- reporting
    # work that did not happen, inventing a fact absent from its context,
    # expanding its own scope, and editing a shared dependency to satisfy a
    # local fix.
    def test_twentyseven_tasks(self):
        self.assertEqual(len(self.tasks), 27)

    def test_unique_ids_sequential(self):
        self.assertEqual([t["id"] for t in self.tasks],
                         [f"T{i:02d}" for i in range(1, 28)])

    # ⚠️ THE README'S COUNT IS A CLAIM ABOUT THIS SUITE AND NOTHING CHECKED IT
    # (added 2026-09-10). It had drifted THREE ways at once: the header said
    # 27, the "why" bullet said 22, and the `--list` comment said 16 -- because
    # adding tasks means editing the table, and whoever does that fixes the
    # number they are looking at. Provenance sentences about the ORIGINAL 16
    # are deliberately not matched here: they are history and stay true.
    def test_readme_states_the_real_task_count(self):
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text()
        m = re.search(r"^## The suite: (\d+) tasks", readme, re.M)
        self.assertIsNotNone(m, "README lost its '## The suite: N tasks' header")
        self.assertEqual(int(m.group(1)), len(self.tasks),
                         "README suite header disagrees with tasks/")

    # The header and the table can drift apart independently: bumping the
    # number without adding a row reads as done and is not.
    def test_readme_table_lists_every_task_exactly_once(self):
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text()
        rows = re.findall(r"^\| (T\d{2}) \|", readme, re.M)
        self.assertEqual(rows, [t["id"] for t in self.tasks],
                         "README suite table does not match tasks/ in ids or order")

    def test_required_keys(self):
        for t in self.tasks:
            missing = REQUIRED - set(t)
            self.assertFalse(missing, f"{t['id']} missing {missing}")
            self.assertGreater(len(t["prompt"]), 40, t["id"])
            self.assertTrue(t["checkers"], t["id"])

    def test_checker_types_valid(self):
        for t in self.tasks:
            for c in t["checkers"]:
                self.assertIn(c.get("type"), VALID_TYPES, f"{t['id']}: {c}")

    def test_judge_tasks(self):
        flagged = {t["id"] for t in self.tasks if t.get("judge")}
        self.assertEqual(flagged, {"T06", "T08", "T10", "T16", "T23"})


if __name__ == "__main__":
    unittest.main()