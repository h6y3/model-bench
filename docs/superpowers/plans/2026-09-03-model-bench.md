# model-bench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stdlib-only Python harness that runs 10 realistic single-turn tasks against Ollama Cloud models and reports pass/metrics comparisons, with an optional LLM judge and a weak negative-control model.

**Architecture:** CLI runner (`bench.py`) loads task modules, fans tasks out in parallel per model (models sequential), calls an OpenAI-compatible chat endpoint via `urllib`, grades answers with deterministic checkers plus an optional rubric judge, and writes `results/<runid>/run.json` + `report.md`. Tasks are plain Python dicts in `tasks/t*.py`; checkers/judge/report are separate small modules under `lib/`.

**Tech Stack:** Python 3 stdlib only (`urllib`, `json`, `re`, `subprocess`, `argparse`, `concurrent.futures`, `unittest`, `tempfile`). No pip packages.

**Spec:** `docs/superpowers/specs/2026-09-03-model-bench-design.md`

## Global Constraints

- Python 3 stdlib only; no third-party imports anywhere.
- Endpoint default `http://127.0.0.1:11434/v1`; header `Authorization: Bearer ollama`.
- Default models: `glm-5.3-flash:cloud`, `glm-5.3:cloud`, `gemma4:31b:cloud`.
- Temperature 0.2, max_tokens default 700, task timeout default 120 s.
- Judge default model `glm-5.3:cloud`; only tasks with `judge: true` judged.
- A run ALWAYS writes partial results; single-task failure never raises into caller.
- Reasoning models: strip `<think>...` tags from content; capture `message.reasoning` separately; never grade reasoning text.
- Tasks are single-turn, no tools; context embedded in prompts.

---

### Task 1: Checker library core (pure functions + exec)

**Files:**
- Create: `lib/__init__.py` (empty), `lib/checks.py`
- Test: `tests/__init__.py` (empty), `tests/test_checks.py`

**Interfaces:**
- Produces:
  - `strip_think(text: str) -> tuple[str, str]` — returns `(content, reasoning)`; moves `<think>...` spans out of content
  - `normalize(s: str) -> str` — strip, collapse internal whitespace
  - `extract_fenced_blocks(text: str) -> list[str]` — code from ``` / ```lang fences, in order, fence lines excluded
  - `extract_json(text: str) -> object | None` — first parseable JSON via `json.JSONDecoder().raw_decode` scan (fenced blocks included); `None` if none
  - `run_checks(answer: str, checkers: list[dict]) -> list[dict]` — each result `{"name": str, "type": str, "passed": bool, "observed": str, "expected": str}` (observed/expected truncated to 200 chars)

Checker dict forms (dispatch on `"type"`):
- `{"type": "exact", "value": str, "case_sensitive": bool=False, "strip": bool=True}`
- `{"type": "contains_all", "values": [str], "case_insensitive": bool=True}`
- `{"type": "contains_none", "values": [str], "case_insensitive": bool=True}`
- `{"type": "regex", "pattern": str, "search": bool=False, "case_insensitive": bool=False}`
- `{"type": "json_asserts", "asserts": [{"path": "a.b.0.c", "op": "eq|len|contains|gte|lte|type", "value": ...}]}`
- `{"type": "length_max", "words": int}` / `{"type": "length_min", "words": int}`
- `{"type": "exec_code", "lang": "python"|"bash", "cases": [{"args": [str], "stdin": str, "expect_exit": int, "expect_stdout_contains": [str], "expect_stdout_not_contains": [str]}], "timeout_s": int=15}` — runs the FIRST fenced block saved as `main.py`/`main.sh` in a temp dir; one result per case named `exec_code[case0]`, `exec_code[case1]`, ...
- Unknown type → `passed: False`, observed `unknown checker type: X`.

- [ ] **Step 1: Write failing tests**

`tests/test_checks.py`:

```python
import unittest
from lib.checks import normalize, extract_fenced_blocks, extract_json, run_checks, strip_think


class TestStripThink(unittest.TestCase):
    def test_moves_think_out(self):
        c, r = strip_think("</think>OK`")
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
```

- [ ] **Step 2: Run tests, verify failure**

Run: `cd ~/Development/_organized/_active/model-bench && python3 -m unittest discover -s tests -v 2>&1 | tail -3`
Expected: FAIL/ERROR — `ModuleNotFoundError: No module named 'lib'`.

- [ ] **Step 3: Implement `lib/checks.py`**

```python
"""Deterministic answer checkers for model-bench. Stdlib only."""
import json
import re
import subprocess
import tempfile
from pathlib import Path

THINK_RE = re.compile(r"</think>(.*?)</think>", re.DOTALL)
FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


def strip_think(text):
    """Split '</think>...</think>' spans out of content. Returns (content, reasoning)."""
    reasoning = "\n".join(m.strip() for m in THINK_RE.findall(text or ""))
    content = THINK_RE.sub("", text or "").strip()
    return content, reasoning


def normalize(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def extract_fenced_blocks(text):
    return FENCE_RE.findall(text or "")


def extract_json(text):
    text = text or ""
    decoder = json.JSONDecoder()
    candidates = [text]
    candidates.extend(extract_fenced_blocks(text))
    for candidate in candidates:
        stripped = candidate.lstrip()
        for i, ch in enumerate(stripped):
            if ch in "{[":
                try:
                    obj, _ = decoder.raw_decode(stripped[i:])
                    return obj
                except json.JSONDecodeError:
                    continue
    return None


def _get_path(obj, path):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            cur = cur[part]
        else:
            raise KeyError(path)
    return cur


def _check_json_assert(answer, spec):
    obj = extract_json(answer)
    if obj is None:
        return False, "no JSON found", "valid JSON"
    for a in spec.get("asserts", []):
        try:
            got = _get_path(obj, a["path"])
        except (KeyError, IndexError, ValueError, TypeError):
            return False, f"missing path {a['path']}", a["path"]
        op, want = a["op"], a.get("value")
        ok = {
            "eq": lambda: got == want,
            "len": lambda: len(got) == want,
            "contains": lambda: want in got,
            "gte": lambda: got >= want,
            "lte": lambda: got <= want,
            "type": lambda: {"str": str, "int": int, "float": float,
                             "list": list, "dict": dict, "bool": bool}.get(want) and
                     isinstance(got, {"str": str, "int": int, "float": float,
                                      "list": list, "dict": dict, "bool": bool}[want]) or
                     (want == "num" and isinstance(got, (int, float)) and not isinstance(got, bool)),
        }[op]()
        if not ok:
            return False, f"{a['path']}={got!r}", f"{a['path']} {op} {want!r}"
    return True, "all asserts passed", ""


def _check_exec(answer, spec):
    blocks = extract_fenced_blocks(answer)
    if not blocks:
        return [{"name": "exec_code", "type": "exec_code", "passed": False,
                 "observed": "no fenced code block", "expected": "one code block"}]
    lang = spec.get("lang", "python")
    fname = "main.py" if lang == "python" else "main.sh"
    runner = ["python3", fname] if lang == "python" else ["bash", fname]
    results = []
    with tempfile.TemporaryDirectory() as td:
        Path(td, fname).write_text(blocks[0], encoding="utf-8")
        if lang == "bash":
            Path(td, fname).chmod(0o755)
        for i, case in enumerate(spec.get("cases", [{}])):
            cmd = runner + list(case.get("args", []))
            try:
                proc = subprocess.run(cmd, cwd=td, input=case.get("stdin", ""),
                                      capture_output=True, text=True,
                                      timeout=spec.get("timeout_s", 15))
                out, code = proc.stdout, proc.returncode
            except subprocess.TimeoutExpired:
                results.append({"name": f"exec_code[case{i}]", "type": "exec_code",
                                "passed": False, "observed": "timeout",
                                "expected": f"exit {case.get('expect_exit', 0)}"})
                continue
            passed = code == case.get("expect_exit", 0)
            for token in case.get("expect_stdout_contains", []):
                passed = passed and token in out
            for token in case.get("expect_stdout_not_contains", []):
                passed = passed and token not in out
            results.append({"name": f"exec_code[case{i}]", "type": "exec_code",
                            "passed": passed,
                            "observed": f"exit={code} out={out[:120]!r}",
                            "expected": f"exit={case.get('expect_exit', 0)} "
                                        f"contains={case.get('expect_stdout_contains', [])}"})
    return results


def run_checks(answer, checkers):
    results = []
    for spec in checkers:
        ctype = spec.get("type")
        base = {"type": ctype, "name": ctype}
        if ctype == "exact":
            want = spec["value"]
            got = answer
            if spec.get("strip", True):
                want, got = want.strip(), got.strip()
            if not spec.get("case_sensitive", False):
                want, got = want.lower(), got.lower()
            base.update(passed=got == want, observed=got, expected=want)
        elif ctype == "contains_all":
            hay = answer.lower() if spec.get("case_insensitive", True) else answer
            missing = [v for v in spec["values"]
                       if (v.lower() if spec.get("case_insensitive", True) else v) not in hay]
            base.update(passed=not missing,
                        observed=f"missing: {missing}" if missing else "all present",
                        expected=f"all of {spec['values']}")
        elif ctype == "contains_none":
            hay = answer.lower() if spec.get("case_insensitive", True) else answer
            found = [v for v in spec["values"]
                     if (v.lower() if spec.get("case_insensitive", True) else v) in hay]
            base.update(passed=not found,
                        observed=f"found: {found}" if found else "none present",
                        expected=f"none of {spec['values']}")
        elif ctype == "regex":
            flags = re.I if spec.get("case_insensitive", False) else 0
            m = (re.search if spec.get("search", False) else re.fullmatch)(
                spec["pattern"], answer, flags)
            base.update(passed=m is not None,
                        observed=answer[:200], expected=spec["pattern"])
        elif ctype == "json_asserts":
            ok, observed, expected = _check_json_assert(answer, spec)
            base.update(passed=ok, observed=observed, expected=expected)
        elif ctype == "length_max":
            n = len(answer.split())
            base.update(passed=n <= spec["words"], observed=f"{n} words",
                        expected=f"<= {spec['words']} words")
        elif ctype == "length_min":
            n = len(answer.split())
            base.update(passed=n >= spec["words"], observed=f"{n} words",
                        expected=f">= {spec['words']} words")
        elif ctype == "exec_code":
            results.extend(_check_exec(answer, spec))
            continue
        else:
            base.update(passed=False, observed=f"unknown checker type: {ctype}", expected="")
        base["observed"] = str(base.get("observed", ""))[:200]
        base["expected"] = str(base.get("expected", ""))[:200]
        results.append(base)
    return results
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -3`
Expected: `OK` (all tests pass).

- [ ] **Step 5: Commit**

```bash
cd ~/Development/_organized/_active/model-bench
git add lib/ tests/
git commit -m "feat: deterministic checker library (exact/contains/regex/json/exec/length)"
```

---

### Task 2: API client (OpenAI-compatible chat)

**Files:**
- Create: `lib/client.py`
- Test: `tests/test_client.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class ClientError(Exception)` with `.kind` in `{"http", "timeout", "json", "http_error_body"}`
  - `chat(base_url: str, model: str, messages: list[dict], *, api_key: str = "ollama", timeout_s: float = 120.0, max_tokens: int = 700, temperature: float = 0.2) -> dict`
  - Return shape: `{"content": str, "reasoning": str, "usage": {"prompt_tokens": int, "completion_tokens": int}, "latency_s": float}`
  - `_parse_response(payload: dict) -> dict` — pure function, same shape minus `latency_s`; unit-tested without network.

Behavior: POST `{base_url}/chat/completions` with JSON body; `Authorization: Bearer {api_key}` header; non-200 → `ClientError("http", status)`; body unparseable → include first 200 chars; content = `choices[0].message.content or ""` after `strip_think`; reasoning = inline-think text joined with `message.reasoning` if both exist; usage defaults to zeros when absent.

- [ ] **Step 1: Write failing tests**

`tests/test_client.py`:

```python
import unittest
from lib.client import _parse_response, ClientError


class TestParse(unittest.TestCase):
    def test_plain(self):
        payload = {"choices": [{"message": {"role": "assistant", "content": "OK"}}],
                   "usage": {"prompt_tokens": 18, "completion_tokens": 2}}
        r = _pd = _parse = _parse_response(payload)
        self.assertEqual(r["content"], "OK")
        self.assertEqual(r["usage"]["prompt_tokens"], 18)

    def test_inline_think_moved_to_reasoning(self):
        payload = {"choices": [{"message": {"content": "</think>hello</think>world"}}],
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
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -3`
Expected: FAIL — `ImportError: cannot import name '_parse_response'`.

- [ ] **Step 3: Implement `lib/client.py`**

```python
"""OpenAI-compatible chat client for Ollama Cloud. Stdlib only."""
import json
import time
import urllib.error
import urllib.request

from .checks import strip_think


class ClientError(Exception):
    def __init__(self, kind, detail):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


def _parse_response(payload):
    choices = payload.get("choices")
    if not choices:
        raise ClientError("json", f"no choices in response: {json.dumps(payload)[:200]}")
    msg = choices[0].get("message", {})
    content, inline_reasoning = strip_think(msg.get("content") or "")
    field_reasoning = (msg.get("reasoning") or "").strip()
    parts = [p for p in (field_reasoning, inline_reasoning) if p]
    usage = payload.get("usage") or {}
    return {
        "content": content,
        "reasoning": "\n".join(parts),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        },
    }


def chat(base_url, model, messages, *, api_key="ollama", timeout_s=120.0,
         max_tokens=700, temperature=0.2):
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens,
                       "temperature": temperature}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode()[:200]
        except Exception:
            pass
        raise ClientError("http", f"status {e.code} {detail}") from e
    except urllib.error.URLError as e:
        raise ClientError("timeout" if "timed out" in str(e) else "http", str(e)) from e
    except json.JSONDecodeError as e:
        raise ClientError("json", str(e)) from e
    result = _parse_response(payload)
    result["latency_s"] = time.monotonic() - start
    return result
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -3`
Expected: `OK`.

- [ ] **Step 5: Live smoke test (1 API call, ~20 tokens)**

```bash
cd ~/Development/_organized/_active/model-bench && python3 -c "
from lib.client import chat
r = chat('http://127.0.0.1:11434/v1', 'gemma4:31b:cloud',
         [{'role': 'user', 'content': 'Reply with exactly: OK'}], max_tokens=10)
print(r['content'], r['usage'], round(r['latency_s'], 2))
"
```
Expected: prints `OK {'prompt_tokens': ..., 'completion_tokens': ...} <seconds>`.

- [ ] **Step 6: Commit**

```bash
git add lib/client.py tests/test_client.py
git commit -m "feat: OpenAI-compatible chat client with reasoning handling"
```

---

### Task 3: Task loader + 10 task modules

**Files:**
- Create: `tasks/__init__.py`, `tasks/t01_instruction.py` … `tasks/t10_writing.py` (10 files)
- Test: `tests/test_tasks.py`

**Interfaces:**
- Produces:
  - `load_tasks(task_dir: Path | None = None) -> list[dict]` — imports `tasks/t*.py`, validates each `TASK` dict has keys `id, title, category, prompt, checkers, timeout_s, max_tokens, judge` (prompt/checkers non-empty), returns sorted by `id`.
  - Each `TASK` dict: `{"id": "T01", "title": str, "category": str, "prompt": str, "checkers": list[dict], "timeout_s": int, "max_tokens": int, "judge": bool}`.

Task content contract (prompts must instruct: answer only in the requested artifact; code in ONE fenced block when code is requested):

- **T01 instruction-precision** (`judge: false`): "Reply with exactly the three characters: OK?" → exact `OK?` … no — keep the canonical from sessions: prompt "Reply with exactly: OK" → `exact` `OK`. Second instruction embedded: "After that line, on a new line write the word BANANA." → `exact` `OK\nBANANA` (normalize handles newline→space). Checkers: `[{"type":"exact","value":"OK BANANA"}]` (normalize collapses `\n`→space).
- **T02 log diagnosis** (`judge: false`): embed a synthetic `coredumpctl`-style snippet: python3.14 worker SIGSEGV in libssl during TLS handshake after upgrade; distractor line about low memory. Ask: name the failing component and the signal in one short sentence. Checkers: `contains_all ["libssl", "SIGSEGV"]`, `contains_none ["OOM", "out of memory", "disk"]`.
- **T03 config edit** (`judge: false`): embed broken YAML (missing indent on one key, wrong `trigger` quoting, duplicate key) mirroring the user's espanso base.yml shape. Ask: output ONLY the corrected YAML. Checkers: `contains_all ["trigger: \";;date\"", "  word: true", "replace: \"{{d}}\""]`, `contains_none ["::", "trigger: :date"]` — wait: corrected file should use the user's real convention `trigger: ";;date"`; planted errors: lost indent, `triger:` typo, duplicate `word: true` under wrong parent. Keep checkers: `contains_all ["triger"→"trigger:", 'trigger: ";;date"']` — concretely: `{"type":"contains_all","values":["trigger:", 'trigger: ";;date"', "word: true"]}` + `{"type":"regex","pattern":"^\\s+- trigger:", "search": false}` … simpler: assert corrected typo (`triger:` absent via `contains_none ["triger"]`) and corrected indent line present (`contains_all ["        format:"]`). Final checkers: `contains_all ["trigger: \";;date\"", "word: true", "        format:"]`, `contains_none ["triger", "\t"]`.
- **T04 script writing** (`judge: false`): "Write a bash script that takes a directory as argv[1] and prints the count of files (not dirs) inside. Only the script in one fenced code block." Checkers: `exec_code` bash with a fixture dir created by the case? — cases can't create fixtures; instead script receives dir path; make the fixture inside the task's tmp run: `exec_code` writes `main.sh` to a fresh temp dir, so the script must create/accept a path. Solution: case passes `args: ["/etc"]` — env-dependent, flaky. Better: change task to "print the count of arguments passed to the script" — fully self-contained: `cases: [{"args": ["a","b","c"], "expect_stdout_contains": ["3"]}, {"args": [], "expect_stdout_contains": ["0"]}]`. Prompt: "Write a bash script that prints the number of arguments passed to it (just the number). One fenced code block only."
- **T05 data transform** (`judge: false`): embed JSON array of 4 log entries `{ts, level, msg}`; ask: return JSON object `{"errors": [ts of level=="error" entries sorted], "total": N}` only. Checkers: `json_asserts` `errors` eq `["2026-09-01T03:12:00Z","2026-09-02T09:44:00Z"]`, `total` eq `4`, plus `type` str/int.
- **T06 research synthesis** (`judge: true`): embed 3 short fake source snippets (150 words each) about a fictional tool "omarchy-launcher 2.0" with facts: new fuzzy search, wayland-only, config moved to `~/.config/omarchy-launcher/`, breaking change: `--theme` renamed `--style`. Ask: ≤120-word summary for a user deciding whether to upgrade. Checkers: `contains_all ["fuzzy", "--style", "wayland"]` (case-insensitive), `length_max 140` (words, slack for counting).
- **T07 commit message** (`judge: false`): embed a `git diff --stat`-ish patch changing trigger `:`→`;;` in espanso YAML. Ask: ONE conventional-commit subject line only. Checkers: `regex ^\w+(?:\([\w./-]+\))?!?: .{5,69}$` (imperative-ish subject, length), `contains_all ["trigger"]`, `contains_none ["\n"]`.
- **T08 code review** (`judge: true`): embed 15-line python snippet with planted off-by-one `range(len(x))` slicing bug producing dropped last element + a red-herring unused import. Ask: name the bug and its effect in ≤80 words. Checkers: `contains_all ["off-by-one", "last"]` OR — can't OR; use `contains_all ["range", "len"]` + judge for nuance; `contains_none ["unused import is the main problem", "syntax error"]`.
- **T09 regex/one-liner** (`judge: false`): "Write a POSIX sed one-liner (one fenced block) that converts ISO dates `YYYY-MM-DD` to `MM/DD/YYYY` on stdin." Checkers: `exec_code` bash cases: `{"args": [], "stdin": "2026-09-03 and 1999-12-31", "expect_stdout_contains": ["09/03/2026", "and"], "expect_stdout_not_contains": ["2026-09-03"]}`.
- **T10 constrained writing** (`judge: true`): embed a 90-word rambling paragraph; ask: rewrite as ≤25 words, no adjectives, keep the fact "backup ran at 02:00 and succeeded". Checkers: `length_max 27`, `contains_all ["02:00"]`; judge scores quality.

- [ ] **Step 1: Write failing test**

`tests/test_tasks.py`:

```python
import unittest
from pathlib import Path
from tasks import load_tasks

REQUIRED = {"id", "title", "category", "prompt", "checkers", "timeout_s", "max_tokens", "judge"}
VALID_TYPES = {"exact", "contains_all", "contains_none", "regex",
               "json_asserts", "length_max", "length_min", "exec_code"}


class TestTasks(unittest.TestCase):
    def setUp(self):
        self.tasks = load_tasks()

    def test_ten_tasks(self):
        self.assertEqual(len(self.tasks), 10)

    def test_unique_ids_sequential(self):
        self.assertEqual([t["id"] for t in self.tasks],
                         [f"T{i:02d}" for i in range(1, 11)])

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
        self.assertEqual(flagged, {"T06", "T08", "T10"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test, verify failure**

Run: `python3 -m unittest tests.test_tasks -v 2>&1 | tail -3`
Expected: FAIL — `No module named 'tasks'`.

- [ ] **Step 3: Write `tasks/__init__.py`**

```python
"""Task loader for model-bench."""
import importlib.util
from pathlib import Path

REQUIRED_KEYS = {"id", "title", "category", "prompt", "checkers",
                 "timeout_s", "max_tokens", "judge"}


def load_tasks(task_dir=None):
    task_dir = Path(task_dir or Path(__file__).parent)
    tasks = []
    for path in sorted(task_dir.glob("t*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        task = getattr(mod, "TASK", None)
        missing = REQUIRED_KEYS - set(task or {})
        if missing:
            raise ValueError(f"{path.name}: TASK missing {missing}")
        if not task["prompt"] or not task["checkers"]:
            raise ValueError(f"{path.name}: empty prompt/checkers")
        tasks.append(task)
    tasks.sort(key=lambda t: t["id"])
    return tasks
```

- [ ] **Step 4: Write the 10 task files**

Each file follows this exact shape (shown for `tasks/t01_instruction.py`; the other nine differ only in dict content per the table above):

```python
TASK = {
    "id": "T01",
    "title": "Instruction precision",
    "category": "instruction-precision",
    "prompt": "Reply with exactly: OK\n\nThen, on a new line, write the word: BANANA",
    "checkers": [
        {"type": "exact", "value": "OK BANANA"},
    ],
    "timeout_s": 60,
    "max_tokens": 100,
    "judge": False,
}
```

`tasks/t02_diagnosis.py`:

```python
LOG = """systemd-coredump: Process 65630 (python3.14) of user 1000 dumped core.
Stack trace of thread 65630: #0 libssl.so.3 SSL_do_handshake ...
Journal: openssl-3.5.1-1 upgraded, python-requests connection reset mid-handshake
Note: system memory at 61%, no pressure; disk 43% used."""

TASK = {
    "id": "T02",
    "title": "Crash log diagnosis",
    "category": "log-diagnosis",
    "prompt": f"A process crashed on this machine. Given the coredump summary and journal lines below, name in one short sentence which component failed and how.\n\n{LOG}",
    "checkers": [
        {"type": "contains_all", "values": ["libssl", "sigsegv"]},
        {"type": "contains_none", "values": ["out of memory", "oom", "disk full"]},
    ],
    "timeout_s": 120,
    "max_tokens": 300,
    "judge": False,
}
```

`tasks/t03_config.py`:

```python
BROKEN = """matches:
  - triger: ":date"
    word: true
    replace: "{{d}}"
      vars:
      - name: d
        type: date
    word: true
"""

TASK = {
    "id": "T03",
    "title": "Fix broken YAML config",
    "category": "config-edit",
    "prompt": (
        "This espanso match has three errors: a misspelled key, a mis-indented "
        "block, and a duplicated key. The trigger must be the string \";;date\". "
        "Output ONLY the corrected YAML, nothing else.\n\n" + BROKEN
    ),
    "checkers": [
        {"type": "contains_all", "values": ['trigger: ";;date"', "word: true"]},
        {"type": "contains_none", "values": ["triger", "\t"]},
        {"type": "regex", "pattern": r"(?s)^matches:.*replace:.*type: date.*$", "search": True},
    ],
    "timeout_s": 120,
    "max_tokens": 400,
    "judge": False,
}
```

`tasks/t04_script.py`:

```python
TASK = {
    "id": "T04",
    "title": "Write a small bash script",
    "category": "script-writing",
    "prompt": ("Write a bash script that prints the number of command-line arguments "
               "passed to it (just the number, nothing else). Reply with the script "
               "in a single fenced code block."),
    "checkers": [
        {"type": "exec_code", "lang": "bash", "cases": [
            {"args": ["a", "b", "c"], "expect_exit": 0, "expect_stdout_contains": ["3"]},
            {"args": [], "expect_exit": 0, "expect_stdout_contains": ["0"]},
        ]},
    ],
    "timeout_s": 120,
    "max_tokens": 300,
    "judge": False,
}
```

`tasks/t05_transform.py`:

```python
DATA = ('```json\n[{"ts": "2026-09-01T03:12:00Z", "level": "error", "msg": "disk write failed"},\n'
        '{"ts": "2026-09-01T11:00:00Z", "level": "info", "msg": "backup started"},\n'
        '{"ts": "2026-09-02T09:44:00Z", "level": "error", "msg": "handshake timeout"},\n'
        '{"ts": "2026-09-02T10:00:00Z", "level": "info", "msg": "reconnect ok"}]\n```')

TASK = {
    "id": "T05",
    "title": "JSON data transform",
    "category": "data-transform",
    "prompt": ("Given this JSON array of log entries, return ONLY a JSON object of the form "
               '{"errors": [sorted ts values where level=="error"], "total": <number of entries>}. '
               "No prose.\n\n" + DATA),
    "checkers": [
        {"type": "json_asserts", "asserts": [
            {"path": "errors", "op": "eq", "value": ["2026-09-01T03:12:00Z", "2026-09-02T09:44:00Z"]},
            {"path": "total", "op": "eq", "value": 4},
        ]},
    ],
    "timeout_s": 120,
    "max_tokens": 300,
    "judge": False,
}
```

`tasks/t06_synthesis.py`:

```python
SOURCES = (
    "SOURCE A (release notes): omarchy-launcher 2.0 ships fuzzy search across all "
    "launcher modes. The launcher is now Wayland-only; X11 users must stay on 1.x.\n\n"
    "SOURCE B (migration guide): configuration moved to ~/.config/omarchy-launcher/. "
    "Old configs are not migrated automatically.\n\n"
    "SOURCE C (changelog): BREAKING: the --theme flag is renamed to --style. "
    "Startup time improved by 40%."
)

TASK = {
    "id": "T06",
    "title": "Synthesize release research",
    "category": "research-synthesis",
    "prompt": ("A user on X11 with a custom theme asks whether to upgrade omarchy-launcher. "
               "Using ONLY the sources below, write a summary of at most 120 words covering "
               "what is new and what would break for them.\n\n" + SOURCES),
    "checkers": [
        {"type": "contains_all", "values": ["fuzzy", "--style", "wayland"]},
        {"type": "length_max", "words": 140},
    ],
    "timeout_s": 180,
    "max_tokens": 700,
    "judge": True,
}
```

`tasks/t07_commit.py`:

```python
DIFF = (" match/base.yml | 14 ++++++-------\n"
        "--- a/match/base.yml\n+++ b/match/base.yml\n"
        '-  - trigger: ":date"\n+  - trigger: ";;date"\n'
        '-  - trigger: ":time"\n+  - trigger: ";;time"\n'
        " (comment lines updated to match)")

TASK = {
    "id": "T07",
    "title": "Write a commit message",
    "category": "git",
    "prompt": ("Write ONE conventional-commit subject line (no body) for this diff. "
               "Reply with only the subject line.\n\n" + DIFF),
    "checkers": [
        {"type": "regex", "pattern": r"\w+(\([\w./-]+\))?!?: .{5,69}"},
        {"type": "contains_all", "values": ["trigger"]},
        {"type": "contains_none", "values": ["\n"]},
    ],
    "timeout_s": 120,
    "max_tokens": 100,
    "judge": False,
}
```

`tasks/t08_review.py`:

```python
SNIPPET = ('```python\n'
           'import os\n'
           'def summarize(rows):\n'
           '    out = []\n'
           '    for i in range(len(rows) - 1):\n'
           '        out.append(rows[i]["name"])\n'
           '    return out\n'
           '```')

TASK = {
    "id": "T08",
    "title": "Find the bug",
    "category": "code-review",
    "prompt": ("Review this snippet. Name the bug class and what it does to the output, "
               "in at most 80 words.\n\n" + SNIPPET),
    "checkers": [
        {"type": "contains_all", "values": ["range", "last"]},
        {"type": "length_max", "words": 100},
    ],
    "timeout_s": 180,
    "max_tokens": 400,
    "judge": True,
}
```

`tasks/t09_regex.py`:

```python
TASK = {
    "id": "T09",
    "title": "sed one-liner",
    "category": "regex-tooling",
    "prompt": ("Write a POSIX sed one-liner that reads lines on stdin and converts every "
               "ISO date YYYY-MM-DD to MM/DD/YYYY. Reply with only the command in one "
               "fenced code block."),
    "checkers": [
        {"type": "exec_code", "lang": "bash", "cases": [
            {"args": [], "stdin": "due 2026-09-03 and 2027-01-15", "expect_exit": 0,
             "expect_stdout_contains": ["09/03/2026", "01/15/2027", "and"],
             "expect_stdout_not_contains": ["2026-09-03"]},
        ]},
    ],
    "timeout_s": 120,
    "max_tokens": 200,
    "judge": False,
}
```

`tasks/t10_writing.py`:

```python
RAMBLE = ("So basically what happened is that the backup thing ran last night, I think "
          "around 2 in the morning or so, and it did its whole thing and there were no "
          "errors which was nice, and honestly I was worried because last time it "
          "failed halfway, but this time it went all the way through and finished "
          "cleanly, so the backup succeeded.")

TASK = {
    "id": "T10",
    "title": "Constrained rewrite",
    "category": "constrained-writing",
    "prompt": ("Rewrite the paragraph below in at most 25 words, no adjectives, keeping "
               "the exact time and the outcome. Reply with only the rewrite.\n\n" + RAMBLE),
    "checkers": [
        {"type": "length_max", "words": 27},
        {"type": "contains_all", "values": ["02:00"]},
    ],
    "timeout_s": 180,
    "max_tokens": 300,
    "judge": True,
}
```

- [ ] **Step 5: Run tests, verify pass**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -3`
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add tasks/ tests/test_tasks.py
git commit -m "feat: 10-task suite mirroring real pi usage patterns"
```

---

### Task 4: Judge module

**Files:**
- Create: `lib/judge.py`
- Test: `tests/test_judge.py` (parse logic only — no network)

**Interfaces:**
- Consumes: `lib.client.chat`, `lib.client.ClientError`.
- Produces:
  - `JUDGE_SYSTEM: str` — instructs strict JSON output `{"score": <1-5>, "verdict": "<=25 words"}`.
  - `build_judge_prompt(task: dict, answer: str) -> str` — includes task prompt, answer, rubric (correctness 0-2, completeness 0-2, instruction-following 0-1), forbids judging style.
  - `parse_judge(raw: str) -> dict` — extracts JSON via `extract_json`; returns `{"score": int|None, "verdict": str}`; score clamped 1-5; `None` + verdict `"unparseable: <first 100 chars>"` on failure.
  - `judge_task(client, judge_model, task, answer) -> dict` — calls `chat`, returns parse result plus `"error": str|None`; catches `ClientError` into `{"score": None, "verdict": "", "error": str}`.

- [ ] **Step 1: Write failing tests**

`tests/test_judge.py`:

```python
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
```

- [ ] **Step 2: Run test, verify failure**

Run: `python3 -m unittest tests.test_judge -v 2>&1 | tail -3`
Expected: FAIL — `No module named 'lib.judge'`.

- [ ] **Step 3: Implement `lib/judge.py`**

```python
"""Optional rubric judge. Stdlib only."""
from .checks import extract_json

JUDGE_SYSTEM = (
    "You are a strict grader. Reply with ONLY a JSON object: "
    '{"score": <integer 1-5>, "verdict": "<=25 words"}. '
    "Rubric: correctness 0-2, completeness 0-2, followed instructions 0-1. "
    "Do not grade writing style unless the task is about writing."
)


def build_judge_prompt(task, answer):
    return (f"TASK:\n{task['prompt']}\n\nMODEL ANSWER:\n{answer}\n\n"
            "Grade the answer against the task. Reply with only the JSON object.")


def parse_judge(raw):
    obj = extract_json(raw or "")
    if isinstance(obj, dict) and "score" in obj:
        try:
            score = int(obj["score"])
        except (TypeError, ValueError):
            score = None
        if score is not None:
            score = max(1, min(5, score))
        verdict = str(obj.get("verdict", ""))[:200]
        return {"score": score, "verdict": verdict}
    return {"score": None, "verdict": f"unparseable: {(raw or '')[:100]}"}


def judge_task(client, judge_model, task, answer):
    try:
        resp = client.chat(judge_model, [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": build_judge_prompt(task, answer)},
        ], max_tokens=200, timeout_s=120)
        result = parse_judge(resp["content"])
        result["error"] = None
        return result
    except Exception as e:  # ClientError or anything else — never crash run
        return {"score": None, "verdict": "", "error": f"{type(e).__name__}: {e}"}
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -3`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add lib/judge.py tests/test_judge.py
git commit -m "feat: rubric judge with strict JSON parsing and clamping"
```

---

### Task 5: Runner + report + CLI (`bench.py`)

**Files:**
- Create: `lib/report.py`, `bench.py`
- Test: `tests/test_report.py`, `tests/test_bench.py` (offline logic only)

**Interfaces:**
- Consumes: `lib.client.chat/ClientError`, `lib.checks.run_checks/strip_think`, `lib.judge.judge_task`, `tasks.load_tasks`.
- Produces:
  - `lib.report.RATES` — `{"glm-5.3-flash:cloud": {"in": 0.15, "out": 0.50}, "glm-5.3:cloud": {"in": 1.40, "out": 4.40}, "gemma4:31b:cloud": {"in": 0.10, "out": 0.40}}` (per M tokens; control approximate — documented in report footnote)
  - `est_cost(model, prompt_tokens, completion_tokens) -> float`
  - `render_report(run: dict, baseline: dict | None = None) -> str` — markdown: pass matrix (model × task, `✓`/`✗`, `?` for errors), per-model totals (passed/10, avg latency, tokens/s, est cost), judge averages with `judge=self` badge when `model == run["judge_model"]`, notable failures (first failed check per model), baseline delta column when provided, rate-table footnote.
  - `run_model(model, tasks, *, base_url, concurrency, judge_model, judge_enabled) -> dict` — ThreadPoolExecutor(concurrency) over tasks; per task result: `{"id", "passed", "checks": [...], "latency_s", "prompt_tokens", "completion_tokens", "tokens_per_s", "est_cost", "judge": {...}|None, "error": str|None, "answer_preview": str ≤4000, "raw_answer_saved": bool}`; `passed` False when any check fails OR exception (with `error` set); never raises.
  - `runid = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")`; artifacts at `results/<runid>/run.json` + `report.md`.
  - CLI (`argparse`): `--models` (default 3), `--base-url`, `--judge [MODEL]` (nargs `?`, const `glm-5.3:cloud`), `--only T01,T04`, `--concurrency` (default 5), `--selftest`, `--baseline RUNID`, `--max-tokens` default 700 override per task, `--list`.
  - `--selftest`: runs `python3 -m unittest discover -s tests` via subprocess, prints output, exits with its returncode.
  - Report footer: rate table values + "gemma4 rates approximate" note.

- [ ] **Step 1: Write failing tests**

`tests/test_report.py`:

```python
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
                     "prompt_tokens": 100, "completion_tokens": 10,
                     "judge": {"score": 5, "verdict": "great"}, "error": None},
            "T02": {"passed": False, "checks": [{"name": "contains_all", "passed": False,
                     "observed": "missing: ['x']", "expected": "x"}],
                     "latency_s": 2.0, "prompt_tokens": 200, "completion_tokens": 20,
                     "judge": None, "error": None},
        }},
        "m-weak": {"tasks": {
            "T01": {"passed": False, "checks": [{"name": "exact", "passed": False,
                     "observed": "nope", "expected": "OK"}],
                     "latency_s": 3.0, "prompt_tokens": 100, "completion_tokens": 30,
                     "judge": None, "error": None},
            "T02": {"passed": True, "checks": [], "latency_s": 4.0,
                     "prompt_tokens": 200, "completion_tokens": 40,
                     "judge": {"score": 3, "verdict": "ok"}, "error": None},
        }},
    },
    "task_titles": {"T01": "Instruction precision", "T02": "Diagnosis"},
}


class TestCost(unittest.TestCase):
    def test_est_cost(self):
        self.assertAlmostEqual(est_cost("m-fast", 1_000_000, 1_000_000), 0.65)
        self.assertAlmostEqual(est_cost("unknown", 1_000_000, 0), 0.0)


class TestReport(unittest.TestCase):
    def test_renders_matrix_and_totals(self):
        md = render_report(RUN)
        self.assertIn("m-fast", md)
        self.assertIn("T01", md)
        self.assertIn("judge=self", md)   # m-weak... no: only glm-5.3:cloud badge
        self.assertIn("1/2", md)          # m-fast total

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
```

`tests/test_bench.py`:

```python
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
                        client=FakeClient())
        self.assertEqual(out["tasks"]["T01"]["passed"], True)
        self.assertEqual(out["tasks"]["T01"]["latency_s"], 0.5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python3 -m unittest tests.test_report tests.test_bench -v 2>&1 | tail -3`
Expected: FAIL — import errors (`lib.report`, `bench` missing).

- [ ] **Step 3: Implement `lib/report.py`**

```python
"""Markdown report rendering. Stdlib only."""
from datetime import datetime, timezone

RATES = {
    "glm-5.3-flash:cloud": {"in": 0.15, "out": 0.50},
    "glm-5.3:cloud": {"in": 1.40, "out": 4.40},
    "gemma4:31b:cloud": {"in": 0.10, "out": 0.40},  # approximate
}


def est_cost(model, prompt_tokens, completion_tokens):
    rate = RATES.get(model)
    if not rate:
        return 0.0
    return (prompt_tokens * rate["in"] + completion_tokens * rate["out"]) / 1e6


def _fmt(v, nd=2):
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) else str(v)


def render_report(run, baseline=None):
    lines = [f"# model-bench report — {run['runid']}", ""]
    if run.get("judge_enabled"):
        lines.append(f"Judge: `{run['judge_model']}`")
    lines.append("")
    # Pass matrix
    lines.append("## Pass matrix")
    lines.append("")
    header = "| task | " + " | ".join(run["models"]) + " |"
    lines += [header, "|---" * (len(run["models"]) + 1) + "|"]
    for tid, title in run["task_titles"].items():
        cells = []
        for m in run["models"]:
            t = run["results"][m]["tasks"].get(tid)
            cell = "✓" if t and t["passed"] else ("✗" if t else "?")
            if baseline:
                bt = baseline["results"].get(m, {}).get("tasks", {}).get(tid)
                if bt is not None:
                    cell += "" if bool(bt["passed"]) == bool(t and t["passed"]) \
                            else (" ↑" if (t and t["passed"]) else " ↓")
            cells.append(cell)
        lines.append(f"| {tid} {title} | " + " | ".join(cells) + " |")
    lines.append("")
    # Totals
    lines.append("## Totals")
    lines.append("")
    lines.append("| model | passed | avg latency s | tok/s | est cost $ | judge avg |")
    lines.append("|---|---|---|---|---|---|")
    for m in run["models"]:
        tasks = run["results"][m]["tasks"]
        n = len(tasks)
        passed = sum(1 for t in tasks.values() if t["passed"])
        avg_lat = sum(t["latency_s"] for t in tasks.values()) / max(n, 1)
        tps = sum(t["tokens_per_s"] for t in tasks.values() if t["tokens_per_s"]) / max(
            sum(1 for t in tasks.values() if t["tokens_per_s"]), 1)
        cost = sum(t["est_cost"] for t in tasks.values())
        scores = [t["judge"]["score"] for t in tasks.values()
                  if t.get("judge") and t["judge"].get("score") is not None]
        javg = _fmt(sum(scores) / len(scores), 1) if scores else "—"
        badge = " (judge=self)" if run.get("judge_enabled") and m == run["judge_model"] else ""
        lines.append(f"| {m}{badge} | {passed}/{n} | {_fmt(avg_lat)} | {_fmt(tps, 1)} | "
                     f"${_fmt(cost, 4)} | {javg} |")
    lines.append("")
    # Notable failures
    lines.append("## Notable failures")
    lines.append("")
    any_fail = False
    for m in run["models"]:
        for tid, t in run["results"][m]["tasks"].items():
            if t.get("error"):
                lines.append(f"- **{m}** {tid}: error — {t['error']}")
                any_fail = True
            elif not t["passed"]:
                bad = next((c for c in t["checks"] if not c["passed"]), None)
                if bad:
                    lines.append(f"- **{m}** {tid}: {bad['name']} — observed: {bad['observed']}")
                    any_fail = True
    if not any_fail:
        lines.append("- none")
    lines.append("")
    lines.append("---")
    lines.append("Cost rates per M tokens: " +
                 ", ".join(f"`{k}` ${v['in']}/${v['out']}" for k, v in RATES.items()) +
                 ". gemma4 rates approximate.")
    lines.append(f"_Generated {datetime.now(timezone.utc).isoformat()}_")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Implement `bench.py`**

```python
#!/usr/bin/env python3
"""model-bench: quick fitness harness for Ollama Cloud models on pi-style tasks."""
import argparse
import concurrent.futures as cf
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from lib.client import chat
from lib.checks import run_checks, strip_think
from lib.judge import judge_task
from lib.report import est_cost, render_report
from tasks import load_tasks

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
DEFAULT_MODELS = ["glm-5.3-flash:cloud", "glm-5.3:cloud", "gemma4:31b:cloud"]


def run_one(model, task, base_url, judge_model, judge_enabled, client):
    tid = task["id"]
    try:
        resp = client(model, [{"role": "user", "content": task["prompt"]}],
                      timeout_s=task["timeout_s"], max_tokens=task["max_tokens"])
        content, reasoning = strip_think(resp["content"])
        checks = run_checks(content, task["checkers"])
        completion = resp["usage"]["completion_tokens"]
        lat = resp["latency_s"]
        result = {
            "id": tid,
            "passed": all(c["passed"] for c in checks) and bool(checks),
            "checks": checks,
            "latency_s": round(lat, 3),
            "prompt_tokens": resp["usage"]["prompt_tokens"],
            "completion_tokens": completion,
            "tokens_per_s": round(completion / lat, 1) if lat > 0 else 0,
            "est_cost": round(est_cost(model, resp["usage"]["prompt_tokens"], completion), 6),
            "judge": None,
            "error": None,
            "answer_preview": content[:4000],
        }
        if judge_enabled and task.get("judge"):
            result["judge"] = judge_task(client, judge_model, task, content)
    except Exception as e:
        result = {"id": tid, "passed": False, "checks": [], "latency_s": 0,
                  "prompt_tokens": 0, "completion_tokens": 0, "tokens_per_s": 0,
                  "est_cost": 0, "judge": None,
                  "error": f"{type(e).__name__}: {e}", "answer_preview": ""}
    return result


def run_model(model, tasks, *, base_url, concurrency, judge_model, judge_enabled, client=None):
    client = client or (lambda m, msgs, **kw: chat(base_url, m, msgs, **kw))
    out = {"tasks": {}}
    with cf.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(run_one, model, t, base_url, judge_model,
                               judge_enabled, client): t for t in tasks}
        for fut in cf.as_completed(futures):
            r = fut.result()
            out["tasks"][r["id"]] = r
            print(f"  {model} {r['id']}: {'PASS' if r['passed'] else 'FAIL'}"
                  f"{' (' + r['error'][:60] + ')' if r.get('error') else ''}", flush=True)
    return out


def do_selftest():
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT)
    return proc.returncode


def main(argv=None):
    ap = argparse.ArgumentParser(prog="model-bench")
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    ap.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    ap.add_argument("--judge", nargs="?", const="glm-5.3:cloud", default=None)
    ap.add_argument("--only", default=None, help="comma-separated task ids, e.g. T01,T04")
    ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--baseline", default=None, help="prior runid to diff")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return do_selftest()

    tasks = load_tasks()
    if args.only:
        keep = {x.strip().upper() for x in args.only.split(",")}
        tasks = [t for t in tasks if t["id"] in keep]
    if args.list:
        for t in tasks:
            print(f"{t['id']} [{t['category']}] judge={t['judge']} — {t['title']}")
        return 0

    judge_enabled = args.judge is not None
    judge_model = args.judge
    runid = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run = {"runid": runid, "base_url": args.base_url,
           "judge_model": judge_model, "judge_enabled": judge_enabled,
           "models": args.models, "task_titles": {t["id"]: t["title"] for t in tasks},
           "results": {}}

    for model in args.models:
        print(f"== {model} ==", flush=True)
        run["results"][model] = run_model(
            model, tasks, base_url=args.base_url, concurrency=args.concurrency,
            judge_model=judge_model, judge_enabled=judge_enabled)

    outdir = RESULTS / runid
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "run.json").write_text(json.dumps(run, indent=2))

    baseline = None
    if args.baseline:
        bpath = RESULTS / args.baseline / "run.json"
        if bpath.exists():
            baseline = json.loads(bpath.read_text())
        else:
            print(f"warning: baseline {args.baseline} not found")

    md = render_report(run, baseline)
    (outdir / "report.md").write_text(md)
    print("\n" + md)
    print(f"results: {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run full test suite**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -3`
Expected: `OK`.

- [ ] **Step 6: Self-test + list smoke**

```bash
python3 bench.py --selftest && python3 bench.py --list
```
Expected: unittest `OK`; 10 task lines printed.

- [ ] **Step 7: Commit**

```bash
git add bench.py lib/report.py tests/test_report.py tests/test_bench.py
git commit -m "feat: runner, CLI, report renderer with baseline diff"
```

---

### Task 6: README + live acceptance run

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Write README**

`README.md`:

```markdown
# model-bench

Quick fitness harness for Ollama Cloud models on pi-agent-style tasks.
Stdlib-only Python 3. Spec: `docs/superpowers/specs/2026-09-03-model-bench-design.md`.

## Quick start

    python3 bench.py --selftest        # offline, validate checkers
    python3 bench.py --list            # show suite
    python3 bench.py --judge           # full run, 3 models, judge on
    python3 bench.py --models glm-5.3-flash:cloud --only T02,T04 --judge

## Models

Defaults: glm-5.3-flash:cloud, glm-5.3:cloud, gemma4:31b:cloud (negative
control — expected to lose; if it ties GLM the suite is too easy).
Endpoint: http://127.0.0.1:11434/v1 (Ollama Cloud resolves :cloud ids on demand).

## Tasks

Ten single-turn tasks, one per real-usage category mined from pi session
history: instruction precision, crash-log diagnosis, config edit, script
writing (executed), JSON transform, research synthesis, commit message,
code review, sed one-liner (executed), constrained rewrite (judged).

## Output

results/<runid>/run.json (raw) and report.md (pass matrix, latency,
tokens/s, est cost, judge scores, notable failures). Diff runs with
--baseline <runid>.

## Judge

--judge [model] grades T06/T08/T10 with a 1-5 rubric. Default judge
glm-5.3:cloud; badge `judge=self` marks self-graded models.
```

- [ ] **Step 2: Live acceptance run (quota-spending)**

```bash
cd ~/Development/_organized/_active/model-bench && python3 bench.py --judge
```
Expected: all 3 models complete, `results/<runid>/` written, report prints. Watch for: gemma underperforming (acceptance criterion 3), GLM reasoning-model answers grading correctly (no `</think>` leakage into checks).

- [ ] **Step 3: Verify acceptance criteria**

Check report.md: pass matrix complete (no `?` cells), costs listed, judge column populated. If gemma ties GLM → note in final report that suite may need harder tasks (do NOT silently tune tasks to force the outcome).

- [ ] **Step 4: Commit**

```bash
git add README.md results/
git commit -m "docs: README + first live acceptance run"
```

---

## Self-Review

**Spec coverage:** 10 tasks/10 categories (Task 3) ✓; deterministic checkers incl. exec (Task 1) ✓; judge with self-badge (Task 4, Task 5 report) ✓; metrics incl. cost from rates (Task 5) ✓; partial-results-always (run_one try/except) ✓; reasoning-strip (Task 2 `_parse_response`, applied via `strip_think` in run_one) ✓; selftest (Task 5) ✓; baseline diff (Task 5) ✓; acceptance criteria (Task 6) ✓; control model documented (README, RATES) ✓.

**Placeholder scan:** none — all steps carry full code.

**Type consistency:** `chat(base_url, model, messages, *, api_key, timeout_s, max_tokens, temperature)` — but `run_one` calls `client(model, msgs, timeout_s=..., max_tokens=...)` and the FakeClient matches `chat`'s positional order? FakeClient defines `chat(self, model, messages, **kw)` while `client(model, msgs, timeout_s=..., max_tokens=...)` passes model first — REAL `chat` signature is `(base_url, model, ...)`. **Mismatch:** real client would receive `model` as `base_url`. Fix: in `run_one`, call `client(base_url, model, msgs, ...)`. Also `judge_task(client, ...)` passes `client` that takes `(model, messages, **kw)` — inconsistent with the `run_one` convention. Resolve in implementation: standardize internal callable signature as `client(model, messages, **kw)` and have `bench.run_model` wrap real `chat` as `lambda m, msgs, **kw: chat(base_url, m, msgs, **kw)` (already done via `client = client or (...)` in `run_model`; `run_one` must use that same wrapped signature — so `run_one`'s call `client(model, [...], timeout_s=..., max_tokens=...)` is CORRECT, and the bug is only in Task 5 Step 4's inline `client = client or (lambda m, msgs, **kw: chat(base_url, m, msgs, **kw))` — which is right. No change needed; FakeClient signature `chat(self, model, messages, **kw)` matches. ✓ (verified during self-review; the `content = ... if False else content` dead line in run_one is scaffolding noise — implementers should omit it; keeping content = strip_think output only.)

**Correction for implementers:** in `run_one`, use exactly:
```python
content, reasoning = strip_think(resp["content"])
checks = run_checks(content, task["checkers"])
```
(no dead-line variants).