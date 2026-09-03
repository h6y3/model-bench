import unittest
from lib.checks import normalize, extract_fenced_blocks, extract_json, run_checks, strip_think


class TestStripThink(unittest.TestCase):
    def test_moves_think_out(self):
        c, r = strip_think("<think>thinking</think>OK")
        self.assertEqual(c, "OK")
        self.assertEqual(r, "thinking")

    def test_plain_passthrough(self):
        c, r = strip_think("just an answer")
        self.assertEqual((c, r), ("just an answer", ""))


class TestNormalize(unittest.TestCase):
    def test_collapses_whitespace(self):
        self.assertEqual(normalize("  a\n  b\t c "), "a b c")


class TestFenced(unittest.TestCase):
    def test_single_block(self):
        self.assertEqual(extract_fenced_blocks("```python\nprint(1)\n```"), ["print(1)"])

    def test_multiple_blocks_no_lang(self):
        self.assertEqual(extract_fenced_blocks("a\n```\nx\n```\n```\ny\n```"), ["x", "y"])

    def test_none(self):
        self.assertEqual(extract_fenced_blocks("no code"), [])


class TestExtractJson(unittest.TestCase):
    def test_inline(self):
        self.assertEqual(extract_json('junk {"a": 1} tail'), {"a": 1})

    def test_fenced(self):
        self.assertEqual(extract_json('```json\n{"a": [1,2]}\n```'), {"a": [1, 2]})

    def test_invalid(self):
        self.assertIsNone(extract_json("not json at all"))


class TestRunChecks(unittest.TestCase):
    def run1(self, answer, checker):
        return run_checks(answer, [checker])[0]

    def test_exact_pass_fail(self):
        c = {"type": "exact", "value": "OK"}
        self.assertTrue(self.run1("OK", c)["passed"])
        self.assertFalse(self.run1("ok", {**c, "case_sensitive": True})["passed"])
        self.assertTrue(self.run1("  ok ", c)["passed"])

    def test_contains_all_none(self):
        self.assertTrue(self.run1("Fix the auth bug", {"type": "contains_all", "values": ["auth", "bug"]})["passed"])
        self.assertFalse(self.run1("auth", {"type": "contains_all", "values": ["auth", "bug"]})["passed"])
        self.assertTrue(self.run1("use TLS", {"type": "contains_none", "values": ["http"]})["passed"])
        self.assertFalse(self.run1("use HTTP", {"type": "contains_none", "values": ["http"]})["passed"])

    def test_regex(self):
        self.assertTrue(self.run1("v2.4.1", {"type": "regex", "pattern": r"v\d+\.\d+\.\d+", "search": True})["passed"])
        self.assertFalse(self.run1("see v2.4.1 here", {"type": "regex", "pattern": r"^v\d+$"})["passed"])

    def test_json_asserts(self):
        c = {"type": "json_asserts", "asserts": [
            {"path": "name", "op": "eq", "value": "x"},
            {"path": "items", "op": "len", "value": 2},
            {"path": "items.0", "op": "contains", "value": "a"},
        ]}
        self.assertTrue(self.run1('{"name": "x", "items": ["a", "b"]}', c)["passed"])
        self.assertFalse(self.run1('{"name": "y", "items": ["a"]}', c)["passed"])

    def test_length(self):
        self.assertTrue(self.run1("one two three", {"type": "length_max", "words": 3})["passed"])
        self.assertFalse(self.run1("one two three four", {"type": "length_max", "words": 3})["passed"])
        self.assertTrue(self.run1("one two three", {"type": "length_min", "words": 3})["passed"])

    def test_exec_python(self):
        code = "import sys\nprint('hi ' + sys.argv[1])\n"
        answer = "Here:\n```python\n" + code + "```"
        c = {"type": "exec_code", "lang": "python", "cases": [
            {"args": ["world"], "expect_exit": 0, "expect_stdout_contains": ["hi world"]},
            {"args": ["x"], "expect_stdout_not_contains": ["bye"]},
        ]}
        self.assertTrue(all(r["passed"] for r in run_checks(answer, [c])))

    def test_exec_bash(self):
        answer = "```\n#!/usr/bin/env bash\nsed 's/a/b/' <<< \"$1\"\n```"
        c = {"type": "exec_code", "lang": "bash", "cases": [
            {"args": ["cat"], "expect_exit": 0, "expect_stdout_contains": ["cbt"]},
        ]}
        self.assertTrue(run_checks(answer, [c])[0]["passed"])

    def test_exec_no_block_fails(self):
        r = self.run1("no code", {"type": "exec_code", "lang": "python", "cases": [{"args": []}]})
        self.assertFalse(r["passed"])

    def test_unknown_type(self):
        r = self.run1("x", {"type": "wat"})
        self.assertFalse(r["passed"])
        self.assertIn("wat", r["observed"])


if __name__ == "__main__":
    unittest.main()
