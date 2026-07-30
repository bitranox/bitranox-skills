# skill-writer checklist - devops-bmk: document the .sh shell-lint gate's settings (2026-07-30)

Change: add the concrete `shfmt`/`bashate` flag values bmk's pipeline passes, the fact that bashate
reads no config file, and the pre-3.13.2 nested-worktree false positive, to section 5.

## PLAN
- [x] Skill type identified: REFERENCE (documents a tool's actual behaviour), so the test approach
      is a retrieval/application scenario, not a discipline pressure scenario.
- [x] Test approach chosen: give an agent the real symptom ("formatting diffs CI rejects though it
      passes locally, and bashate flags long lines we consider fine") and see whether it can state
      the flags the pipeline must pass and where bashate reads config from.
- [x] Scenario drafted before writing anything.
- [x] Scope: self-contained edit to the existing SKILL.md, no new supporting file.
- [x] Task list created for the phases.

## RED - baseline WITHOUT the change
- [x] Baseline dispatched to a sonnet subagent, skill content NOT supplied, trap NOT telegraphed
      (the scenario gave the symptom, never the flag names).
- [x] Baseline FAILED, and the failure is documented verbatim:
      - answered `shfmt -d -i 2 -ci -bn -sr .` - the indent width is WRONG for this pipeline
        (bmk uses `-i 4`), so following it reproduces exactly the rejected-diff symptom;
      - proposed `bashate -i E006` (disable the long-line check) rather than the pipeline's
        `--max-line-length 120`, a different and lossier remedy;
      - recommended putting the style in `.editorconfig` "removing the need to match flags by
        hand", which does not describe what bmk actually runs;
      - did NOT know the nested-worktree false positive at all.
- [x] Pattern identified: the generic tool knowledge is present and correct, but the PROJECT's own
      pipeline values are unknowable to the agent, and guessing them reproduces the reported bug.
      That is precisely the class a tool skill must supply.

## GREEN - minimal change addressing the baseline failure
- [x] Change addresses the specific baseline failures: states `-i 4 -ci` (and why omitting `-ci`
      still fails), `--max-line-length 120`, and that bashate reads NO config file so the flag is
      mandatory - closing the `.editorconfig` and `-i E006` detours the baseline took.
- [x] Nested-worktree false positive documented with its diagnostic tell.
- [x] No content added for hypothetical cases beyond the observed failures.
- [x] Placed in the existing "Missing external tools" section next to where the two tools are
      already named, so retrieval lands on it.
- [x] Frontmatter untouched (name/description unchanged, still trigger-first).
- [x] No `@` links; no bare script filenames introduced.
- [x] ASCII only, no em-dashes or typographic tells.

## REFACTOR
- [x] Re-read for loopholes: the wording forbids the two specific wrong turns the baseline took
      (match indent but drop `-ci`; reach for a config file) rather than only stating the values.
- [x] No rationalization table needed - this is a reference fact, not a discipline rule.

## Quality
- [x] Quick-reference placement verified (section 5 already lists shfmt/bashate).
- [x] No narrative storytelling; states current behaviour, with the version boundary (3.13.2) given
      as a live upgrade condition rather than a history note.
- [x] Token budget: addition is a short paragraph pair in an existing reference/hub skill.
- [x] No external doc reference added, so nothing new to make install-reachable.

## Deployment
- [x] Security review of the diff: no secrets, credentials, private hostnames, IPs, internal paths,
      or PII. The change names only tool flags and a public version number.
- [x] Plugin version bumped in `plugins/bitranox/.claude-plugin/plugin.json` in the same change.
- [x] Derived artifacts regenerated (skill_triggers.json, docs/skills.md, README count).
- [x] `repo-gate.py --ci` run green with CI's full dependency set.
- [x] Committed additively to `master` (no force-push, history stays append-only).
