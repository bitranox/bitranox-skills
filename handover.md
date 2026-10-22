# Handover 2026-10-22: [23] batch 3 finished (9.11.2 + btx-skill-jev-judge 0.3.2); batch 4 next

## In flight

- Nothing part-done. No subagent, workflow or worktree is running; the fold-23-batch3c worktree
  and branch are removed (merged), the meta-skill-writer receipt is closed.
- origin/master carries this session's 119fbbd3 (9.11.2) + a54ee8a1 (JEV_JUDGE_FLOOR 0.3.2), with
  the igittigitt session's 113476e8 (coding-python-gitignore, 9.11.3) on top. That session pushed
  its own commit; nothing of it is owed here.
- The user has NOT yet installed 9.11.2/9.11.3 here: `/plugin marketplace update bitranox-skills`
  plus `/reload-plugins` brings the folded meta-claude-hooks text the 10 cut pointers now point at.

## Committed, or not

- This commit: `OPEN-WORK.md` ([23] carries every result of this session, measured) and this file.
- Already pushed elsewhere: memory store commits 208d3ad, f918ab9, the 10-hook cut and the
  recurrence-10 fact; btx-skill-jev-judge 1bbc410, tagged v0.3.2 and on PyPI.
- Gitignored: `EXECUTION-USER-REVIEW.md` holds today's two user decisions verbatim ("Fold + short
  pointer (Recommended)", "Release 0.3.2 first (Recommended)"); `.plan/fold-23/batch3/fold10/`
  holds the round's data (fold-result.json, hooks-before/after.json, qcheck and checklist scripts).

## Decided, and why - do not reopen

- The 10 REACH-FAILS rows were folded and KEEP a short pointer; no meta-claude-hooks nudge was
  built (user chose the fold over "Add a nudge, then fold").
- The bare-interpreter fact's recorded `shortened_hook` in `safe17-merged.json` named a different
  rule; its pointer was rewritten to the fact's own subject instead.
- The subagent-effort pointer (236 chars from [29]) was left as is.

## Still open, untouched

- [23] batch 4 (next lower level group): `OPEN-WORK.md`.
- [28], [335], [96]: blocked on Jev shadow data. Everything else: `OPEN-WORK.md`.

## Lessons for the next nap

- When reusing an earlier round's workflow script, re-check its model and effort pins against the
  current rules first: the fold18 script pinned no model on scenario and editor agents and ran
  quote-backs without effort medium.
- When a review subagent's "Skill gaps" names a count in a lead-in ("Three things"), check whether
  your own edit changed what it counts: the fold added a fourth bullet under it.
- When `factedit check` is the validator, read its advisories, not its exit code: it exits 0 on a
  trigger-less hook and only prints an advisory.
- Carried from earlier handovers (not yet napped):
  - When measuring a subagent's output by effort, use the notification's subagent_tokens minus the
    transcript input: transcript usage.output_tokens is the message_start partial.
  - When a /goal's pre-registered threshold misses but the arms do not overlap, decide on what the
    plan actually rests on, and record the weaker reading and the miss.
  - When a user answers an AskUserQuestion without reading it and asks again, the superseding
    answer governs; log both, the second marked as replacing the first.
  - tooling: `repo-gate.py --mirrors` counts a tool repo's linked worktrees as UNLISTED twins and
    exits 1 though no pair drifted (queued in contrib_queue).
  - tooling: the auto-mode classifier refused a subagent's Bash edit of plugin.json; keep version
    bumps in the controller.
  - When a rule depends on what an OMITTED subagent field inherits, read `~/.claude/settings.json`
    first and probe the override before building on it.
  - When an OPEN-WORK line carries several dated segments, the latest segment's "Next:" is current
    and the `next:` field can be stale: fix the field whenever you touch the item.
  - When a handover's next action names counts, recount them from the cited data first.
  - When a mirrored skill's text carries a package version floor, check every pin of that floor
    first (the twin's metadata test, `jev_shadow.py` JEV_JUDGE_FLOOR) - HIT AGAIN 2026-10-22: the
    pre-push gate caught `jev_shadow.py` still at 0.3.1. Run `repo-gate.py --ci` before pushing.
  - tooling: bmk's floor-pin reconcile drops a hand-written `exclude-newer-package` timestamp once
    the floor is older than the cooldown (seen again 2026-10-22 for certifi, correctly).
  - When a PreToolUse gate refuses a git command, stage or fetch in a separate earlier command
    (recurrence 10 recorded in the store fact today).

## The exact next action

[23] is the top-ranked open item, and its next step is Phase 3 batch 4: open
`~/.claude/plans/curried-mapping-dolphin.md`, pick the next lower level group after the
bitranox-skills/KI levels, classify its FOLD rows read-only (reach + skeptic lens, as batch 3 did
in `.plan/fold-23/batch3/`), and put the batch to the user before folding anything.

## Files that matter

- `OPEN-WORK.md` line [23] - every batch result, measured, with its data path.
- `.plan/fold-23/batch3/fold10/` (gitignored) - this round's workflow data and scripts.
- `plugins/bitranox/skills/meta-claude-hooks/references/io-contract.md` and `authoring.md` - where
  the 9 hook rules now live.
- `plugins/bitranox/skills/meta-self-improve/jev_shadow.py` - JEV_JUDGE_FLOOR, pinned by a test to
  the ai-llm-jev-judge floor.

## How to verify

- `git status --porcelain` in the repo: empty after this commit except gitignored files.
- The 9.11.2 content is on origin: `git merge-base --is-ancestor a54ee8a1 origin/master`.
- btx-skill-jev-judge 0.3.2 on PyPI: `curl -s https://pypi.org/pypi/btx-skill-jev-judge/json`.
- CI for the commit carrying this file: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
