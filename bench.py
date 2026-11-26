#!/usr/bin/env python3
"""model-bench: quick fitness harness for Ollama Cloud models on pi-style tasks."""
import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from lib.client import DEFAULT_TEMPERATURE, chat
from lib.checks import run_checks, strip_think
from lib.judge import judge_task
from lib.report import est_cost, render_report
from tasks import load_tasks

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
DEFAULT_MODELS = ["glm-5.3-flash:cloud", "kimi-k2.7-code:cloud", "gemma4:31b:cloud"]
OLLAMA_URL = "http://127.0.0.1:11434/v1"
OPENROUTER_URL = "https://openrouter.ai/api/v1"


def make_client(base_url, api_key="ollama", extra_body=None):
    """A client(model, messages, **kw) bound to one endpoint, key and body extras."""
    def client(model, messages, **kw):
        return chat(base_url, model, messages, api_key=api_key, extra_body=extra_body, **kw)
    return client


def run_one(model, task, base_url, judge_model, judge_enabled, client, judge_client=None):
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
            "truncated": resp.get("finish_reason") == "length",
            "finish_reason": resp.get("finish_reason"),
            "max_tokens": task["max_tokens"],
            "checks": checks,
            "latency_s": round(lat, 3),
            "prompt_tokens": resp["usage"]["prompt_tokens"],
            "completion_tokens": completion,
            "tokens_per_s": round(completion / lat, 1) if lat > 0 else 0,
            "est_cost": round(resp["cost"] if resp.get("cost") is not None
                              else est_cost(model, resp["usage"]["prompt_tokens"], completion), 6),
            "cost_source": "billed" if resp.get("cost") is not None else "rate",
            "served_model": resp.get("served_model"),
            "served_provider": resp.get("served_provider"),
            "judge": None,
            "error": None,
            "answer_preview": content[:4000],
        }
        if judge_enabled and task.get("judge"):
            result["judge"] = judge_task(judge_client or client, judge_model, task, content)
    except Exception as e:
        result = {"id": tid, "passed": False, "checks": [], "latency_s": 0,
                  "prompt_tokens": 0, "completion_tokens": 0, "tokens_per_s": 0,
                  "est_cost": 0, "judge": None,
                  "error": f"{type(e).__name__}: {e}", "answer_preview": ""}
    return result


def run_model(model, tasks, *, base_url, concurrency, judge_model, judge_enabled, client=None,
              judge_client=None):
    """client signature: client(model, messages, **kw) -> chat result dict.

    judge_client grades through a different endpoint when given (an OpenRouter
    run still judges with an Ollama model); otherwise the judge uses client."""
    client = client or make_client(base_url)
    out = {"tasks": {}}
    with cf.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(run_one, model, t, base_url, judge_model,
                               judge_enabled, client, judge_client): t for t in tasks}
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


def preflight(models, base_url, client=None):
    """Probe each model with a tiny request; abort before a wasted full run.

    Ollama cloud catalog churns (mass retirements June/July 2026), so a model
    id that worked last week may be gone. Fail loud here, not per-task.
    """
    client = client or make_client(base_url)
    dead = []
    for model in models:
        try:
            # 64, not 8: a reasoning model spends a short budget thinking and
            # returns nothing, which is a live model, not a dead one.
            client(model, [{"role": "user", "content": "Reply with exactly: OK"}],
                   max_tokens=64, timeout_s=60.0)
            print(f"preflight ok: {model}", flush=True)
        except Exception as e:
            dead.append(f"{model} — {e}")
    if dead:
        print("PREFLIGHT FAILED — model(s) unusable:", file=sys.stderr)
        for d in dead:
            print(f"  {d}", file=sys.stderr)
        print("Fix: pick another model, or check ollama.com deprecation table.",
              file=sys.stderr)
        sys.exit(1)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="model-bench")
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    ap.add_argument("--base-url", default=None,
                    help=f"OpenAI-compatible endpoint (default {OLLAMA_URL})")
    ap.add_argument("--openrouter", action="store_true",
                    help="run through OpenRouter: its URL, key from OPENROUTER_API_KEY, "
                         "billed cost per call; the judge stays on local Ollama")
    ap.add_argument("--api-key-env", default=None,
                    help="name of the environment variable holding the API key "
                         "(the key itself never goes on the command line)")
    ap.add_argument("--provider", default=None,
                    help='OpenRouter routing as JSON, e.g. '
                         '\'{"only":["alibaba"],"allow_fallbacks":false}\'')
    ap.add_argument("--judge-base-url", default=None,
                    help="endpoint for the judge model (default: --base-url, or local "
                         "Ollama with --openrouter)")
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
    base_url = args.base_url or (OPENROUTER_URL if args.openrouter else OLLAMA_URL)
    key_env = args.api_key_env or ("OPENROUTER_API_KEY" if args.openrouter else None)
    api_key = "ollama"
    if key_env:
        api_key = os.environ.get(key_env, "")
        if not api_key:
            print(f"error: ${key_env} is empty; export the key there", file=sys.stderr)
            return 2
    extra = {}
    if args.provider:
        try:
            extra["provider"] = json.loads(args.provider)
        except json.JSONDecodeError as e:
            print(f"error: --provider is not JSON: {e}", file=sys.stderr)
            return 2
    if args.openrouter:
        extra["usage"] = {"include": True}
    client = make_client(base_url, api_key, extra or None)
    judge_url = args.judge_base_url or (OLLAMA_URL if args.openrouter else base_url)
    # The provider pin is for the model under test; the judge model may not be
    # served by that provider, so it never inherits the pin.
    judge_client = (make_client(base_url, api_key,
                                {k: v for k, v in extra.items() if k != "provider"} or None)
                    if judge_url == base_url else make_client(judge_url))
    preflight(args.models, base_url, client)
    runid = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run = {"runid": runid, "base_url": base_url,
           "judge_model": judge_model, "judge_enabled": judge_enabled,
           "models": args.models, "task_titles": {t["id"]: t["title"] for t in tasks},
           "settings": {"temperature": DEFAULT_TEMPERATURE,
                        "concurrency": args.concurrency, "only": args.only,
                        "provider": extra.get("provider"),
                        "api_key_env": key_env,
                        "judge_base_url": judge_url if judge_enabled else None},
           "results": {}}

    for model in args.models:
        print(f"== {model} ==", flush=True)
        run["results"][model] = run_model(
            model, tasks, base_url=base_url, concurrency=args.concurrency,
            judge_model=judge_model, judge_enabled=judge_enabled,
            client=client, judge_client=judge_client)

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