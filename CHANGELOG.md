# Changelog

All notable changes to model-bench are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [0.1.0] - 2026-09-03

### Added
- 16-task benchmark suite mined from 45 real coding-agent sessions on Omarchy
  Linux: instruction precision, crash-log diagnosis, config editing, script
  writing (executed), JSON transforms, research synthesis, commit messages,
  code review, sed one-liners (executed), constrained writing, dependency
  reconciliation, config-schema diagnosis, skill authoring, install guidance,
  multi-file consistency, notification-log correlation.
- Deterministic checker library: exact, contains, regex, JSON path assertions,
  sandboxed code execution with case lists, length bounds.
- Optional rubric judge (`--judge`) with strict-JSON parsing, clamping, and
  `judge=self` self-grading badges.
- OpenAI-compatible client with reasoning-channel handling, `finish_reason`
  capture, and per-task `truncated` flags.
- Markdown reports with pass matrix, per-model latency/tokens/cost, notable
  failures, and `--baseline` run-to-run diffing.
- Negative-control model doctrine (weak control expected to lose).
- `--selftest` offline checker validation; 36 unit/integration tests.