# skill-writer checklist - infra-soundtouch-decloud (prerequisites)

The skill documented every command as `uv run ...` and never checked that `uv`, Python or Docker
were present, nor said how to install them. Docker was the exception and already had a per-platform
table. This adds the missing half and the phase that runs it first.

## PLAN

- [x] Change type: a new capability on a technique skill, so the instrument is an application
      scenario plus a negative control - the check must work on a machine where the tools are gone.
- [x] Scope: one new script, its tests, a phase 0 in SKILL.md, and the mirrored twin.

## RED

- [x] The gap is established by reading, not by a scenario: every documented invocation in SKILL.md
      and the five reference files begins `uv run`, and no file mentions installing `uv`. Docker is
      the one prerequisite with a check (`check-docker`) and a per-platform hint.
- [x] The failure is structural rather than behavioural, so a pressure scenario is the wrong
      instrument: an agent handed the old text on a machine without `uv` cannot run any documented
      command, and there is nothing in the text for it to get wrong.
- [x] The real trap is recorded because it decides the design: the tool that reports what is
      missing must not itself need the missing tool. A `uv run` preflight is unrunnable exactly
      when it is needed.

## GREEN

- [x] `soundtouch_preflight.py` reports Python, `uv`, Docker and `pytest`, each with a reason and,
      when absent, a per-platform install instruction. Standard library only, run as
      `python3 scripts/soundtouch_preflight.py`.
- [x] Platform detected rather than asked - an owner who cannot say whether the box is Debian or
      Fedora is who this skill is for - with `--system` still winning for a container, a NAS, or a
      machine that is not the one in front of you.
- [x] `pytest` is reported and never required, so a user is not asked to install a developer tool.
- [x] Docker's existing per-platform table is reused rather than duplicated.
- [x] Phase 0 added to the walkthrough, with the instruction to work missing tools one at a time
      and the note that a fresh install usually needs a new terminal before it is on PATH.
- [x] The `uv run` line in the Scripts section now names its one exception, so the exception is
      where a reader meets the rule.

## REFACTOR

- [x] Verified against a control that must answer differently: with only Python on PATH the check
      exits 1 and names `uv` and `docker`, with the Windows instructions under `--system windows`.
      A first attempt at that control was itself broken - emptying PATH removed `python3` too and
      the run died at 127 rather than reporting - and was redone.
- [x] `docker` present without the compose plugin is treated as NOT present, because that state
      fails later at `docker compose up` instead of here, and it is pinned by a test.
- [x] Seams injected rather than internals patched: the os-release path and the PATH lookup are
      parameters, so the absent-tool cases are tested without touching the machine's real PATH.
- [x] Every required tool reported missing carries an install instruction, asserted as a property
      over all checks rather than one at a time.

## Quality

- [x] Tests cover detection, each check, the whole run and the CLI, including an unknown platform
      and a missing os-release.
- [x] No real addresses, hosts or paths added.
- [x] Tables reformatted, typographic tells stripped.
- [x] The twin is re-synced and the mirror audit reports 0 of 11 pairs drifted.

## Deployment

- [x] Frontmatter parses; description unchanged.
- [x] Full CI-parity gate green.
- [x] Security review of the diff: no secrets, credentials, private hosts or personal data.
- [x] Both plugin versions bumped, derived catalogue and trigger map regenerated.
