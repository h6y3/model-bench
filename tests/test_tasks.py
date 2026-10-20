import re
import unittest
from pathlib import Path

from lib.checks import run_checks
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
    # local fix. T28 (review a green PR that is still wrong) arrived
    # 2026-10-20, when regrading T08/T14 left every recorded model passing the
    # suite's only code-review tasks.
    def test_twentyeight_tasks(self):
        self.assertEqual(len(self.tasks), 28)

    def test_unique_ids_sequential(self):
        self.assertEqual([t["id"] for t in self.tasks],
                         [f"T{i:02d}" for i in range(1, 29)])

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

    # Graders checked against REAL answers, not just for shape. Both fixtures
    # below are verbatim minimax-m3.1-flash answers from 2026-10-20 runs that
    # were correct and scored as failures.
    def _grade(self, tid, answer):
        task = next(t for t in self.tasks if t["id"] == tid)
        return all(c["passed"] for c in run_checks(answer, task["checkers"]))

    # T14 used to ban the string "omarchy-plugin install". The prompt asks WHY
    # the user's command failed, so a correct answer quotes it -- the ban
    # failed every model that did (5/5 minimax-m3.1-flash trials, gemma4, and
    # minimax-m3's only miss on 2026-10-08) and passed whoever happened to
    # write "`install`" alone. A negated assertion graded phrasing.
    def test_t14_passes_a_correct_answer_that_quotes_the_failed_command(self):
        answer = ("```bash\nomarchy-plugin add https://github.com/example/widget.git --enable\n```\n\n"
                  "The command failed because the legacy `omarchy-plugin install` command was "
                  "removed in version 2.0. The README specifies `add` followed by the Git URL "
                  "and `--enable`.")
        self.assertTrue(self._grade("T14", answer))

    def test_t14_fails_an_answer_that_recommends_install(self):
        answer = ("Run `omarchy-plugin install --force https://github.com/example/widget.git`; "
                  "the legacy command was removed in 2.0 and needs --force now.")
        self.assertFalse(self._grade("T14", answer))

    def test_t14_fails_a_command_without_the_reason(self):
        answer = "omarchy-plugin add https://github.com/example/widget.git --enable"
        self.assertFalse(self._grade("T14", answer))

    # T08 required the literal words "range" and "last"; "omits the final
    # row" is the same finding and failed, as did correct answers that never
    # quoted the loop.
    def test_t08_accepts_final_as_well_as_last(self):
        answer = ("**Bug class:** Off-by-one error.  \n**Effect:** `range(len(rows) - 1)` "
                  "omits the final row, so the output contains names for only the first "
                  "`len(rows) - 1` rows.")
        self.assertTrue(self._grade("T08", answer))

    def test_t08_passes_without_quoting_the_loop(self):
        answer = ("**Bug Class:** Off-by-one error.\n\n**Effect:** The function fails to "
                  "process the final element of the `rows` list, resulting in an output "
                  "list that is missing the last entry.")
        self.assertTrue(self._grade("T08", answer))

    def test_t08_accepts_non_breaking_hyphens(self):
        answer = ("**Bug class:** off\u2011by\u2011one iteration error.  \n**Effect:** the loop "
                  "stops before the last row, so the final entry is omitted.")
        self.assertTrue(self._grade("T08", answer))

    def test_t08_fails_without_the_bug_class(self):
        answer = "The loop skips the last row, so one name is missing from the output."
        self.assertFalse(self._grade("T08", answer))

    def test_t08_fails_when_the_dropped_element_is_not_named(self):
        answer = "Off-by-one error in `range(len(rows) - 1)`; the output is wrong."
        self.assertFalse(self._grade("T08", answer))

    # T28's grader, validated before any model saw it: the reference fix
    # passes, and each plausible wrong review fails for its own reason.
    T28_HEAD = "VERDICT: REQUEST CHANGES\nIt crashes on the documented -rcN versions.\n\n"
    T28_MAIN = ('if __name__ == "__main__":\n'
                '    print("RESULT:%s" % is_newer(sys.argv[1], sys.argv[2]))\n')

    def _t28(self, body, head=None):
        return ((self.T28_HEAD if head is None else head) +
                "```python\nimport sys\n\n" + body + "\n" + self.T28_MAIN + "```\n")

    def test_t28_passes_the_reference_fix(self):
        body = ("def _key(v):\n"
                "    core, _, rc = v.partition('-rc')\n"
                "    nums = tuple(int(x) for x in core.split('.'))\n"
                "    return nums + ((1, 0) if not rc else (0, int(rc)))\n\n"
                "def is_newer(a, b):\n"
                "    return _key(a) > _key(b)\n")
        self.assertTrue(self._grade("T28", self._t28(body)))

    def test_t28_fails_a_rubber_stamp(self):
        self.assertFalse(self._grade("T28", "VERDICT: APPROVE\nFixes the report; CI is green."))

    def test_t28_fails_resubmitting_the_pr(self):
        body = ("def is_newer(a, b):\n"
                "    return tuple(int(x) for x in a.split('.')) > "
                "tuple(int(x) for x in b.split('.'))\n")
        self.assertFalse(self._grade("T28", self._t28(body)))

    def test_t28_fails_comparing_the_rc_suffix_as_a_string(self):
        body = ("def _key(v):\n"
                "    core, _, rc = v.partition('-rc')\n"
                "    nums = tuple(int(x) for x in core.split('.'))\n"
                "    return nums + ((1, '') if not rc else (0, rc))\n\n"
                "def is_newer(a, b):\n"
                "    return _key(a) > _key(b)\n")
        self.assertFalse(self._grade("T28", self._t28(body)))

    def test_t28_fails_a_correct_fix_under_an_approve_verdict(self):
        body = ("def _key(v):\n"
                "    core, _, rc = v.partition('-rc')\n"
                "    nums = tuple(int(x) for x in core.split('.'))\n"
                "    return nums + ((1, 0) if not rc else (0, int(rc)))\n\n"
                "def is_newer(a, b):\n"
                "    return _key(a) > _key(b)\n")
        self.assertFalse(self._grade("T28", self._t28(body, head="VERDICT: APPROVE\n\n")))

    def test_judge_tasks(self):
        flagged = {t["id"] for t in self.tasks if t.get("judge")}
        self.assertEqual(flagged, {"T06", "T08", "T10", "T16", "T23"})


if __name__ == "__main__":
    unittest.main()