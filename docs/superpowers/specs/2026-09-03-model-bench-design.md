# model-bench design

Date: 2026-09-03
Status: approved in chat, pending spec review

## Purpose

Fast, repeatable harness to assess whether an open-source model served via
Ollama Cloud is fit for the tasks the user actually gives their pi coding
agent. Optimized for triage: a full comparison across 3 models in under
~10 minutes and modest quota.

Derived from analysis of 45 real pi sessions (2026-09-02..03). Usage profile:
system diagnosis from logs, config file editing, research synthesis, install/
setup guidance, GitHub operations, script writing, instruction precision.

## Models under test

| Role | Model ID | Notes |
|------|----------|-------|
| Primary (fast) | `glm-5.3-flash:cloud` | user's pi default |
| Heavy | `glm-5.3:cloud` | user's hard-task model |
| Negative control | `gemma4:31b:cloud` | weakest cloud tier; id `gemma4:31b-cloud` resolves to same backend |

Rationale for control: a model expected to underperform proves the harness
discriminates. If gemma scores near parity with GLM, the suite is too easy.

Default endpoint: `http://127.0.0.1:11434/v1` (OpenAI-compatible). Auth
header `Authorization: Bearer ollama` (matches pi models.json; harmless
locally, required if endpoint is remote).

## Non-goals (YAGNI)

- No multi-turn tool-use simulation (flaky, unfair grading).
- No streaming/TTFB metrics.
- No database, web UI, or persistent aggregation beyond per-run artifacts.
- No local models in the default suite.

## Architecture

```
model-bench/
├── bench.py              # CLI, orchestration, reporting
├── lib/
│   ├── client.py         # chat client (urllib), retry, usage + reasoning capture
│   ├── checks.py         # deterministic checkers
│   └── judge.py          # optional rubric judge (default glm-5.3:cloud)
├── tasks/*.py            # one TASK dict per file, 10 tasks
├── results/<runid>/      # run.json + report.md
└── README.md
```

Python 3 stdlib only. No venv, no pip installs.

## Task suite (10 tasks, one per category)

| # | Category | Source pattern in sessions | Checker |
|---|----------|---------------------------|---------|
| T01 | instruction-precision | "Reply with exactly: OK" | exact match |
| T02 | log diagnosis | systemd-coredump crash triage | contains_all(root-cause tokens), contains_none(distractors) |
| T03 | config edit | YAML with planted errors | corrected lines asserted via regex/contains (no YAML lib; line-level checks) |
| T04 | script writing | small bash/python utility | code block extracted + executed in temp dir, stdout/exit asserted |
| T05 | data transform | JSON → JSON | output parses as JSON, schema-lite assertions (keys, types, values) |
| T06 | research synthesis | multi-source research asks | contains_all(required facts), contains_none(cited-but-absent claims) |
| T07 | commit message | espanso/git work | format regex (imperative, ≤72-char subject), contains_all(scope terms) |
| T08 | code review | "why doesn't X work" | contains_all(bug name + fix concept), contains_none(false diagnoses) |
| T09 | regex/one-liner | bash one-liners, sed/grep | regex executed against pass/fail case lists |
| T10 | constrained writing | reformat under length/style rules | deterministic length/structure + judge rubric |

Task files are Python modules (`tasks/t01_*.py`) each exporting `TASK`:
id, title, category, prompt, system (optional), checkers (list of dicts),
timeout_s (default 120), max_tokens (default 700). Python modules avoid
hand-rolling a YAML parser (stdlib has none) and keep prompts editable.

Embedded context (logs, YAML, JSON, diffs, source snippets) is pasted into
the prompt — single-turn, no tools, temperature 0.2.

## Grading

### Deterministic (always)

Checker types in `lib/checks.py`:
- `exact` — normalized string equality (whitespace/case-fold options)
- `contains_all` / `contains_none` — substring sets, case-insensitive option
- `json_valid` + `json_asserts` — parse output (after extracting first JSON
  object or fenced block) and evaluate key-path assertions
- `exec_code` — extract first fenced code block, write to temp dir, run with
  `subprocess` timeout, assert exit code and stdout content (pass/fail case
  lists for regex/one-liner tasks)
- `regex` — full-match or search against pattern list
- `length_max` / `length_min` — word/char bounds

Task passes iff all its checks pass. Each check records pass/fail + observed
value for debugging.

### Judge (optional, `--judge`)

Only for tasks with `judge: true` (T06, T08, T10). Judge model default
`glm-5.3:cloud`. Judge receives task prompt + model answer + rubric, returns
strict JSON `{score: 1-5, verdict: "<=25 words"}`. Malformed judge output →
score recorded as null with reason; never crashes the run.

Bias note: when a candidate model IS glm-5.3:cloud, its judge-scored tasks
are self-graded. Report flags this (`judge=self` badge).

## Metrics

Per task: wall latency (request→complete, non-streaming), prompt_tokens,
completion_tokens, tokens/s, estimated cost from a static rate table
(flash $0.15/$0.50, glm-5.3 $1.40/$4.40, gemma4 $0.10/$0.40 per M — control
rate approximate; documented as such).

## Report

`results/<runid>/`:
- `run.json` — full machine-readable results (per task: checks, metrics,
  raw answer truncated to 4 KB, judge result)
- `report.md` — comparison across all models in the run:
  - pass matrix (model × task)
  - per-category pass rates
  - latency / tokens/s / cost table
  - judge averages + `judge=self` badges
  - notable failures (first failed check per model)

`--baseline <runid>` marks a prior run to diff against in report.md.

## CLI

```
python3 bench.py                       # default suite, default models
  --models a b c                       # model IDs (default: the three above)
  --judge [MODEL]                      # enable judge (default glm-5.3:cloud)
  --only T01,T04                       # subset of tasks
  --concurrency N                      # parallel tasks per model (default 5)
  --selftest                           # checker validation, no API calls
  --baseline <runid>                   # diff against prior run
```

Concurrency: tasks parallel within a model (default 5 — quota-friendly);
models sequential. Errors (HTTP, timeout) → task recorded as failed with
reason string; run always writes partial results.

### Model-response handling

Reasoning models (GLM) may return reasoning in `message.reasoning` and/or
inline `<think>` tags: strip tags from content, capture reasoning token
counts when present in usage, never treat reasoning as answer content.
Non-reasoning models (gemma) return plain content — both shapes must grade
identically.

## Error handling

- Per-task timeout (default 120 s) enforced client-side.
- HTTP/auth errors: fail that task, continue the run; report summarizes.
- Output extraction failures (no code block found etc.) = check failure,
  recorded with observed value.
- Never raises into caller from a single task failure.

## Self-test

`--selftest`: feeds known-good and known-bad canned answers through every
checker and the report renderer. Exit 0 only if all checkers behave. Runs
offline in <1 s. Gate before any quota-spending run.

## Acceptance criteria

1. `--selftest` exits 0.
2. Live run of the 3 default models completes with judge on; report.md
   renders pass matrix + metrics.
3. Negative control expected (not guaranteed) to underperform GLM on
   ≥6/10 tasks; harness must show a measurable gap in pass counts,
   latency, or cost for the suite to be considered discriminative.
4. Total run cost within a few cents of quota; wall time ≤ ~15 min for
   all 3 models with judge.

## Rejected alternatives

- Multi-turn tool-use simulation — declined by user; slow/flaky, grading
  unfairness across tool-calling ability.
- YAML/Markdown task files — stdlib lacks YAML; custom parsers fragile.
- Streaming TTFB metrics — not needed for triage decisions.
- Local qwen3:8b as control — declined by user (cloud models only).