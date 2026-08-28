# skill-writer checklist - process-agents-subagent-driven-development (2026-08-28, audit bucket E+F)

One unanchored claim: the agent-frontmatter hot-loading exception, with no version and no check.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. The defect is a FACTUAL claim carrying no version or date,
      so the test is a ground-truth check against the installed package, the live catalogue or the
      running tool - not a pressure scenario.
- [x] Scope: correction only. No new capability, no procedure reshaped.

## RED
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording rather than the draft and cannot fail honestly. The route
      taken instead is a ground-truth check, whose result is immune to inherited context.
- [x] The exception (a machine's very first agents dir needs one session restart) was probed on
      an earlier Claude Code build. A reader hitting an effort setting that seems ignored has no
      way to tell whether the documented exception still applies to their version.

## GREEN
- [x] The passage now marks itself NOT re-verified since Claude Code 2.1.250 (the version here)
      and names the one action that resolves it either way: restart the session once before
      digging further. The claim is kept with an explicit unverified marker rather than dropped,
      because it is cheap to act on and the failure it describes is otherwise opaque.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched, so no routing keyword moved and the description cap is unaffected.
- [x] The version is stated as the build the claim was NOT re-tested against, not as the build
      it was verified on - the distinction the finding turned on.

## Follow-up: re-tested instead of hedged, and the claim was WRONG (decision review)

- [x] Two arms on Claude Code 2.1.250, both dispatched mid-session with no restart:
      a NEW project agents dir (`.claude/agents/probe-hotload.md`) and a NEW file in the
      already-loaded user dir (`~/.claude/agents/probe-hotload2.md`). BOTH failed with
      `Agent type 'X' not found`, and the reported available list was the session-start roster
      in both cases.
- [x] Positive control: `probe-effort-low`, which comes from that same user dir and was present
      when the session started, IS in that list. So the dir is read - just not again.
- [x] The shipped claim ("hot-loaded, EXCEPT the very first agents dir on a machine") is
      therefore WRONG on this version, not merely unanchored: the exception is not the first dir,
      it is EVERY mid-session addition. The text now states the measured rule, that the roster is
      fixed at session start.
- [x] Scope stated honestly: this measures ADDING a definition. Whether EDITING one already in
      the roster takes effect mid-session was not tested, and the text does not claim it.
- [x] Probe files removed from both dirs; one had been auto-staged and was unstaged, and the
      working tree is clean.
