# STALE - read 2026-10-26, work continued

## In flight

- A `run_in_background` shell of the old session waits for CI on the pass-1 commit `ed942844`
  (`ci_wait.py --ref HEAD`, output in the old session's scratchpad `ci-b6p1.out`). It survives the
  clear and reports into the next conversation; its verdict is the CI result for 10.0.20. If it is
  gone, re-run `ci_wait.py --sha ed9428447556caa467b9dc3517c12ad75bc07a4d` (bitranox:compuse-toolbox).
- No subagent or workflow is running.
- Worktree `.claude/worktrees/fold-23-b6p1` (branch `fold-23-b6p1`) holds the pass-1 commit and
  this handover commit, both pushed to master. Remove it with wtclean once nothing needs it.
- Peer worktree `.claude/worktrees/ipscout-mac-twin` is the ipscout session's; leave it alone.

## Committed, or not

- Pushed: bitranox-skills 10.0.20 `ed942844` (pre-push gate green); memory store `cb6e4cb` (batch 5
  pass 2: 25 hooks cut, 4 bodies corrected); backlog commits for both.
- NOT done: the 14 batch-6 archive facts are still live in the store (archive only after 10.0.20
  is installed); the 37 cut rows (pass 2) are untouched.
- Gitignored and local (main checkout): `.plan/fold-23/batch6/` (census.json, r1/p1/rn/pn.json,
  roster.json, journal-check.jsonl, merged.json, dispositions.json, fold/ with g1-g3.json, pre/
  snapshots, journal-fold.jsonl, journal-r2.jsonl, qs-r2-questions.json, pass1.diff,
  make_checklists.py), `.plan/fold-23/batch5/pass2/qcheck_installed.py` and `apply_cut.py`,
  `EXECUTION-USER-REVIEW.md` (batch 6 adjudication and the user's pass-1 choice).
- Not mine, left alone: the main checkout's untracked `o` (19 bytes, "Nothing to upgrade").

## Decided, and why - do not reopen

- User: "start batch 6"; "Pass 1 now, both groups (Recommended)" - fold the 14 archive rows in one
  release, archive them after the install.
- Archive vs cut is my adjudication (logged in `EXECUTION-USER-REVIEW.md`): archive only where the
  skeptic found nothing host-relevant lost and reach found the owner loaded; these are host and
  company levels, so most bodies keep host data that a public skill cannot hold.
- compuse-ssh's trusted-subnet rule is `accept-new` plus a separate known_hosts file plus
  `ssh-keygen -R ... -f` that file and one retry, matching `fleet_ssh.py`; the archived fact
  `ssh-internal-accept-host-keys` still says `no` and goes away in the archive step.
- `store_manifest verify` cannot show a hook or body change (it keys on level, slug, title, pin);
  the batch 5 pass 2 cut was verified line by line instead (queued against script:store_manifest).

## Decided against, and why

- No on-disk-version check for a running unbound in net-firewall-pfsense: no verified way to read
  the running daemon's version.
- GREEN gaps declined (in each `.skillwriter/checklist-20261026-fold23-batch6-pass1.md`): keeping a
  busy-port skip, other OSes beyond the Windows skip, AttributeError wording on older Pythons, an
  openvpn restart form.

## Still open, untouched

- [23] steps (1)-(4) and batch 6 pass 2: `OPEN-WORK.md` [23] line.
- [770] guard for the bmk push-message fact (engine advisory): `OPEN-WORK.md`.
- Queued tooling contributions (contrib_queue, this repo's queue): ref_map misses bare-prose slug
  mentions; store-edit-guard misses Bash writes to the store; store_manifest verify cannot see a
  hook or body change.
- [760] quotecheck jig proposal, awaiting the user's OK; [730], [740], [750] and the rest:
  `OPEN-WORK.md`. A tree dream is due; [730] is its input.

## Lessons for the next nap

- When folding facts from host or company levels into public skills, default to cut (keep the fact
  with a short hook): their bodies carry host data the sessions on that host still use.
- When a skeptic or RED agent reports that the owner skill contradicts itself on the rule being
  folded, reconcile the skill in the same pass before archiving the fact.
- When a workflow round's result is not saved by its script, copy it into the plan dir at once: a
  round-3 answer had to be recovered from subagent transcripts.
- When a Workflow needs per-group inputs, write them to a file the agents read (scoring fields
  removed); a placeholder `args` launch had to be stopped.
- When substring-checking subagent quote-backs, split each quote at ' ... ', ' / ', '|', newlines,
  `" and "`, `" (...) "` and `[...]`, strip `**`, backticks and wrapping quotes, expect run-together
  list items, and treat a punctuation-only miss after a reorder as a match (see [760]).
- tooling: `store_manifest verify` reports identical after a hook-only or body-only edit (queued).
- tooling: the AskUserQuestion premise gate refuses each first ask; mark recorded-but-unmeasured
  premises "unverified" before the first send.
- Carried from earlier handovers (not yet napped):
  - tooling: when archiving facts, grep the slugs as plain text over `facts/` too: ref_map counts
    only `[[links]]` and missed a deliberate prose mention (queued against meta-self-improve).
  - tooling: store-edit-guard blocks Edit/Write on a fact but not a python `write_text` from Bash;
    use factedit for re-points (queued against hook:store-edit-guard).
  - When mirroring a skill edit into a twin repo another session works in, tell that session first:
    the uncommitted twin text makes its repo-gate refuse every commit until both sides land.
  - When a twin repo holds an unpushed commit you did not make, check whether it is a fleet-wide
    template commit before pushing over it, and ask; it can be pushed by its owner meanwhile.
  - When `store_manifest.py backup --out` points inside the softdev tree, `--check-tree` counts the
    copied `CLAUDE.local.md` files as levels: put the backup in the scratchpad.
  - When quote-checking a fold against installed text after fix rounds, use each row's LATEST
    round's quotes: an earlier round quoted text a fix later replaced.
  - When a mirrored skill changes on both sides, commit both twins before any push, and
    fast-forward the marketplace main checkout's master to the worktree commit first: the twin's
    gate reads it.
  - When a CHANGELOG line summarises a fix that removed an overstatement, re-read it against the
    fix: the first draft reintroduced the removed "only".
  - When a mirror gate refuses a commit over a mirrored skill the commit does not stage, look for an
    UNSTAGED edit in that skill: copy it aside, commit, restore it.
  - When a peer's commit will ride on your push to a public repo, scan it for private names first
    and rewrite only the unpushed range (keep a backup branch).
  - When fix rounds touch prose, run a column and fence-closure check over the ADDED lines each
    round.
  - When probing cmd.exe behaviour over ssh, ship a .cmd file: nested inline quoting misleads.
  - When a script globs a skill's reference files, glob every .md in the skill dir.
  - When several sessions bump one marketplace, take the next number from origin at push time and
    tell the peers which number you took.
  - tooling: reformat_tables.py sits at skills/docs-md-table-formatting/ root, not under scripts/.
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

[23], the top-ranked item. Confirm CI green on `ed942844`; then ask the user to run
`/plugin marketplace update bitranox-skills` and `/reload-plugins`. Then quote-check the 14 archive
rows against the installed `~/.claude/plugins/cache/bitranox-skills/bitranox/10.0.20/skills/`:
adapt `.plan/fold-23/batch5/pass2/qcheck_installed.py` to `.plan/fold-23/batch6/fold/` (rows from
g1-g3.json; GREEN quotes from journal-fold.jsonl overridden by journal-r2.jsonl; RED g3 quotes for
the 7 ALREADY rows whose skills did not change; soundtouch-decloud rows against its own repo),
with a control run on 10.0.17. Then archive per the [23] line's step (3).

## Files that matter

- `OPEN-WORK.md` ([23], [770]); `.plan/fold-23/batch6/dispositions.json` (the 14 archive slugs),
  `.plan/fold-23/batch6/fold/g1.json`, `g2.json`, `g3.json`, `journal-fold.jsonl`, `journal-r2.jsonl`
- `.plan/fold-23/batch5/pass2/qcheck_installed.py` (the installed-text checker to adapt)
- `plugins/bitranox/skills/{process-test-design,coding-input-sanitization,net-firewall-pfsense,compuse-ssh,infra-proxmox}/`

## How to verify

- CI: `ci_wait.py --ref HEAD` from bitranox:compuse-toolbox.
- Local gate: `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci`.
- Memory store: `python3 <plugin>/skills/meta-self-improve/reconcile_memory_index.py --check-tree
  <tree top>` (TOTAL 5 before the archive).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
