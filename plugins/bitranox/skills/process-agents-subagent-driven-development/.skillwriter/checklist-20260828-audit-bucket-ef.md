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
