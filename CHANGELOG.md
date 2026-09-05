# Changelog

All notable changes to model-bench are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [0.3.0] - 2026-09-04

### Added
- T23, a voice-matching task. Every prior task states its rule in the prompt
  -- which is exactly why T17-T22 were passed by all four models, including
  the deliberately weak control: they measure careful reading, not
  capability, and are kept as regression pins by this repo's own
  negative-control doctrine. T23 states its convention only by example:
  three short invented emails establish a register -- terse, answer first,
  no closing phrase, bare first-name sign-off -- and the model must write a
  fourth that matches it while carrying two supplied facts (Thursday; the
  loading dock) and not inventing a third that was deliberately withheld
  (no time of day is given). Inferring a convention from samples and holding
  it while generating is a capability difference, not a reading-comprehension
  one, so T23 should discriminate where T17-T22 could not.
- The invention checker is the one that matters most: it mirrors a real
  failure where a model fabricated a serial number into a draft addressed to
  a third party over its owner's name. Here, a reply naming any time of day
  fails, since none was ever supplied.

## [0.2.0] - 2026-09-04

### Added
- Six email-triage tasks (T17-T22), modeled on a live personal-assistant lane
  that filed eleven useless tasks in six days: distinguishing an email that
  REPORTS something finished from one that ASKS for something, holding a
  three-line output contract that a downstream parser depends on, and writing
  a task title specific to the email rather than a phrase that would fit any
  of them. T20 wears an urgent subject line over a completed payment; T21
  states the principle with no examples; T22 is the inverse trap -- a shipping
  notice that genuinely needs action, so the suite is not scored purely on
  suppression.
- Methodology note on universal passes: a task the negative control also
  passes measures the prompt, not the model. T17-T22 are all in that class and
  are kept as regression pins rather than as discriminators.

### Notes
- All four models tested (glm-5.3-flash, glm-5.2, deepseek-v4-flash, and the
  gemma4:31b control) pass all six triage tasks. On T17-T22 latency spread was
  wide where correctness was not: glm-5.3-flash 3.6s avg vs glm-5.2 18.6s.

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