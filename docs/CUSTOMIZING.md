# Customizing model-bench

## Point at an endpoint

```bash
python3 bench.py --base-url https://my-host:11434/v1 --models my-model
```

Anything OpenAI-compatible works. For Ollama, cloud model IDs (`*:cloud`) resolve
on demand server-side — a 404 means the id is wrong, not that "cloud is down"
(listings under-report cloud models; probe by running, not by listing).

## Add a model

```bash
python3 bench.py --judge --models <id> --baseline <prior-runid>
```

To track cost, add a rate entry in `lib/report.py`:

```python
RATES = {
    ...,
    "<model-id>": {"in": 0.22, "out": 0.66},  # USD per M tokens
}
```

Unknown rates render as $0 — the run still works.

## Author a task

1. Copy an existing file in `tasks/` and rename to `t<NN>_<name>.py`.
2. Set a unique `id` (`T17`, `T18`, …), `title`, `category`.
3. Write the `prompt` — embed all context (logs, YAML, JSON, diffs) the model needs.
4. Pick checkers (catalog in `lib/checks.py`).
5. Set `judge: true` only if correctness is open-ended and the deterministic
   checks would be too coarse alone.
6. Leave `max_tokens: 4000+` headroom for reasoning models; the run records
   `truncated: true` when a model hits the cap.

7. **Update the README's suite table and its count in the same change.** Add a
   row to the table under `## The suite: N tasks`, and bump the `N`.

The loader validates every task at startup (required keys, non-empty prompt and
checkers) and `tests/test_tasks.py` enforces suite-wide invariants — run
`python3 -m unittest discover -s tests` after adding tasks.

Step 7 is enforced, not a courtesy. Two tests tie the README to `tasks/`:
`test_readme_states_the_real_task_count` compares the `N` in that header
against the loaded task count, and `test_readme_table_lists_every_task_exactly_once`
compares the table's ids against `tasks/` in order — so bumping the number
without adding a row fails too, which is the half that reads as done and is not.

⚠️ **They exist because the count drifted three ways at once.** The header said
27, the "why" bullet said 22, and the `--list` comment said 16 — all in one
file, all shipped. Adding tasks means editing the table, and whoever edits the
table fixes the number in front of them. Nothing checked the rest, so the
`## The suite: N` header now has to earn its number on every run.

Sentences about the ORIGINAL 16-task suite are history and stay true; the tests
deliberately match only the suite header and the table, never prose about
provenance.

### Checker authoring rules (from real failures)

- Demand only facts present in the prompt.
- Match stems, not exact words (`"fall"` not `"fallback"`).
- Keep format strictness when the format matters in real use; document why in a
  task comment when it's non-obvious.
- Add a distractor via `contains_none` when there's a plausible wrong answer you
  specifically want to fail (e.g. banned "restart the daemon" advice).

## Interpret results

- `report.md` — pass matrix, per-model totals, notable failures, baseline deltas.
- `run.json` — everything: per-check pass/fail with observed/expected values,
  latency, token usage, `truncated` flags, judge scores, answer previews (first
  4 KB).
- A universal failure (all models fail one task) is a task bug, not a model
  signal — fix the checker or prompt, then rerun just that task with `--only`.
- A universal *pass*, control included, is the mirror image: the task measures
  your prompt, not the model. Keep it as a regression pin; do not let it
  influence a model choice. See "The mirror: a universal pass" in
  [METHODOLOGY.md](METHODOLOGY.md).

## Troubleshooting

| symptom | cause | fix |
|---|---|---|
| `404 model "X" not found` | wrong id spelling | probe variants (`id:cloud`, `id-cloud`) |
| empty answer, `truncated: true` | reasoning starved the budget | raise task `max_tokens`; check prompt ambiguity |
| universal task failure | checker demands absent knowledge / wrong vocabulary | see checker rules above |
| `ClientError http: status 401` | endpoint auth | pass key via pi config or local gateway |