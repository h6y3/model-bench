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
Endpoint: http://127.0.0.1:11434/v1 (Ollama Cloud resolves :cloud ids on
demand; `gemma4:31b-cloud` spelling resolves to the same backend).

## Tasks

Ten single-turn tasks, one per real-usage category mined from 45 pi session
files: instruction precision, crash-log diagnosis, config edit, script
writing (executed), JSON transform, research synthesis, commit message,
code review, sed one-liner (executed), constrained rewrite (judged).

## Output

`results/<runid>/run.json` (raw) and `report.md` (pass matrix, latency,
tokens/s, est cost, judge scores, notable failures). Diff runs with
`--baseline <runid>`.

## Judge

`--judge [model]` grades T06/T08/T10 with a 1-5 rubric. Default judge
glm-5.3:cloud; badge `judge=self` marks self-graded models.

## Notes

- Reasoning models (GLM): inline reasoning markup is stripped before grading;
  content only is scored.
- A single task failure never aborts a run; partial results always written.
- Source builds reasoning-markup literals via string concatenation — never
  write them as contiguous sequences (transport mangling, see pi incident
  2026-09-03-subagent-transport-model-tiers).