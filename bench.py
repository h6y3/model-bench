#!/usr/bin/env python3
"""model-bench: quick fitness harness for Ollama Cloud models on pi-style tasks."""
import argparse
import concurrent.futures as cf
import json
import subprocess
import sys
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
    """client signature: client(model, messages, **kw) -> chat result dict."""
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
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
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