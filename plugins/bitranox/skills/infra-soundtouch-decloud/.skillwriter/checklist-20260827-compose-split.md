# skill-writer checklist - infra-soundtouch-decloud (Docker and compose are separate findings)

The prerequisite check folded the Docker engine and the compose plugin into one result. The verdict
was right and the advice was wrong: an owner who had just installed Docker, on a distribution where
the plugin is its own package, was told to install Docker.

## PLAN

- [x] Change type: a correction to a shipped check's OUTPUT, so the instrument is the specific
      machine state that produced the wrong advice, asserted directly.
- [x] Scope: one script, its tests, the phase 0 wording, and the mirrored twin.

## RED

- [x] The failing state is named rather than guessed: `docker` on PATH, `docker compose version`
      failing. The old code reported `docker: not present` and handed back the full engine install
      instruction, which that owner had already followed.
- [x] It was not caught by the existing tests because the old test asserted only the VERDICT
      (`present is False`), which was correct. Nothing asserted what the reader was told to do.

## GREEN

- [x] `check_compose` is its own check with its own verdict, reason and per-platform instruction:
      the plugin package on Debian and Fedora, and updating Docker Desktop on Windows and macOS,
      where the engine ships it.
- [x] `check_docker` now answers only for the engine, so it reads present when the engine is present.
- [x] With no engine at all, compose reports "not available" and does not pretend to have probed.

## REFACTOR

- [x] The new test asserts BOTH halves of the case that motivated the change: docker present,
      compose absent, and the compose instruction naming the plugin and NOT the engine installer.
      An assertion on the verdict alone would have passed against the old code.
- [x] The seam control is carried forward and updated: every reported version must still come from
      the injected lookup, now across five checks rather than four.
- [x] The row is named for the COMMAND, `docker compose`, not the package. `docker-compose` is
      also the deprecated standalone v1 binary, so a reader who searched the label would have
      reached the wrong tool: the failure this change exists to stop, one step further along.
- [x] Declined, with reason: compose is not made optional. The service is started with
      `docker compose up`, so an owner without it cannot finish, and reporting it as a nicety would
      be the same wrong-advice failure in the other direction.

## Quality

- [x] Tests cover engine present, engine absent, plugin absent with the engine present, plugin
      present, and the no-engine case, on both a Linux and a Desktop platform.
- [x] No real addresses, hosts or paths added.
- [x] Tables reformatted, typographic tells stripped.
- [x] Twin re-synced; mirror audit reports 0 of 11 pairs drifted.

## Deployment

- [x] Frontmatter parses; description unchanged.
- [x] Full CI-parity gate green.
- [x] Security review of the diff: no secrets, credentials, private hosts or personal data.
- [x] Both plugin versions bumped, derived catalogue and trigger map regenerated.
