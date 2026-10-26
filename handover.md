# Handover 2026-10-26: [23] batch 6 pass 2 shipped (10.0.23 + 5 twins); install, then cut the 37 hooks

## In flight

- A `run_in_background` shell of the old session waits for marketplace CI on `8efa6963` (10.0.23)
  with `ci_wait.py --sha 8efa69633e9596720448636c48d623ac38cffb1e`. It survives the clear and
  reports into the next conversation; its verdict is the CI result for 10.0.23. If it is gone,
  re-run that command (bitranox:compuse-toolbox).
- No subagent or workflow is running. The pass-2 worktrees (marketplace `fold-23-b6p2`, the pwshpy
  and btx_lib_mail `fold-23-b6p2-twin`) are removed; their branches are merged and deleted.
- Peer worktree `.claude/worktrees/lib-log-rich-702-twin` is the lib_log_rich session's; leave it.

## Committed, or not

- Pushed, CI green except where noted: bitranox-skills 10.0.23 `8efa6963` (CI pending, above);
  pwshpy 1.8.1 `cff9539`; lib_layered_config plugin 7.3.5 `8bd7b2b`; btx_lib_mail 4.6.2 `8d82962`;
  check_zpools 4.0.8 `26fb4dc`; soundtouch-decloud 1.10.6 `9bd119e`. No PyPI release was cut for
  any of them (`make release` tags the committed version later).
- Memory store: batch 6 pass 1 archive `d8af1fd` pushed. The 37 pass-2 hooks are NOT cut yet.
- Gitignored and local (main checkout): `.plan/fold-23/batch6/pass2/` (g*.json groups, pre/
  snapshots, journal-fold.jsonl, journal-r2.jsonl, journal-r3.jsonl, review/, newhooks.json,
  qcheck_live.py, make_checklists.py, build_pass2.py), `EXECUTION-USER-REVIEW.md` (pass-2
  decisions). Not mine, left alone: the main checkout's untracked `o`.

## Decided, and why - do not reopen

- User: "go" for pass 2; "Push all six (Recommended)" for the twin batch plus 10.0.23.
- pwshpy 1.8.1 carries a lib_log_rich 7 fix (`cli_logdemo` passes `ConsoleTheme`): bmk raised the
  floor to 7.0.1 and the gate went red on exactly that call. The pwshpy session agreed to 1.8.1 and
  the push; 1.8.1 also dates its pushed-but-unreleased [124] CHANGELOG entries, which it accepted.
- `pfsense.py doctor` now agrees with the skill (box DNS before the upgrade lock, both lock paths,
  no quad-100 forward zone); the dns add/rm restart is left as [780].
- Fold owner is always the disposition owner, never the reach lens's better_owner (batch 4/5 rule).
- Details and reversal steps: `EXECUTION-USER-REVIEW.md`, entry "[23] batch 6 pass 2".

## Decided against, and why

- Pinning lib_log_rich below 7 in pwshpy: bmk re-raises floors on every gate run; the consumer fix
  is the root cause.
- Declined GREEN round-3 gaps: pwshpy's "5.1 and 7" shell cell (the table header defers to its
  note), soundtouch's SETUP "do not reboot first" (scoped to that section), zram's second
  verification list (a different moment).

## Still open, untouched

- [23] remaining steps (hook cut, one body fix, batch 7): `OPEN-WORK.md` [23].
- [780] pfsense dns add/rm unbound restart: `OPEN-WORK.md`.
- check_zpools defaultconfig.toml "(comma-separated)" comments and the "Failed to send alert"
  skip log: check_zpools `OPEN-WORK.md` [10], [20].
- [760] quotecheck jig proposal: still unanswered (the user's "yes" covered [23] only).
- Queued tooling contributions (contrib_queue, this repo's queue): ref_map misses bare-prose slug
  mentions; store-edit-guard misses Bash writes to the store; store_manifest verify cannot see a
  hook or body change.
- [730], [740], [750], [770] and the rest: `OPEN-WORK.md`. A tree dream is due; [730] is its input.

## Lessons for the next nap

- When a mirrored skill's twin repo is another live session's checkout, NEVER write into it, not
  even temporarily: a two-time SKILL.md overwrite there ran during that session's own gate, and it
  objected. Ask that session first.
- tooling: repo-gate cannot pair a twin committed in a linked worktree while that repo's main
  checkout is on another branch (the marketplace commit reads the twin from the main checkout; the
  twin's push needs the marketplace committed), so the only route that passed wrote into the
  peer's tree - a gap to queue against hook:repo-gate.
- When a twin is committed in a linked worktree, fast-forward that repo's main checkout (or push
  it) before the marketplace commit and push: the gate reads the main checkout.
- When bmk raises a floor across a major during make test, a twin commit's gate can go red for an
  unrelated reason: fix the consumer as its own change with a RED test, never pin the floor.
- When quote-back agents join several quotes with labels in one string, the substring checker
  misses them: say "one quote per field, a second quote on its own line" in the prompt.
- When a loop runs git in several repos, the commit gate cannot read the target and judges the
  session repo: one repo per call with a literal cd.
- When a fold editor reports a contradiction in a tool the skill ships (pfsense.py), fix the tool in
  the same release with tests, or the skill ships disagreeing with its own tool.
- tooling: a fifth hand-written quote checker this session; supports the [760] jig.
- tooling: the AskUserQuestion premise gate refuses each first ask; mark recorded-but-unmeasured
  premises "unverified" before the first send.
- Carried from earlier handovers (not yet napped):
  - tooling: when archiving facts, grep the slugs as plain text over `facts/` too: ref_map counts
    only `[[links]]` and missed a deliberate prose mention (queued against meta-self-improve).
  - tooling: store-edit-guard blocks Edit/Write on a fact but not a python `write_text` from Bash;
    use factedit for re-points (queued against hook:store-edit-guard).
  - tooling: `store_manifest verify` reports identical after a hook-only or body-only edit (queued).
  - When folding facts from host or company levels into public skills, default to cut (keep the
    fact with a short hook): their bodies carry host data the sessions on that host still use.
  - When a skeptic or RED agent reports that the owner skill contradicts itself on the rule being
    folded, reconcile the skill in the same pass before archiving the fact.
  - When a workflow round's result is not saved by its script, copy its journal into the plan dir
    at once.
  - When a Workflow needs per-group inputs, write them to a file the agents read.
  - When mirroring a skill edit into a twin repo another session works in, tell that session first.
  - When a twin repo holds an unpushed commit you did not make, check whether it is a fleet-wide
    template commit before pushing over it, and ask.
  - When `store_manifest.py backup --out` points inside the softdev tree, `--check-tree` counts the
    copied `CLAUDE.local.md` files as levels: put the backup in the scratchpad.
  - When quote-checking a fold against installed text after fix rounds, use each row's LATEST
    round's quotes.
  - When a CHANGELOG line summarises a fix that removed an overstatement, re-read it against the fix.
  - When a mirror gate refuses a commit over a mirrored skill the commit does not stage, look for an
    UNSTAGED edit in that skill.
  - When a peer's commit will ride on your push to a public repo, scan it for private names first.
  - When fix rounds touch prose, run a column and fence-closure check over the ADDED lines.
  - When probing cmd.exe behaviour over ssh, ship a .cmd file.
  - When a script globs a skill's reference files, glob every .md in the skill dir.
  - When several sessions bump one marketplace, take the next number from origin at push time.
  - tooling: reformat_tables.py sits at skills/docs-md-table-formatting/ root, not under scripts/.
  - tooling: repo-gate's commit gate judges the INDEX; stage in an earlier call.
  - When a user's "yes" answers one of several open questions, never read it as approving the
    others.
  - When a pending item says a peer drafted an edit awaiting approval, check the target first.
  - When a dependency's fixed release needs a newer Python than the floor, declare the floor with a
    `python_version` marker.
  - tooling: gate.py refuses `--gate-cwd` before `--gate`.
  - tooling: a backgrounded `ci_wait ...; echo RC=$?` is refused by block-masked-gate-exit.

## The exact next action

[23], the top-ranked item. Confirm CI green on `8efa6963`; then ask the user to run
`/plugin marketplace update bitranox-skills`, `/plugin marketplace update soundtouch-decloud` and
`/reload-plugins`. Then quote-check the 37 rows against the INSTALLED text (adapt
`.plan/fold-23/batch6/pass2/qcheck_live.py` to the cache dirs of bitranox 10.0.23 and
soundtouch-decloud 1.10.6; latest round per row: r3 over r2 over r1), with a control on 10.0.22.
Then review `newhooks.json` (37 editor drafts, trigger-first, <= 297 chars) and cut each hook with
`factedit apply --hook-file` at its level, as `.plan/fold-23/batch5/pass2/apply_cut.py` did; in the
same pass correct the body of `feedback-ssh-connecttimeout-does-not-bound-the-session-add-a-total-timeout`
("stall in kex": per ssh_config(5) ConnectTimeout covers the key exchange).

## Files that matter

- `OPEN-WORK.md` ([23], [780]); `.plan/fold-23/batch6/pass2/newhooks.json`,
  `.plan/fold-23/batch6/pass2/qcheck_live.py`, `.plan/fold-23/batch6/pass2/g{P,F,A,B,C,D}.json`,
  `.plan/fold-23/batch6/pass2/journal-{fold,r2,r3}.jsonl`
- `.plan/fold-23/batch5/pass2/apply_cut.py` (the cut tool to adapt)
- `plugins/bitranox/skills/net-firewall-pfsense/scripts/pfsense.py` ([780])

## How to verify

- CI: `ci_wait.py --ref HEAD` from bitranox:compuse-toolbox (and `--sha` for the five twins).
- Local gate: `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci`.
- Mirrors: `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` (coding-python-logging drift
  belongs to the lib_log_rich session).
- Memory store: `python3 <plugin>/skills/meta-self-improve/reconcile_memory_index.py --check-tree
  <tree top>` (TOTAL 4 after `d8af1fd`).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
