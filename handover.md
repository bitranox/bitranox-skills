# Handover 2026-10-24: [23] batch 5 pass 1 shipped (17 folds, 3 repos); archive 22 pointers next

## In flight

- Nothing of this session is running: every CI wait ended green, no subagent or workflow is live.
- Worktree `.claude/worktrees/fold-23-batch5` (branch fold-23-batch5) is removed with its branch
  right after this handover is pushed.
- The bmk session (peer) ships the devops-bmk twin `3aee316` in its next release, planned 3.27.0;
  nothing here waits on it.

## Committed, or not

- Pushed and CI green: bitranox-skills 10.0.15 (`27dca1e0`), lib_layered_config `68cc972`
  (plugin 7.3.3) plus `9211e8b` (make test churn), bmk `3aee316` (no bump). Mirror audit: every
  pair in sync on the published refs.
- Pushed earlier this session: memory store `77ccae9` (batch 4 pass 2: 29 pointers cut).
- NOT done: the 22 batch 5 pass-1 pointers are still in the projects/ level's `CLAUDE.local.md`;
  10.0.15 is installed (`/plugin marketplace update` ran), `/reload-plugins` has not.
- Gitignored and local: `.plan/fold-23/batch5/` (inputs, journals, by-label.json, r2-result.json,
  qcheck-installed-10.0.15.json, make_checklists.py).
- Not mine, left alone: the main checkout's untracked `o`.

## Decided, and why - do not reopen

- User: "go" for pass 1 (22 archive rows), then "push both" for the bmk and lib_layered_config
  twins.
- bmk twin pushed without a version bump: the bmk session asked for it and releases bmk itself
  (same as batch 4).
- The 9 FAILS rows (owner coding-python-use-modern-libraries, rarely loaded when they fire) keep
  their pointers; a better home is a separate decision.
- Declined gaps (recorded in each skill's `.skillwriter/checklist-20261024-fold23-batch5-pass1.md`):
  a polling bound for the release-cascade wait, an explicit cascade-vs-stale-floor test, the
  elided `schtasks /create` arguments (the source fact elides them too).

## Decided against, and why

- No new `schtasks` command line in compuse-ssh: no measured argument set exists to fold in.

## Still open, untouched

- [23] next steps (archive 22, pass 2 of 25 rows, batch 6): `OPEN-WORK.md`.
- [730] (--check-tree TOTAL 5), [740], [750] and the rest: `OPEN-WORK.md`.
- lib_layered_config `OPEN-WORK.md` [60] (a docstring defect found while folding), untracked there.
- A tree dream is due per the SessionStart nudge; [730] is its input.

## Lessons for the next nap

- When `store_manifest.py backup --out` points inside the softdev tree, `--check-tree` counts the
  copied `CLAUDE.local.md` files as levels (1576 problems): put the backup in the scratchpad.
- When quote-checking a fold against installed text after fix rounds, use each row's LATEST
  round's quotes: an earlier round quoted text a fix later replaced and reads as missing.
- When a mirrored skill changes on both sides, commit both twins before any push (a push refuses
  until the other side is committed), and fast-forward the marketplace main checkout's local
  master to the worktree commit before committing a twin: the twin's commit gate reads it.
- When a CHANGELOG line summarises a fix that removed an overstatement, re-read it against the
  fix: the first draft reintroduced the removed "only".
- tooling: a quote-back segment check against skill text has now been hand-written 3+ times
  (batch 3, batch 4 pass 2, batch 5); propose it as a toolbox jig.
- Carried from earlier handovers (not yet napped):
  - When a mirror gate refuses a commit over a mirrored skill the commit does not stage, look for
    an UNSTAGED edit in that skill: it marks the skill touched; copy it aside, commit, restore it.
  - When a peer's commit will ride on your push to a public repo, scan it for private names first
    and rewrite only the unpushed range (same message and author, keep a backup branch).
  - When fix rounds touch prose, run a column and fence-closure check over the ADDED lines each
    round (queued for meta-skill-writer in the contrib queue).
  - When probing cmd.exe behaviour over ssh, ship a .cmd file: nested inline quoting misleads.
  - When a script globs a skill's reference files, glob every .md in the skill dir: some skills
    keep them beside SKILL.md, not under references/.
  - When several sessions bump one marketplace, take the next number from origin at push time and
    tell the peers which number you took.
  - tooling: reformat_tables.py sits at skills/docs-md-table-formatting/ root, not under scripts/.
  - tooling: the AskUserQuestion premise gate refuses each first ask; mark unmeasured premises
    "unverified" before the first send.
  - tooling: repo-gate's commit gate judges the INDEX, so a pathspec commit of unstaged edits
    reads as drift; stage in an earlier call.
  - When a user's "yes" answers one of several open questions, never read it as approving the
    others.
  - When a pending item says a peer drafted an edit awaiting approval, check the target's working
    tree first: the edit may already be on disk, uncommitted.
  - When a dependency's fixed release needs a newer Python than the project's floor, declare the
    floor with a `python_version` marker: bmk lowers an unmarked floor silently.
  - tooling: gate.py refuses `--gate-cwd` before `--gate`.
  - tooling: a backgrounded `ci_wait ...; echo RC=$?` is refused by block-masked-gate-exit; run
    the wait alone in the background.

## The exact next action

[23], the top-ranked item: archive the 22 pass-1 pointers. Back up first with
`store_manifest.py backup --from /media/srv-main-softdev --scope tree --out <scratchpad>/b5-archive`,
run `ref_map.py --root /media/srv-main-softdev <the 22 slugs>` and re-point citing facts, then
`reconcile_memory_index.py --archive <slug>` per slug (slugs in `.plan/fold-23/batch5/fold/g1..g5.json`),
then `store_manifest.py verify --out <same dir>` must list exactly those 22 as removed.

## Files that matter

- `OPEN-WORK.md` ([23] line), `.plan/fold-23/batch5/fold/g1.json` .. `g5.json`
- `plugins/bitranox/skills/{process-test-design,coding-python-uv,devops-bmk,coding-python-layered-config,coding-python-textual,compuse-ssh}/`

## How to verify

- `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` (expect 0 drifted for devops-bmk and
  coding-python-layered-config).
- CI: `ci_wait.py --ref HEAD` from bitranox:compuse-toolbox in each of the three repos.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
