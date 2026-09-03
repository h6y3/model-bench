"""Deterministic answer checkers for model-bench. Stdlib only."""
import json
import re
import subprocess
import tempfile
from pathlib import Path

THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)
FENCE_RE = re.compile(r"```[^\n]*\n(.*?)\n?```", re.DOTALL)


def strip_think(text):
    """Split '<think>...</think>' spans out of content. Returns (content, reasoning)."""
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
