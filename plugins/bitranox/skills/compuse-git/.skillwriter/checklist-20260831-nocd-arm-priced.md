# skill-writer checklist - compuse-git (2026-08-31, the wrong-repo guard's priced boundary)

Change: the bare-`git`-after-a-`cd` row now states that NO hook catches the cross-call shape, and
names the measurement that rejected the arm which would have. The hook's own docstring carries the
full record beside the two prices already there.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED route: COVERAGE CHECK AGAINST THE FILE. The rule half is already in this machine's memory
      index (`feedback-wrong-repo-git-plus-a-plain-rev-parse-...`), so a behavioural baseline is
      contaminated. Pre-change, the row taught the rule but claimed nothing about coverage, and a
      reader had no way to tell a guarded shape from an unguarded one.
- [x] MEASURED, not asserted: an arm firing on "a git in a call containing no cd and no -C",
      replayed with `guard_replay.py` over the corpus the hook was built on, speaks on 2,961 of
      65,810 commands - 4.499%, one in 22, against the shipped arm's 0.186%.
- [x] The sample was READ, not just counted: the firings are ordinary single-repo work whose cwd
      was already correct.
- [x] Precision reported honestly: `guard_replay` scores 0.81%, and its own documentation says that
      figure answers the WRONG question for a guard whose hazard is a plausible-but-wrong ANSWER,
      since such a hazard is never followed by a block. The RATE is what rejects the arm, and the
      artifact says so rather than quoting the more damning-looking number.
- [x] The rejection is recorded so it is not re-proposed blind, which is what the queued
      contribution asked for. The note also states why a STATEFUL version is worse than none: the
      harness sometimes resets the cwd between calls, so it would answer confidently and wrongly.
- [x] Scope: shared - the mechanism is the Bash tool's persistent cwd, not this machine's layout.
- [x] Security scan: prose and counts only; no paths, hosts or credentials.
- [x] CSO description: unchanged; the row lives under existing triggers.
- [x] Token budget: one sentence added to an existing row.
