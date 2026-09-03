import unittest

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


if __name__ == "__main__":
    unittest.main()