# Contributing

Thanks for considering a contribution. The bar is low and the loop is fast.

## Ground rules

1. **Python 3 stdlib only.** No pip dependencies — the harness must stay
   clone-and-run on any machine.
2. **Tests first.** New checkers and task-loader behavior need unit tests in
   `tests/`. Run the suite offline:

   ```bash
   python3 -m unittest discover -s tests
   ```

3. **Task authoring rules** are in [docs/CUSTOMIZING.md](docs/CUSTOMIZING.md) —
   they exist because real benchmark runs exposed the failure modes they prevent.
   Read them before adding a task.
4. **One PR, one concern.** A new task + a new checker type are two PRs.
5. **No model results in git.** `results/` is machine-local; commit only code,
   tasks, docs, and example reports under `docs/`.

## Good first contributions

- A new task category modeled on your own coding-agent logs
- Rate-table entries for models you've priced
- A new checker type with tests (keep the interface: `run_checks` dispatch,
  per-check `passed/observed/expected` dicts)

## Reporting benchmark results

Issues with full `run.json` attachments (model ids redacted as you prefer) are
gold — they grow the evidence base for what these tasks can and can't measure.