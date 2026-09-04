import unittest

from lib.judge import parse_judge


class TestParseJudge(unittest.TestCase):
    def test_clean_json(self):
        r = parse_judge('{"score": 4, "verdict": "solid, minor gaps"}')
        self.assertEqual((r["score"], r["verdict"]), (4, "solid, minor gaps"))

    def test_wrapped_json(self):
        r = parse_judge('Sure!\n```json\n{"score": 5, "verdict": "perfect"}\n```')
        self.assertEqual(r["score"], 5)

    def test_clamped(self):
        self.assertEqual(parse_judge('{"score": 9, "verdict": "x"}')["score"], 5)
        self.assertEqual(parse_judge('{"score": 0, "verdict": "x"}')["score"], 1)

    def test_unparseable(self):
        r = parse_judge("no json here")
        self.assertIsNone(r["score"])
        self.assertTrue(r["verdict"].startswith("unparseable"))


if __name__ == "__main__":
    unittest.main()