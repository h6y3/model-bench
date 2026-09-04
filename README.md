# model-bench

**A fast, stdlib-only fitness harness for language models on real coding-agent work — built from the actual task history of an Omarchy Linux power user.**

Most benchmarks measure trivia. model-bench measures the things you actually ask a coding agent to do on a daily-driver Linux system: diagnose a crash from a coredump, fix a broken YAML config, write a small script, review a diff, follow an instruction *exactly*. It was built to answer one question repeatedly and cheaply:

> *"Is this open-source model, served through Ollama Cloud, fit for my pi-agent-style work — and is it worth its tokens?"*

A full comparison across 3–4 models runs in 10–20 minutes for pennies, produces a side-by-side pass matrix with latency / throughput / cost, and ships with a deliberately weak **negative control** so you can tell a discriminating benchmark from a rubber stamp.

---

## Why model-bench

- **Tasks mined from real usage.** The 22-task suite was derived from 45 logged coding-agent sessions on an Omarchy Linux system — system diagnosis, config editing, research synthesis, GitHub work, script writing, instruction precision. No riddles, no trivia.
- **Deterministic by default.** Answers are graded by checkers: exact match, substring sets, regex, JSON path assertions, and — for code tasks — the harness *executes* the model's output in a sandbox and checks stdout/exit codes. No vibes.
- **Optional judge, honestly labeled.** Open-ended tasks can be graded by a rubric judge model. When the judge grades itself, the report badges it (`judge=self`).
- **Negative-control doctrine.** The suite ships with a weak model (`gemma4:31b:cloud`) that is *expected* to lose. If the control ties your frontier model, the benchmark is too easy — and you'll know.
- **Zero dependencies.** Python 3 stdlib only. No venv, no pip install, no YAML library hand-rolled in the source tree. Clone and run.

## Quick start

```bash
git clone <this repo> && cd model-bench

python3 bench.py --selftest        # validate all checkers offline, no API calls
python3 bench.py --list            # show the 16-task suite
python3 bench.py --judge           # full run: 3 default models + judge
python3 bench.py --models glm-5.3-flash:cloud --only T02,T04 --judge
python3 bench.py --baseline 20260903-223427   # diff against a prior run
```

Requires an Ollama endpoint (default `http://127.0.0.1:11434/v1`). Cloud model IDs
(`*:cloud`) resolve on demand through Ollama Cloud — including models that do not
appear in `/v1/models`. API key defaults to `ollama`; override for remote endpoints.

Results land in `results/<runid>/` — `run.json` (machine-readable, everything)
and `report.md` (the comparison). `docs/example-report.md` shows a real one.

## The suite: 22 tasks, one per real-usage category

| ID | Category | Modeled on | Grading |
|----|----------|-----------|---------|
| T01 | instruction precision | "Reply with exactly: OK" | exact |
| T02 | crash-log diagnosis | systemd-coredump triage | substring facts |
| T03 | config edit | broken YAML repair | line-level assertions |
| T04 | script writing | small bash utilities | **executed**, stdout/exit checked |
| T05 | data transform | JSON → JSON | JSON path assertions |
| T06 | research synthesis | multi-source research asks | facts + judge |
| T07 | commit message | conventional commits | format regex |
| T08 | code review | find the planted bug | facts + judge |
| T09 | regex/one-liner | sed pipelines | **executed** against case lists |
| T10 | constrained writing | rewrite under length rules | length + judge |
| T11 | dependency reconcile | installed-vs-required versions | JSON assertions |
| T12 | config-schema diagnosis | silent config rejection | facts + distractors |
| T13 | skill authoring | YAML frontmatter contracts | structure regex |
| T14 | install guidance | README-comprehension | facts + banned answers |
| T15 | multi-file consistency | cross-file renames | dual assertions |
| T16 | log correlation | notifications-vs-service env | facts + judge |
| T17 | email triage | a shipped-order notice | verdict regex |
| T18 | email triage | a request for a document | verdict + specific title |
| T19 | email triage | a chatty progress report | three-line format |
| T20 | email triage | "Action Required" over a finished payment | verdict regex |
| T21 | email triage | the same call with no examples given | verdict regex |
| T22 | email triage | a delivery that *does* need you | verdict + specific title |

Every task is a small, readable Python file in [`tasks/`](tasks/) — open one, you'll
get it in thirty seconds. Tasks are single-turn with context embedded in the prompt:
fast, deterministic, and fair across models regardless of tool-calling ability.

## Sample results

Real run (2026-09-03, judge on, Ollama Cloud). Costs estimated from per-M token rates:

| model | pass | avg latency | tok/s | run cost |
|---|---|---|---|---|
| glm-5.3-flash:cloud | 15/16 | 5.3s | 126 | $0.006 |
| kimi-k2.7-code:cloud | **16/16** | 6.6s | 65 | ~$0.05 |
| glm-5.3:cloud | 15/16 | 16.1s | 59 | $0.064 |
| deepseek-v4-flash:cloud | 12/16 | 3.3s | 119 | $0.004 |
| gemma4:31b:cloud (control) | 12/16 | 1.2s | 57 | — |

The leaderboard told a clean story: kimi-k2.7-code was the only model to pass
all 16 tasks — including T13 skill authoring, where every GLM tier failed;
the fast GLM tier matched the heavy tier's correctness at 1/10 the cost; the
cheap backup model (deepseek-v4-flash) lost exactly the reasoning-flavored
tasks (crash diagnosis, bug-finding); the control lost the code tasks. See
[`docs/example-report.md`](docs/example-report.md) for the full
matrix, and [docs/METHODOLOGY.md](docs/METHODOLOGY.md) for what the numbers
do and don't mean.

## Judge mode

`--judge [model]` grades the open-ended tasks (T06/T08/T10/T16) with a 1–5 rubric:
correctness 0–2, completeness 0–2, instruction adherence 0–1. Judge output must be
strict JSON; malformed grades are recorded as unparseable, never crash a run.

Caveat, stated plainly: LLM judges are lenient. The deterministic checks carry the
real signal — treat judge scores as a tiebreaker, not a verdict. When the judge
model is also under test, the report marks it `judge=self`.

## Baselines and regressions

Every run writes a `runid`. Point a later run at an earlier one:

```bash
python3 bench.py --baseline 20260903-223427
```

The pass matrix gains ↑/↓ markers per model×task, so a provider-side model update
that silently regresses your daily driver shows up as a red arrow, not a hunch.

## Adding things

- **A model:** `python3 bench.py --models <id>`. Add a cost entry to `RATES` in
  [`lib/report.py`](lib/report.py) to track spend.
- **A task:** copy a file in [`tasks/`](tasks/), set a fresh `TXX` id, pick checkers
  from the catalog in [`lib/checks.py`](lib/checks.py), and flip `judge: true` if
  the answer is open-ended. The suite self-validates on load.
- **A checker:** [`lib/checks.py`](lib/checks.py) — dispatch on `type`, return
  `{"passed": bool, "observed": ..., "expected": ...}` per check.

Detailed walkthroughs: [docs/CUSTOMIZING.md](docs/CUSTOMIZING.md).

## Architecture

```
bench.py              CLI, orchestration, partial-result guarantees
lib/client.py         OpenAI-compatible chat client (reasoning-aware)
lib/checks.py         8 deterministic checker types + code execution
lib/judge.py          strict-JSON rubric judge
lib/report.py         markdown report renderer + cost rates
tasks/t01..t22.py     the suite
tests/                36 offline unit/integration tests
```

Notable engineering details, learned the hard way and documented in
[docs/METHODOLOGY.md](docs/METHODOLOGY.md):

- **Reasoning models can starve.** A reasoning-heavy model can burn its entire
  token budget thinking and emit an empty answer. The harness captures
  `finish_reason` and flags `truncated` so starvation is measurable, not invisible.
- **Ambiguity burns reasoning budgets.** One under-specified task drove a model
  from 5.8s to 53.7s of wall time at 4000+ reasoning tokens — with *no* answer
  emitted. Ambiguous prompts are a hidden cost multiplier for reasoning models.
- **Knowledge must be in the prompt.** A task that expects a model to know your
  internal schema rules measures memory, not competence. Test knowledge you
  provided, not knowledge you assume.
- **A task every model passes measures your prompt, not the model.** The six
  email-triage tasks (T17-T22) were added after a real lane filed eleven
  useless items in six days. Every model tested passes all six — including the
  weak control, and including the two written specifically to be hard. That is
  a result, not a wasted afternoon: the judgement was never model-limited, the
  rule had simply never been written down. Keep such tasks as regression pins;
  do not use them to choose between candidates.

## FAQ

**Why no tool-use / agentic loop?** Deliberate. Tool-call loops are slow, flaky,
and unfair across models with different tool-calling maturity. model-bench tests
the *reasoning and instruction-following* that survives inside such loops.

**Why is the control allowed to be so weak?** That's its job. A benchmark that
the control passes isn't discriminating anything. If gemma ties your frontier
model, add harder tasks before drawing conclusions.

**Does it work with non-Ollama endpoints?** Anything OpenAI-compatible
(`/v1/chat/completions`) — point `--base-url` at it.

**Why stdlib-only?** So the harness itself is never the setup cost. Clone, run.

## Roadmap

- [ ] Streaming TTFB metrics (nice-to-have, not needed for triage)
- [ ] Optional multi-turn tool-use tier behind a flag
- [ ] Historical cost aggregation across baselines

## License

[MIT](LICENSE) — © 2026 Han Yuan.