# skill-writer checklist - meta-dream-crosstree-deep (add step 4b, the personal harness half)

Change: a new step 4b runs the personal half of the local harness audit (`~/.claude/skills`,
`~/.claude/hooks`, and the hooks wired in `~/.claude/settings.json`), and the report list gains a
line for its findings.

## Scope
- [x] Wiring change only. The procedure lives in `bitranox:meta-audit-local-skills-and-hooks`,
      reviewed under its own checklist; the ownership rule is cited, never restated. Verified by
      grep - zero hits for `claude-plugin` or `REPORT ONLY` in this SKILL.md.
- [x] Altitude split is explicit in both directions: this step states the per-tree dream owns the
      project half, and the per-tree pass states the personal half belongs here. Either call site
      read alone leads to the right scope.

## RED
- [x] Before the change nothing audited `~/.claude`. On this machine that surface held a test
      module that cannot be collected, orphan bytecode for a hook that no longer exists, a parked
      dir holding 22 skills, and a local skill duplicating a shipped one at a 100% description
      match with no mirror gate over the pair. None of it was reachable by any existing gate.
- [x] Placement is deliberate: `~/.claude` loads in every session on the machine whatever the cwd,
      so it belongs to the machine-global pass, not to any one tree's dream.

## GREEN
- [x] Step 4b sits between the org-chart audit and the inherited crosstree steps, so it runs
      before the report is assembled and its findings have somewhere to land.
- [x] The cited skill name resolves to a real skill directory.

## REFACTOR
- [x] Gap: the deep dream's report list had no slot for these findings, exactly the failure its
      own step-4 note calls out ("a deep run can generate them and never surface them"). CLOSED:
      the report line now covers both the org-chart proposals and the harness findings.
- [x] The report line requires the REFUSED count, not just the finding count. A refusal count of
      zero on a machine holding tool repos means the ownership filter did not run, and that is
      invisible if only findings are reported. Evidence, not a verdict.
- [x] Undecided gap list is empty.

## Quality
- [x] Numbered to match the file's existing `3b` convention for an inserted step.
- [x] No narrative, no provenance, no machine-specific addresses or paths.
- [x] ASCII only.
- [x] Frontmatter untouched, so the CSO description is unchanged and needs no re-review.
