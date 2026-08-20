# devops-bmk: how bmk keeps itself installed, and what now serialises it

Scope: the "bmk's env holds bmk alone, and is shared" section rewritten (the command it documents,
plus its bullet list), and one paragraph added to "The project venv `.venv`". No other section
changes.

## The finding this adds

Two corrections and one addition.

The skill said every `make` runs `uv tool install --reinstall --force "bmk>=<minimum>"`, and that
`--reinstall` "already implies `--refresh`". bmk replaced that in 3.13.0 with `uv tool upgrade bmk`,
which is a near no-op when current and takes no `--refresh` at all - uv rejects the flag, exit 2.
This is worse than an absence claim: it is a POSITIVE claim about a command the tool no longer runs,
and it described the exact behaviour that was removed BECAUSE it was destructive. The unconditional
reinstall tore the shared env down on every invocation, deleting site-packages out from under any
bmk still running out of it in another repo.

The addition is what bmk 3.16.0 and 3.17.0 ship: venv provisioning serialised per venv path, and a
shared/exclusive lock over the machine-wide tool environment. The reader-facing consequence is that
a caller-side `flock` around `make`, or a coordinator mutex, is no longer needed - and is worse than
the built-in guard, because it serialises whole gates where bmk serialises only the provisioning.

## RED: the behavioural arm is unavailable here, so the text check is the evidence

- [x] `redcheck.py --scenario ... --corpus-cascade <bmk repo>` over 675 assembled documents reports
      INHERITED COVERAGE, evidence STRONG, naming `/media/srv-main-softdev/CLAUDE.local.md`. The
      machine's always-loaded cascade already carries how bmk keeps itself installed and how
      concurrent runs collide, so a dispatched subagent answers from there rather than from the
      scenario, whatever the scenario says. A behavioural RED could not fail honestly.
- [x] Route taken, per the skill's rule for that case: the behavioural arm is replaced by a text
      check of the artifact, which inherited context cannot reach.

## Text check: pre-change vs post-change, eleven assertions

Pre-change file (the text a reader was actually handed):

- [x] contains `uv tool install --reinstall --force "bmk>=` - the command bmk stopped running
- [x] contains the claim that `--reinstall` implies `--refresh`
- [x] contains no occurrence of `uv tool upgrade`
- [x] contains no occurrence of `lock` in any form
- [x] contains no occurrence of `BMK_TOOL_LOCK`

Post-change file:

- [x] the reinstall-every-make command is gone
- [x] the implies-`--refresh` claim is gone
- [x] `uv tool upgrade` is present and is what the documented command block shows
- [x] `BMK_TOOL_LOCK` is documented
- [x] `BMK_VENV_LOCK_TIMEOUT` is documented
- [x] the text states outright that a caller-side lock is no longer needed

## Claims verified by measurement, not by reading release notes

Every claim the new text makes about uv was measured, because the design turned on one of them.

- [x] uv genuinely honours its own `<uv tool dir>/.lock`: holding an exclusive `flock` there makes
      `uv tool install` block rather than proceed.
- [x] `uv tool upgrade` and `uv tool list` block on that same lock, while `uv tool dir`, `uvx` and
      `uv run` do not. This is why the skill does not tell readers to reuse uv's lock: the upgrade
      runs before every target, so a gate-lifetime shared lock on uv's file would make every `make`
      on the machine, and every unrelated `uv tool install`, wait for the longest-running gate.
- [x] A uv tool env's `bin/python` is a symlink to an interpreter outside the tool dir. That is what
      makes a stdlib-only guard running on it non-circular, and the skill's account depends on it.
- [x] `uv tool upgrade` rejects `--refresh` with exit 2, so the removed claim is not merely stale
      but unrunnable as written.
- [x] The guard is exercised end to end against the shipped Makefile with a stub `uv`: uncontended
      the upgrade runs; with a reader holding the shared lock it waits the bounded interval, reports
      why on stderr, and mutates nothing; released, it runs again.

## Mirror

- [x] This copy and the bmk repo's `skills/devops-bmk/SKILL.md` are identical, and
      `repo-gate.py --mirrors` reports `in sync` for all ten pairs, devops-bmk among them. The pair
      carries no conventional divergences - the `name:` field, the H1 and the absence of a
      self-install blockquote already match - so the sync is a straight copy with nothing to
      re-apply.
