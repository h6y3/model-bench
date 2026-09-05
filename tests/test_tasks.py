import unittest

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
    # exemplars) arrived 2026-09-04.
    def test_twentytwo_tasks(self):
        self.assertEqual(len(self.tasks), 23)

    def test_unique_ids_sequential(self):
        self.assertEqual([t["id"] for t in self.tasks],
                         [f"T{i:02d}" for i in range(1, 24)])

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