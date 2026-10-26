# Handover 2026-10-26: [23] batch 5 pass 2 shipped (25 folds, 4 repos); cut the 25 hooks next

## In flight

- Nothing of this session is running: every CI wait ended green, no subagent, workflow or
  background shell is live (`ps --ppid` clean).
- Peer worktrees in this repo, NOT mine: `.claude/worktrees/ipscout-snmp-twin` (the ipscout
  session syncing its drifted `coding-python-network-probe` twin) and `.claude/worktrees/pwshpy45-twin`
  (the pwshpy session, its [45] item). Leave them alone.

## Committed, or not

- Pushed and CI green: bitranox-skills 10.0.16 (`3933259e`); twins lib_layered_config `328c63c`
  (plugin 7.3.4), pwshpy `d41caba` and bmk `0aadc91` (skill-only, no bump; each session ships it in
  its next release), all with CI and CodeQL green. Memory store `5a40fef` (pass-1 archive of 22)
  and `3839877` (two fact updates) pushed.
- NOT done: the 25 pass-2 pointers still carry their long hooks; 4 of their bodies state claims the
  fold measured false. 10.0.16 is not installed here yet.
- Gitignored and local: `.plan/fold-23/batch5/pass2/` (h1..h6.json inputs, journal-fold.jsonl,
  by-label.json, r1.json, r2/r3 inputs and results, review-r1.json, analyze.py, make_checklists.py
  plus disp_pass2.py, newhooks.json, bodies/ with the 4 corrected bodies).
- `EXECUTION-USER-REVIEW.md` (gitignored) has the pass-2 owner decision entry.
- Not mine, left alone: the main checkout's untracked `o`.

## Decided, and why - do not reopen

- User: "start [23] pass 2"; "Push all three myself" (twins); "Push it along" for the fleet-wide
  `ci: setup-uv v10.3.2` commit sitting in the twin repos (it was already on origin by push time).
- Rows stay with their recorded owner even where the reach lens named a better one (the two
  German-Windows rows in coding-python-pwshpy, the socket-timeout row in coding-resilience): same
  rule as batch 4 pass 2, logged in `EXECUTION-USER-REVIEW.md`; the kept short pointer covers the
  moment the owner is not loaded.
- The four refuted claims are corrected in the skills, NOT carried: pydantic 2.14.1 `extra="allow"`
  arm does not swallow its sibling (a bare dict arm does); a rebuilt same-version wheel was re-read
  on uv 0.13.0; bmk quotes ARGS in push/commit (ship stays unquoted); pyright 1.1.380-1.1.414
  accept a fully quoted recursive alias (it is a plain str at runtime).
- Declined review/GREEN gaps are recorded in each skill's
  `.skillwriter/checklist-20261025-fold23-batch5-pass2.md`.

## Decided against, and why

- No compuse-ssh cross-reference for the decimal-comma rule: its pointer stays and fires there.
- The vendored upstream uv escape-hatch list (`uv cache clean`, `--reinstall`) stays unedited; the
  new paragraph names the exception instead.

## Still open, untouched

- [23] steps (1)-(3) above plus batch 6: `OPEN-WORK.md` [23] line.
- [760] quotecheck jig proposal, awaiting the user's OK: `OPEN-WORK.md`.
- [730], [740], [750] and the rest: `OPEN-WORK.md`. A tree dream is due; [730] is its input.
- Queued tooling contributions (contrib_queue, this repo's queue): ref_map misses bare-prose slug
  mentions; store-edit-guard misses Bash writes to the store.

## Lessons for the next nap

- tooling: when archiving facts, grep the slugs as plain text over `facts/` too: ref_map counts
  only `[[links]]` and missed a deliberate prose mention (queued against meta-self-improve).
- tooling: store-edit-guard blocks Edit/Write on a fact but not a python `write_text` from Bash;
  use factedit for re-points (queued against hook:store-edit-guard).
- When mirroring a skill edit into a twin repo another session works in, tell that session
  first: the uncommitted twin text makes its repo-gate refuse every commit until both sides land.
- When a twin repo holds an unpushed commit you did not make, check whether it is a fleet-wide
  template commit before pushing over it, and ask; it can be pushed by its owner meanwhile.
- When quote-checking subagent quote-backs, split each quote at ' ... ', ' / ', '|' and newlines
  and strip `**`, backticks and wrapping quotes before the substring check: agents join lines and
  annotate (see [760]).
- Carried from earlier handovers (not yet napped):
  - When `store_manifest.py backup --out` points inside the softdev tree, `--check-tree` counts the
    copied `CLAUDE.local.md` files as levels: put the backup in the scratchpad.
  - When quote-checking a fold against installed text after fix rounds, use each row's LATEST
    round's quotes: an earlier round quoted text a fix later replaced.
  - When a mirrored skill changes on both sides, commit both twins before any push, and
    fast-forward the marketplace main checkout's master to the worktree commit first: the twin's
    gate reads it.
  - When a CHANGELOG line summarises a fix that removed an overstatement, re-read it against the
    fix: the first draft reintroduced the removed "only".
  - When a mirror gate refuses a commit over a mirrored skill the commit does not stage, look for
    an UNSTAGED edit in that skill: copy it aside, commit, restore it.
  - When a peer's commit will ride on your push to a public repo, scan it for private names first
    and rewrite only the unpushed range (keep a backup branch).
  - When fix rounds touch prose, run a column and fence-closure check over the ADDED lines each
    round.
  - When probing cmd.exe behaviour over ssh, ship a .cmd file: nested inline quoting misleads.
  - When a script globs a skill's reference files, glob every .md in the skill dir.
  - When several sessions bump one marketplace, take the next number from origin at push time and
    tell the peers which number you took.
  - tooling: reformat_tables.py sits at skills/docs-md-table-formatting/ root, not under scripts/.
  - tooling: the AskUserQuestion premise gate refuses each first ask; mark unmeasured premises
    "unverified" before the first send.
  - tooling: repo-gate's commit gate judges the INDEX; stage in an earlier call.
  - When a user's "yes" answers one of several open questions, never read it as approving the
    others.
  - When a pending item says a peer drafted an edit awaiting approval, check the target's working
    tree first.
  - When a dependency's fixed release needs a newer Python than the project's floor, declare the
    floor with a `python_version` marker: bmk lowers an unmarked floor silently.
  - tooling: gate.py refuses `--gate-cwd` before `--gate`.
  - tooling: a backgrounded `ci_wait ...; echo RC=$?` is refused by block-masked-gate-exit; run the
    wait alone in the background.

## The exact next action

[23], the top-ranked item. Ask the user to run `/plugin marketplace update bitranox-skills` and
`/reload-plugins`; then quote-check the 25 rows against the installed
`~/.claude/plugins/cache/bitranox-skills/bitranox/10.0.16/skills/` (adapt
`.plan/fold-23/batch4/pass2/qcheck_installed.py`, quotes from the latest round per row:
`.plan/fold-23/batch5/pass2/journal-fold.jsonl` GREEN opus, overridden by `r2-result.json` and the
r3 bmk answer). Then `store_manifest.py backup --from <tree top> --scope tree --out
<scratchpad>/b5p2-cut`, and per slug in `newhooks.json`:
`factedit.py apply --slug <slug> --from <tree top>/projects --hook "<newhook>"`, adding
`--body-file .plan/fold-23/batch5/pass2/bodies/<slug>.md` for the 4 slugs that have one. Verify:
manifest shows 25 changed, 0 removed; commit only those 25 fact files plus the projects/ index
change (the store has ~84 peer-dirty files: stage by explicit path).

## Files that matter

- `OPEN-WORK.md` ([23], [760]), `.plan/fold-23/batch5/pass2/newhooks.json`,
  `.plan/fold-23/batch5/pass2/bodies/`, `.plan/fold-23/batch5/pass2/analyze.py`
- `.plan/fold-23/batch4/pass2/qcheck_installed.py` (the installed-text checker to adapt)

## How to verify

- `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` (devops-bmk, coding-python-pwshpy,
  coding-python-layered-config in sync).
- CI: `ci_wait.py --ref HEAD` from bitranox:compuse-toolbox in bitranox-skills, bmk, pwshpy and
  lib_layered_config.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
