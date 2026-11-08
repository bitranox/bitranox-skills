# meta-claude-hooks: batch of queued improvements

Rule added: `guard_replay` precision prices only a hazard a gate would block; a wrong-answer guard
is priced by joining each firing to its tool result. References refreshed against upstream after
`hookdoc_stamp.py check` returned STRUCTURAL: Monitor matcher behaviour, auto-mode `updatedInput`
and `ask` paths, unavailable deferred tool resume, PostToolUse after an interrupt, PreCompact
output, `auth_storage_failure`, the WebSearch `mode` field. Baseline and stamp rewritten; `check`
now returns CURRENT, `coverage` is complete, and the skill's 100 tests pass.

Gaps declined:
- A threshold or sample size for a wrong-answer guard: depends on the guard.
- Whether `cmd || echo clean` is a wrong-answer hazard: the guard's own docstring settles it
  (`hooks/block-or-echo-verdict.py`), and the rule is stated by hazard, not by pattern.

- [x] Step 0b: `skill_decisions.py show` run for the skill before the first edit; no rejected or
      removed decision is reversed.
- [x] RED: coverage check of the pre-edit text (`git show HEAD:<path>`): every added rule's key term
      has zero hits. A behavioural RED was replaced by this text check because `redcheck
      --corpus-cascade` names the memory store and CLAUDE.md cascade as already teaching these
      lessons (rc 1, STRONG), so an agent on this machine cannot fail honestly.
- [x] GREEN: quote-back with application questions on `opus` (effort medium) and `haiku`, the edited
      text pasted inline, every dispatch ending in a `Skill gaps` section.
- [x] Every gap is closed or declined below; a decline resting on a system claim cites its source.
- [x] After the fix round the same questions were re-run on the final text on both tiers, and no
      new undecided gap appeared.
- [x] Width, fence, backtick and tell checks over the added lines printed nothing. Each list's
      introducing sentence and the paragraph after each insertion point were read.
- [x] Every mechanism claim added was checked against the code it describes.
- [x] No session narrative, private path or history line was added; the history finder's only hit
      ("no longer covering what moved") describes a test's behaviour, not the skill's past.

- [x] Decisions: d-20261108-2214b183
