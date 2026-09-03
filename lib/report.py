"""Markdown report rendering. Stdlib only."""
from datetime import datetime, timezone

RATES = {
    "glm-5.3-flash:cloud": {"in": 0.15, "out": 0.50},
    "glm-5.3:cloud": {"in": 1.40, "out": 4.40},
    "gemma4:31b:cloud": {"in": 0.10, "out": 0.40},  # approximate
    "deepseek-v4-flash:cloud": {"in": 0.22, "out": 0.66},
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
    if baseline:
        lines.append(f"Baseline comparison vs `{baseline['runid']}` — ↑ new pass, ↓ lost pass")
        lines.append("")
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
        tps_vals = [t["tokens_per_s"] for t in tasks.values() if t["tokens_per_s"]]
        tps = sum(tps_vals) / max(len(tps_vals), 1)
        cost = sum(t["est_cost"] for t in tasks.values())
        scores = [t["judge"]["score"] for t in tasks.values()
                  if t.get("judge") and t["judge"].get("score") is not None]
        javg = f"{sum(scores) / len(scores):.1f}" if scores else "—"
        badge = " (judge=self)" if run.get("judge_enabled") and m == run["judge_model"] else ""
        lines.append(f"| {m}{badge} | {passed}/{n} | {avg_lat:.2f} | {tps:.1f} | "
                     f"${cost:.4f} | {javg} |")
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