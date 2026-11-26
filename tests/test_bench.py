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


def _ok(content="OK BANANA", **extra):
    r = {"content": content, "reasoning": "", "finish_reason": "stop",
         "usage": {"prompt_tokens": 10, "completion_tokens": 2}, "latency_s": 0.5}
    r.update(extra)
    return r


class TestServedAndBilled(unittest.TestCase):
    def test_served_model_and_billed_cost_recorded(self):
        from tasks import load_tasks
        tasks = [t for t in load_tasks() if t["id"] == "T01"]
        client = lambda m, msgs, **kw: _ok(served_model="qwen/qwen3.8-flash",
                                           served_provider="Alibaba", cost=0.0005)
        r = run_model("qwen/qwen3.8-flash", tasks, base_url="http://unused", concurrency=1,
                      judge_model=None, judge_enabled=False, client=client)["tasks"]["T01"]
        self.assertEqual(r["served_model"], "qwen/qwen3.8-flash")
        self.assertEqual(r["served_provider"], "Alibaba")
        self.assertEqual(r["cost_source"], "billed")
        self.assertAlmostEqual(r["est_cost"], 0.0005)

    def test_rate_estimate_when_not_billed(self):
        from tasks import load_tasks
        tasks = [t for t in load_tasks() if t["id"] == "T01"]
        r = run_model("glm-5.3-flash:cloud", tasks, base_url="http://unused", concurrency=1,
                      judge_model=None, judge_enabled=False,
                      client=lambda m, msgs, **kw: _ok())["tasks"]["T01"]
        self.assertEqual(r["cost_source"], "rate")

    def test_judge_goes_through_judge_client(self):
        from tasks import load_tasks
        tasks = [t for t in load_tasks() if t["judge"]][:1]
        calls = []

        def model_client(m, msgs, **kw):
            calls.append(("model", m))
            return _ok("answer")

        def judge_client(m, msgs, **kw):
            calls.append(("judge", m))
            return _ok('{"score": 4, "verdict": "fine"}')
        run_model("qwen/qwen3.8-flash", tasks, base_url="http://unused", concurrency=1,
                  judge_model="glm-5.3:cloud", judge_enabled=True,
                  client=model_client, judge_client=judge_client)
        self.assertIn(("judge", "glm-5.3:cloud"), calls)
        self.assertNotIn(("model", "glm-5.3:cloud"), calls)


class TestOpenRouterCli(unittest.TestCase):
    def _main(self, argv, env):
        seen = {}

        def fake_make_client(base_url, api_key="ollama", extra_body=None):
            seen.setdefault("clients", []).append((base_url, api_key, extra_body))
            return lambda m, msgs, **kw: _ok()
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.dict("os.environ", env, clear=True), \
                mock.patch.object(bench, "RESULTS", Path(d)), \
                mock.patch.object(bench, "make_client", fake_make_client), \
                mock.patch.object(bench, "preflight"), \
                mock.patch.object(bench, "run_model", return_value={"tasks": {}}), \
                mock.patch("builtins.print"):
            rc = bench.main(argv)
            files = list(Path(d).glob("*/run.json"))
            seen["run_text"] = files[0].read_text() if files else ""
        seen["rc"] = rc
        return seen

    def test_openrouter_wires_url_key_provider_and_ollama_judge(self):
        s = self._main(["--openrouter", "--models", "qwen/qwen3.8-flash", "--only", "T01",
                        "--provider", '{"only":["alibaba"],"allow_fallbacks":false}',
                        "--judge"], {"OPENROUTER_API_KEY": "sk-or-test-secret"})
        self.assertEqual(s["rc"], 0)
        base, key, extra = s["clients"][0]
        self.assertEqual(base, bench.OPENROUTER_URL)
        self.assertEqual(key, "sk-or-test-secret")
        self.assertEqual(extra["provider"], {"only": ["alibaba"], "allow_fallbacks": False})
        self.assertEqual(extra["usage"], {"include": True})
        self.assertEqual(s["clients"][1][0], bench.OLLAMA_URL)  # judge stays local
        run = json.loads(s["run_text"])
        self.assertEqual(run["settings"]["api_key_env"], "OPENROUTER_API_KEY")
        self.assertNotIn("sk-or-test-secret", s["run_text"])

    def test_missing_key_refuses_before_any_call(self):
        s = self._main(["--openrouter", "--models", "x", "--only", "T01"], {})
        self.assertEqual(s["rc"], 2)
        self.assertNotIn("clients", s)
        self.assertEqual(s["run_text"], "")

    def test_bad_provider_json_refuses(self):
        s = self._main(["--openrouter", "--models", "x", "--provider", "{nope"],
                       {"OPENROUTER_API_KEY": "k"})
        self.assertEqual(s["rc"], 2)

    def test_judge_on_same_endpoint_drops_provider_pin(self):
        s = self._main(["--openrouter", "--judge-base-url", bench.OPENROUTER_URL,
                        "--models", "qwen/qwen3.8-flash", "--only", "T01",
                        "--provider", '{"only":["alibaba"]}', "--judge", "some/judge"],
                       {"OPENROUTER_API_KEY": "k"})
        judge_base, judge_key, judge_extra = s["clients"][1]
        self.assertEqual(judge_base, bench.OPENROUTER_URL)
        self.assertEqual(judge_key, "k")
        self.assertNotIn("provider", judge_extra)
        self.assertEqual(judge_extra["usage"], {"include": True})

    def test_default_stays_on_ollama(self):
        s = self._main(["--models", "glm-5.3-flash:cloud", "--only", "T01"], {})
        self.assertEqual(s["clients"][0], (bench.OLLAMA_URL, "ollama", None))

