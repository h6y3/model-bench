import unittest

from lib.report import est_cost, render_report

RUN = {
    "runid": "20260903-120000",
    "judge_model": "glm-5.3:cloud",
    "judge_enabled": True,
    "models": ["m-fast", "m-weak"],
    "results": {
        "m-fast": {"tasks": {
            "T01": {"passed": True, "checks": [], "latency_s": 1.0,
                    "tokens_per_s": 10.0, "est_cost": 0.0001,
                    "prompt_tokens": 100, "completion_tokens": 10,
                    "judge": {"score": 5, "verdict": "great"}, "error": None},
            "T02": {"passed": False, "checks": [{"name": "contains_all", "passed": False,
                    "observed": "missing: ['x']", "expected": "x"}],
                    "latency_s": 2.0, "tokens_per_s": 10.0, "est_cost": 0.0002,
                    "prompt_tokens": 200, "completion_tokens": 20,
                    "judge": None, "error": None},
        }},
        "m-weak": {"tasks": {
            "T01": {"passed": False, "checks": [{"name": "exact", "passed": False,
                    "observed": "nope", "expected": "OK"}],
                    "latency_s": 3.0, "tokens_per_s": 10.0, "est_cost": 0.0003,
                    "prompt_tokens": 100, "completion_tokens": 30,
                    "judge": None, "error": None},
            "T02": {"passed": True, "checks": [], "latency_s": 4.0,
                    "tokens_per_s": 10.0, "est_cost": 0.0004,
                    "prompt_tokens": 200, "completion_tokens": 40,
                    "judge": {"score": 3, "verdict": "ok"}, "error": None},
        }},
    },
    "task_titles": {"T01": "Instruction precision", "T02": "Diagnosis"},
}


class TestCost(unittest.TestCase):
    def test_est_cost(self):
        self.assertAlmostEqual(est_cost("glm-5.3-flash:cloud", 1_000_000, 1_000_000), 0.65)
        self.assertAlmostEqual(est_cost("unknown", 1_000_000, 0), 0.0)


class TestReport(unittest.TestCase):
    def test_renders_matrix_and_totals(self):
        md = render_report(RUN)
        self.assertIn("m-fast", md)
        self.assertIn("T01", md)
        self.assertIn("1/2", md)  # m-fast total

    def test_self_judge_badge(self):
        run = dict(RUN)
        run["models"] = ["glm-5.3:cloud"]
        run["results"] = {"glm-5.3:cloud": RUN["results"]["m-fast"]}
        md = render_report(run)
        self.assertIn("judge=self", md)

    def test_baseline_delta(self):
        base = dict(RUN)
        base["models"] = ["m-weak"]
        md = render_report(RUN, baseline=base)
        self.assertIn("baseline", md.lower())


if __name__ == "__main__":
    unittest.main()