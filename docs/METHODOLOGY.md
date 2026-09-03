# Methodology

How model-bench grades, what the numbers mean, and what they don't.

## Grading model

Each task defines a list of **checkers**. A task passes iff every check passes.
Checkers are deterministic string/JSON/process assertions — no LLM in the loop:

| checker | semantics |
|---|---|
| `exact` | normalized string equality (whitespace collapsed, optional case-fold) |
| `contains_all` / `contains_none` | substring sets, case-insensitive by default |
| `regex` | search or fullmatch |
| `json_asserts` | parse JSON (fence-tolerant) + key-path assertions (`eq`, `len`, `contains`, `gte`, `lte`, `type`) |
| `exec_code` | extract first fenced code block → run in temp dir per case → assert exit code + stdout (contains / not-contains) |
| `length_max` / `length_min` | word-count bounds |

Design rules the suite follows:

1. **Every required fact must appear in the prompt.** A checker may only demand
   knowledge the prompt provided. Tasks that secretly depend on internal schema
   knowledge measure recall, not competence — and produce confident hallucinations
   (observed twice in one session: two models invented a plausible-but-wrong
   `"provider"` key fix when the real rule wasn't in the prompt).
2. **Checker vocabulary must match plausible correct answers.** `fallback` fails an
   answer that correctly says "falls back". Prefer stems (`fall`) over exact words.
3. **Format strictness is a feature, not a bug.** A model that wraps YAML frontmatter
   in a code fence produced *correct contents* that would break a real `SKILL.md`
   if pasted. The checker correctly fails it. Instruction adherence is part of
   fitness for coding-agent work.

## The judge (optional)

Open-ended tasks get a 1–5 rubric: correctness 0–2, completeness 0–2,
instruction adherence 0–1. The judge must reply with strict JSON; malformed grades
are recorded as `unparseable` and never crash a run.

**Known limitation, measured:** judge scores came back 5.0/5.0 for answers of
clearly different quality. LLM judges are lenient — deterministic checks carry the
signal; judge scores break ties at best. When the judge model is also under test,
the report badges `judge=self`.

## The negative-control doctrine

The suite ships a weak model expected to lose (default: `gemma4:31b:cloud`).
This is a canary for benchmark rigidity: if the control ties a frontier model,
the suite is too easy — add harder tasks before trusting pass rates. Across this
repo's real runs the control lost precisely the code-synthesis tasks (bug-finding,
sed authoring, skill authoring) while matching retrieval/format tasks, which is
the expected profile for a small generalist.

## Reasoning-model behavior (measured findings)

- **Reasoning starvation.** A reasoning model can consume its entire `max_tokens`
  budget in the reasoning channel and emit an empty answer. The harness records
  `finish_reason` and flags `truncated: true` per task so starvation is visible in
  `run.json`. Observed at 100–8000 token caps depending on task ambiguity.
- **Ambiguity is a cost multiplier.** One diagnosis task with an under-specified
  prompt: 53.7s wall time, 4000+ reasoning tokens, empty answer. After stating the
  schema rule explicitly: 5.8s, clean pass. Same model, same task, one sentence of
  context difference.
- **Fast answers can be confidently wrong.** In the same task, a cheaper model
  answered in 4.9s — hallucinating a fix for a key that was never missing.
  Latency is not quality; the pass matrix exists so you don't have to guess.

## Cost accounting

`lib/report.py` carries a static per-M-token rate table (input/output). Rates for
models not in the table render as $0 — add them if you track spend. Estimates use
actual `usage` numbers, so reasoning tokens are billed honestly.

## What model-bench does not measure

- Multi-turn tool-use ability (deliberately out of scope — see README FAQ)
- Long-context behavior (prompts are 100–600 tokens)
- Speed under concurrent load (models run sequentially; tasks in parallel)
- Anything about your specific prompt template — bring your own by editing tasks

## Suite provenance

Categories were mined from 45 logged coding-agent sessions on an Omarchy Linux
system (2026-09): tool-call frequency analysis (bash 810, read/edit/write 152,
web research 90, GitHub 40) and first-message classification. Tasks were then
authored to be self-contained, offline, and deterministically checkable. Task
files carry the original pattern they model in their comments.