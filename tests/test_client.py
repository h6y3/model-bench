import json
import unittest
from unittest import mock

from lib.client import _parse_response, ClientError, chat

# Build reasoning-markup literals programmatically: the transport mangles
# literal sequences, so never write them contiguous in source.
TAG_OPEN = "<" + "think>"
TAG_CLOSE = "</" + "think>"


def _tagged(inner):
    return TAG_OPEN + inner + TAG_CLOSE


class TestParse(unittest.TestCase):
    def test_plain(self):
        payload = {"choices": [{"message": {"role": "assistant", "content": "OK"}}],
                   "usage": {"prompt_tokens": 18, "completion_tokens": 2}}
        r = _parse_response(payload)
        self.assertEqual(r["content"], "OK")
        self.assertEqual(r["usage"]["prompt_tokens"], 18)

    def test_inline_tags_moved_to_reasoning(self):
        payload = {"choices": [{"message": {"content": _tagged("hello") + "world"}}],
                   "usage": {}}
        r = _parse_response(payload)
        self.assertEqual(r["content"], "world")
        self.assertIn("hello", r["reasoning"])
        self.assertEqual(r["usage"]["completion_tokens"], 0)

    def test_reasoning_field_merged(self):
        payload = {"choices": [{"message": {"content": "ans", "reasoning": "think"}}],
                   "usage": {"prompt_tokens": 1, "completion_tokens": 5}}
        r = _parse_response(payload)
        self.assertEqual(r["content"], "ans")
        self.assertEqual(r["reasoning"], "think")

    def test_missing_choices_raises(self):
        with self.assertRaises(ClientError):
            _parse_response({"error": "boom"})


class TestServedAndCost(unittest.TestCase):
    def test_router_fields_recorded(self):
        payload = {"model": "qwen/qwen3.8-flash", "provider": "Alibaba",
                   "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
                   "usage": {"prompt_tokens": 10, "completion_tokens": 2, "cost": 0.00012}}
        r = _parse_response(payload)
        self.assertEqual(r["served_model"], "qwen/qwen3.8-flash")
        self.assertEqual(r["served_provider"], "Alibaba")
        self.assertAlmostEqual(r["cost"], 0.00012)

    def test_no_cost_means_none_not_zero(self):
        # Zero would read as "free"; None sends the bench to the RATES estimate.
        r = _parse_response({"choices": [{"message": {"content": "OK"}}], "usage": {}})
        self.assertIsNone(r["cost"])
        self.assertIsNone(r["served_provider"])


class FakeResp:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestRequestBody(unittest.TestCase):
    def test_extra_body_merged_and_key_only_in_header(self):
        seen = {}

        def fake_urlopen(req, timeout):
            seen["body"] = json.loads(req.data.decode())
            seen["auth"] = req.get_header("Authorization")
            return FakeResp({"choices": [{"message": {"content": "OK"}}], "usage": {}})

        extra = {"provider": {"only": ["alibaba"], "allow_fallbacks": False},
                 "usage": {"include": True}}
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            chat("https://openrouter.ai/api/v1", "qwen/qwen3.8-flash",
                 [{"role": "user", "content": "hi"}], api_key="sk-test-secret",
                 extra_body=extra)
        self.assertEqual(seen["body"]["provider"], extra["provider"])
        self.assertEqual(seen["body"]["usage"], {"include": True})
        self.assertEqual(seen["body"]["model"], "qwen/qwen3.8-flash")
        self.assertEqual(seen["auth"], "Bearer sk-test-secret")
        self.assertNotIn("sk-test-secret", json.dumps(seen["body"]))


if __name__ == "__main__":
    unittest.main()