# Review checklist - a hand-raised floor PyPI's JSON does not list yet (2026-11-12, bmk 3.33.3)

Change: the release-cascade bullet in section 3 gains the reverse lag case. A floor raised by hand
to a release the JSON API does not list yet is kept and reported (`floor >=X matches no listed
release on PyPI, floor kept`); bmk 3.33.2 lowered it with a false `does not install on Python
3.10` note, so the bullet says to check `git diff pyproject.toml` after a gate on that bmk and how
to repair it. Twin of the bmk repo's `skills/devops-bmk/SKILL.md`, identical bytes. Frontmatter
unchanged.

## PLAN
- [x] Skill type: reference. Test: RED as a retrieval probe on the pre-edit bullet, GREEN as the
      same probe on the edited bullet (opus, text-only baseline-probe agents, same task: a floor
      hand-raised to a 4-minute-old release, `make test` on bmk 3.33.2 passed, about to commit).

## RED
- [x] Behaviour checked against bmk first: `S/probe/stale.py` ran the floor judgement with the
      new release stripped from PyPI's answer and with it present, arms interleaved; the stripped
      arm rewrote `lib_log_rich>=8.2.0` to `>=8.1.2` with the false note, the present arm kept it.
      Seen live first: a gate 4 minutes after the lib_log_rich 8.2.0 upload lowered the floor in a
      consumer's working tree. The fix (`_beyond_listed`, ERROR status, floor kept) has a test that
      went RED on the unfixed source for both `>=6.170.0` and `>6.169.0`.
- [x] RED probe (opus) on the pre-edit bullet: it said to check the floor still reads as written
      because "the deps stage may rewrite floors", but never that it could move DOWN, never named
      the false note, and read a passing local gate as a possible cache artefact only. It listed
      as gaps that the excerpt "says nothing about a floor you edit by hand" and "what the deps
      stage does when PyPI's JSON still reports an older version".

## GREEN
- [x] Same probe on the edited bullet (opus): it named the lowering and the false note, said the
      PASS may have tested the old release against a silently lowered floor, and checked the lock.
- [x] Gap the GREEN probe raised and folded into BOTH twins before commit: how to repair a lowered
      floor (restore it, wait for both endpoints, re-run the gate, since the lock went with the
      lowered floor). Its other gap, whether a newer bmk fixes it, stays implicit: the first
      sentence describes the current behaviour and names 3.33.2 as the one that lowered.
- [x] Non-ASCII: none added. No added line over 100 characters. Frontmatter untouched.
- [x] `diff -r -x .skillwriter` of this skill against the bmk worktree's committed twin: no
      difference (`repo-gate.py --mirror-of` reads an unpushed tool repo from origin, so it
      reports DRIFT until bmk is pushed).
- [x] No address, hostname or private path added.
- [x] Decisions: none - no ledger entry added. Ledger entry d-20261106-dfc4967b (not adopted: an
      exception to "commit the floor churn make test leaves" for a floor bmk lowered) had its
      reopen condition fire ("A bmk run
      lowers a dependency floor again"). The fix went into bmk itself (3.33.3), as that entry
      prefers; the skill text adds no general exception to committing floor churn, only the
      repair for the one bmk release measured to lower a hand-raised floor in the lag window.
