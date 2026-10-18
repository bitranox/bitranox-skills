# Handover 2026-10-18: [12] closed, [23] step 3a done, 9.2.5 and bmk 3.21.5 shipped

## In flight

- Nothing part-done. No subagents or background jobs are running. Both temporary worktrees
  (`bitranox-skills-wt-fold23-dirty`, `bmk-wt-fold23-dirty`) and their branches are removed.

## Committed, or not

- Pushed, CI green: bitranox-skills 9.2.5 (`bacf204d`) and bmk 3.21.5 (`0e801ce`). bmk was pushed,
  NOT released (no tag, no PyPI), as with 3.21.3 and 3.21.4.
- Memory store (`<softdev-root>/.claude-memory`): still uncommitted, now also holding today's six
  bmk archives, 14 re-pointed citing facts and the semdex `--exact` fact's new hook. Backup taken
  before the archives: `.plan/fold-23/backup-pre-archive-bmk5.tgz`. The next dream commits it,
  staging deliberately.
- `projects/CLAUDE.md` (untracked, in no repo) edited in place: its release-ordering sentence now
  points at `bitranox:devops-bmk` section 3.
- `EXECUTION-USER-REVIEW.md` (gitignored) holds today's three user decisions.
- This handover and `OPEN-WORK.md` are committed together.

## Decided, and why - do not reopen

- [12] closed on measurement (user's choice "A"): the decide_path read is in its line; the undefined
  "second wave of 6 sites" is its own item, [28], size unknown.
- The sixth bmk fact's dirty-tree rule was FOLDED into devops-bmk, not kept in memory (user's
  choice, verbatim label "Fold into devops-bmk (Recommended)"). The behavioural RED did not fail
  (5 of 5 arms set the edit aside); the edit rests on the text gap all five reported, recorded in
  `plugins/bitranox/skills/devops-bmk/.skillwriter/checklist-20261018-release-dirty-tree.md`.
- Two deps-fact details were dropped on purpose: the helper one-liner (`BMK_OUTPUT_FORMAT=text`
  supersedes it) and "build>=1.5.0 pinned low" (stale: bmk pins `build>=1.6.1`).

## Still open, untouched

- [23] 3b (pwshpy 2 rules, btx_lib_mail 1) needs a new user approval: it pushes two public repos.
  [23] 3c provmm-benchmark (private Gitea), [23] Phase 3, [26], [28], [96] and the FOUND items:
  `OPEN-WORK.md`.

## Lessons for the next nap

- When a behavioural RED passes on every arm but every arm reports the skill silent on the point,
  record the text gap as the RED and name that route in the review artifact; do not escalate the
  scenario until something fails.
- When archiving facts that a skill now covers, grep every CLAUDE.md and every fact's HOOK prose
  for the slug as well as `[[slug]]` refs: `--check-tree` sees only `[[ ]]` refs, and both a
  CLAUDE.md sentence and a semdex hook still named an archived slug.
- When a fold's evidence is a NEW skill version, run the quote-check and the archive only after
  the user has installed that version; a source-only check can pass while installs lack the text.
- tooling: `redcheck --corpus-cascade` reported INHERITED COVERAGE on term overlap (aside, stash,
  uncommitted) from two unrelated documents while the fact that actually stated the rule went
  unflagged - more evidence for [600].
- tooling: `factedit apply --body-file` normalises a doubled blank line after the frontmatter, so
  one body diff carries an extra removed blank line; harmless, but it trips a ref-lines-only check.
- Carried over, not napped yet: the lessons in `git show 7033a061:handover.md` and the ones that
  file itself carries over.

## The exact next action

[23] is the top-ranked open item and its next step, 3b, is blocked on the user. Ask ONE question
(AskUserQuestion): fold the 2 pwshpy rules and 1 btx_lib_mail rule into those repos' own skills
(each a public push plus its marketplace mirror), or defer 3b and do 3c / Phase 3 first. Read the
[23] line in `OPEN-WORK.md` for the slugs and the step-3 method before asking.

## Files that matter

- `OPEN-WORK.md` ([23] carries the step state; [28] is new)
- `plugins/bitranox/skills/devops-bmk/SKILL.md` and its `.skillwriter/checklist-20261018-release-dirty-tree.md`
- `.plan/fold-23/` (rows, step-6 evidence, backups)

## How to verify

- CI: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox `scripts/`) here and in
  `projects/public/apps/utils/bmk`.
- Twins: `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` reports 0 drifted.
- Memory tree: `reconcile_memory_index.py --check-tree <softdev-root>` (home
  `skills/meta-self-improve/`) reports TOTAL 1 (the known rct-bose sideways ref, [590]).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
