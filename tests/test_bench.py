import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import bench
from bench import run_model


class FakeClient:
    def chat(self, model, messages, **kw):
        task_prompt = messages[-1]["content"]
        return {"content": "OK BANANA" if "exactly" in task_prompt else "wrong",
                "reasoning": "", "usage": {"prompt_tokens": 10, "completion_tokens": 2},
                "latency_s": 0.5}


class TestRunModel(unittest.TestCase):
    def test_pass_and_fail_recorded(self):
        from tasks import load_tasks
        tasks = [t for t in load_tasks() if t["id"] == "T01"]
        out = run_model("fake", tasks, base_url="http://unused",
                        concurrency=1, judge_model=None, judge_enabled=False,
                        client=FakeClient().chat)
        self.assertEqual(out["tasks"]["T01"]["passed"], True)
        self.assertEqual(out["tasks"]["T01"]["latency_s"], 0.5)

    # A model that spends its whole budget on hidden reasoning returns an empty
    # answer; on 2026-10-20 that surfaced only as "no fenced code block". The
    # stop reason and the budget it hit are what make it diagnosable later.
    def test_records_finish_reason_and_budget(self):
        from tasks import load_tasks
        tasks = [t for t in load_tasks() if t["id"] == "T01"]

        def starved(model, messages, **kw):
            return {"content": "", "reasoning": "x" * 50, "finish_reason": "length",
                    "usage": {"prompt_tokens": 10, "completion_tokens": kw["max_tokens"]},
                    "latency_s": 1.0}
        out = run_model("fake", tasks, base_url="http://unused", concurrency=1,
                        judge_model=None, judge_enabled=False, client=starved)
        r = out["tasks"]["T01"]
        self.assertEqual(r["finish_reason"], "length")
        self.assertTrue(r["truncated"])
        self.assertEqual(r["max_tokens"], tasks[0]["max_tokens"])


class TestRunSettings(unittest.TestCase):
    def test_run_json_records_request_settings(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(bench, "RESULTS", Path(d)), \
                mock.patch.object(bench, "preflight"), \
                mock.patch.object(bench, "run_model", return_value={"tasks": {}}), \
                mock.patch("builtins.print"):
            bench.main(["--models", "fake", "--only", "T01", "--concurrency", "1"])
            run = json.loads(next(Path(d).glob("*/run.json")).read_text())
        self.assertEqual(run["settings"]["temperature"], bench.DEFAULT_TEMPERATURE)
        self.assertEqual(run["settings"]["concurrency"], 1)
        self.assertEqual(run["settings"]["only"], "T01")


if __name__ == "__main__":
    unittest.main()