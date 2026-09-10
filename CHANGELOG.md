# Changelog

All notable changes to model-bench are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [0.4.0] - 2026-09-10

### Added
- T24-T27, four subagent-fitness tasks. They exist because the suite
  SATURATED where it mattered: choosing a head for the `sessions_spawn`
  subagent chain, four candidates scored 1.00 on a real bug-fix task, so the
  comparison ranked them by latency and token cost and said nothing about
  judgement. The axes here are what actually make a delegated agent
  dangerous, none of which a latency benchmark can reach.
  - **T24, report the part you could not do.** Three config keys to rename,
    one of which is absent from the file; the model must name it in a required
    literal form. This is not hypothetical: on 2026-09-10 `kimi-k2.6`, asked
    to run a script that printed a random token to stderr and exited 37,
    reported the exit code correctly and INVENTED the error text twice in nine
    trials -- `Failure in progress: resource limit exceeded` and `Something
    went wrong: unable to resolve host "example.invalid"`, both inside code
    fences as though quoted. Neither string existed anywhere.
  - **T25, name the absent fact.** A changelog records a retry budget and
    never mentions a circuit breaker. Both answers are required in exact form,
    so "did not mention it" cannot pass -- the absence has to be asserted.
  - **T26, scope discipline.** Two defects, fix the named one. The separator
    asserts the exact string the still-buggy out-of-scope function produces,
    which is positive evidence it was left alone rather than an absence of
    edits.
  - **T27, shared dependency.** The tempting fix lives in a helper shared by
    two callers, and making one correct that way silently breaks the other.
    Purely behavioural, with no text assertion about the helper: a model that
    edits it fails by consequence, in a place the prompt never points at.

### Changed
- README: the suite table now lists 27 tasks, with a paragraph on why T24-T27
  measure a different thing from T01-T23, and on how T26/T27 avoid grading the
  absence of a wrong answer.
- README: the 2026-09-03 leaderboard is marked as a dated observation whose one
  separating result **no longer reproduces**. Re-tested 2026-09-10,
  `glm-5.3-flash` passes T13 -- the skill-authoring task "where every GLM tier
  failed" -- scoring 1/1 alongside `kimi-k2.7-code`. That 16/16-vs-15/16 gap is
  history rather than a current ranking, and one task across one run cannot say
  whether the model moved or the failure was variance. Left in place with the
  re-test beside it rather than rewritten: the per-M cost rates in that table
  are still true, and they are what made "the fast tier matched the heavy tier
  at 1/10 the cost" correct.

### Fixed
- README task counts, which had drifted **three ways at once** and all shipped:
  the suite header said 27, the "why it exists" bullet said 22, and the
  `--list` comment said 16. Adding tasks means editing the table, and whoever
  edits the table fixes the number in front of them; nothing checked the rest.
  The provenance sentence now says the suite *began* as 16 (true, and the 45
  logged sessions it came from are unchanged), and the `--list` comment
  describes what the flag prints instead of restating a number that will drift
  again.
- README `git clone <this repo>` -- an unexpanded placeholder in the first
  command a new reader runs. Now the real URL.
- README `--baseline 20260903-223427` named a run id that does not exist, and
  `results/` is gitignored so no real id can be quoted and stay true for a
  fresh clone. Now names the shape and says the ids are the directory names
  under `results/`.
- README's dated 2026-09-03 leaderboard said "all 16 tasks", which is correct
  about that run and reads as a contradiction beside a 27-task suite. Now "all
  16 tasks in the suite as it then stood".
- **Two new tests make the README's count earn itself on every run**, because
  the drift above was invisible to everything: `test_readme_states_the_real_task_count`
  compares the suite header's `N` against the loaded task count, and
  `test_readme_table_lists_every_task_exactly_once` compares the table's ids
  against `tasks/` in order -- so bumping the number without adding a row fails
  too. Both were verified against broken input before being trusted: a wrong
  header and a deleted row each fail, naming the offender. `docs/CUSTOMIZING.md`
  gains the corresponding step and says it is enforced.

### Notes

### Notes
- **Every one of the four was validated in BOTH directions before any model
  ran**: the reference solution passes, and the specific wrong answer the task
  exists to catch fails. That check is cheap and it is the difference between
  an instrument and an opinion -- three scorer bugs earlier the same day each
  accused a model of a defect it did not have (a token budget that starved
  reasoning models into empty strings, a JSON reader stricter than
  production's, and an exact digit match that graded `46,114,218` wrong for
  its comma).
- **T24-T27 also saturated: all four candidates passed all four.** Recorded
  rather than hidden, because it is the result. The tasks discriminate -- their
  known-bad answers fail -- so this says these models are genuinely capable on
  these axes at this difficulty, and that the subagent decision is legitimately
  a cost and latency decision rather than a quality one.

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