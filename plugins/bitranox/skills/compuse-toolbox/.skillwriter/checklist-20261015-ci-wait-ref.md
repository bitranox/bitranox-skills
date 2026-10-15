# skill-writer checklist - compuse-toolbox (2026-10-15, ci_wait --ref)

The `ci_wait` row and the marketplace-clone launch example name `--ref HEAD` instead of
`--sha "$(git rev-parse HEAD)"`, the row says what `--ref` resolves, where it must run and what it
refuses, and its `--json` shape now carries `data.sha`. The row also states the `no-runs` label, the
unit, default and start of the `--appear-grace` window, which both arms reported missing.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - one question per run, answered only from the
      full SKILL.md pasted into the prompt, quoting the deciding sentence or NONE, ending with a
      "Skill gaps" section.
- [x] Inherited-context route: every arm ran `claude -p --model haiku --tools ""
      --disable-slash-commands --setting-sources project` from a directory whose ancestor chain holds
      no CLAUDE.md, CLAUDE.local.md or `.claude-memory` (checked by walking it), so the answer came
      from the pasted text, not from an installed copy or memory.

## RED (pre-change SKILL.md, haiku)
- [x] Q1 (wait for CI on the pushed commit; `$(git ...)` is refused; only an 8-character sha seen):
      NONE - "The only `ci_wait` invocation shown is `... --sha $(git rev-parse HEAD) ...`, and your
      session refuses `$(git ...)`."
- [x] Q2 (which `--json` field names the commit watched): NONE.
- [x] Q3 control (how long an empty match is tolerated, which flag): 120 seconds, `--appear-grace`.
- [x] Skill gaps: no way to get a full sha without a substitution; the JSON fields' contents
      undescribed; the `no-runs` label, the grace unit, default and start point unstated.

## GREEN (changed SKILL.md, same model and questions)
- [x] Q1 `uv run scripts/ci_wait.py --ref HEAD`, quoting "Name the commit with `--ref HEAD` ... so
      you never type or complete one" and "also works where your own `$(git rev-parse ...)` is
      refused".
- [x] Q2 `data.sha`, quoting the row's `--json` sentence.
- [x] Q3 control unchanged (120 seconds, `--appear-grace`).
- [x] Diffed against RED both ways: Q3 kept; nothing RED answered was lost.

## REFACTOR
- [x] GREEN gaps closed: the printed sha is the same value as `data.sha`; a missing `sha` means the
      sha was refused and `error` says why; outside a repository, or for a name that is not a commit
      there, it exits 2 before any poll. The gaps both arms shared, which predate this edit, closed
      in the same change: an empty match is reported as `no-runs` (exit 2), and `--appear-grace` is
      in seconds, default 120, counted from the first poll that found nothing (`empty_since` in
      `wait_for`).
- [x] Quote-back re-test on haiku of the three fixes: each answered with a direct quote of the new
      sentence.
- [x] Gap declined, with reason: whether `--repo` lets `--ref` resolve outside a repository - the
      row already says the ref is resolved "in the current repo", which `--repo` does not change.

## Quality and deployment
- [x] Frontmatter untouched; the description is unchanged, so no length change.
- [x] No address, MAC, home or temp path added (the one grep hit over the diff is the existing
      `redaction_scan` row, re-padded by the table formatter).
- [x] Derived artifacts regenerated and byte-identical: `skill_triggers.json`, `docs/skills.md`.
- [x] `ci_wait.py` change test-first: 17 new cases RED on the missing feature (two usage cases were
      made to assert argparse's own message, since the both-flags case already exited 2 when
      `--ref` was an unknown flag); a 7-arm mutation battery killed every arm; a real run resolved
      `HEAD~1` and reported its CI green, and an unknown ref exited 2 without polling.
