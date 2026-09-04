import unittest

from lib.client import _parse_response, ClientError

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


if __name__ == "__main__":
    unittest.main()