# skill-writer checklist - git-worktrees (2026-08-27, audit bucket G)

The ignore check tested a directory the reader had not chosen.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Every defect here is a FACTUAL claim, so the test is a
      ground-truth check against the real file, the installed package or live tool output, not a
      pressure scenario.
- [x] Scope: correction only. No new capability, no procedure reshaped.

## RED
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than the draft and cannot fail honestly. The route
      taken instead is the one the skill names - a ground-truth check whose result is immune to
      inherited context.
- [x] `git check-ignore` matches a PATHNAME and does not test the filesystem, so `check-ignore
      .worktrees || check-ignore worktrees` reports "ignored" whenever EITHER name is listed.
      Both failure directions were reproduced in throwaway repos, and the likelier one was not
      filed: step 3 defaults every repo with neither directory to `.worktrees/`, so any repo whose
      `.gitignore` uses the plain spelling passes falsely and the worktree lands untracked.
- [x] Same block used `$LOCATION` and `$BRANCH_NAME`, which the skill never assigns anywhere.
      Copied verbatim it builds `/my-feature` at the filesystem root, fails, and routes the reader
      into the "sandbox blocked it" fallback - a misdiagnosis dressed as a handled case.

## GREEN
- [x] Directory Selection now BINDS `$LOCATION` and `$BRANCH_NAME`, and the check tests the bound
      directory. The create step notes where the bindings come from.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
