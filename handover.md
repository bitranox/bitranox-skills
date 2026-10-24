# STALE - read 2026-10-24, work continued

## In flight

- Nothing running in this session. Every peer that gated a push has released it:
  - marketplace: the network-probe peer session pushed `c90231c4` (10.0.2) at 00:43, and the main
    checkout's `master` is `488e08cd` (10.0.3, this batch) on top of it, so the push is a
    fast-forward. NOT pushed yet.
  - lsdsk: the `lsdsk` session pushed 1.15.2 (origin/main `93522cc`, which also brings a
    filelock floor and bmk 3.24.0's Makefile). My commit `996f50e` sits in the worktree
    `apps/utils/lsdsk-wt-fold23` (branch `fold-23-batch4`) on the OLD base `6f82492`. NOT pushed.
- A peer branch sits on top of the unpushed `488e08cd`: `ctxwatch-clear-shells` (`ef0d6b4b`,
  worktree `../bitranox-skills-wt-ctxwatch`, from the pwshpy session, bumps to 10.0.4, edits
  meta-context-watcher). That session waits for this push and then rebases or drops its branch;
  message it after pushing (it signed as "Subagent contents" from the pwshpy session).

## Committed, or not

- bmk: DONE. `a7fd330` (devops-bmk twin plus 3.23.4 bump, untagged) is on origin, folded into
  the bmk session's 3.24.0 release (`15b033d`, CI green on every cell, on PyPI). Its
  devops-bmk pyright paragraph ([121] in bmk's backlog) stays with the next bmk session.
- marketplace `488e08cd`, committed on `master` in the main checkout and on `fold-23-batch4`
  in `.claude/worktrees/fold-23-batch4`: 15 folds across 6 skills, a checklist per skill,
  CHANGELOG 10.0.3, the [23] progress segment and the new [720].
- lsdsk `996f50e`, committed in its worktree only (skill paragraph plus checklist; no
  CHANGELOG line and no bump yet).
- Uncommitted: this `handover.md`. Gitignored and local: `EXECUTION-USER-REVIEW.md` (the two
  batch 4 user decisions, verbatim) and `.plan/fold-23/batch4/fold/` (inputs, journals per
  round, diffs, `slugs18.txt`, `refmap18.json`).

## Decided, and why - do not reopen

- User: batch 4 folds REACH-OK rows first ("REACH-OK first"); tool-repo pushes approved for bmk
  and lsdsk only ("Push bmk + lsdsk"). Verbatim in EXECUTION-USER-REVIEW.md.
- devops-bmk was rewritten to present tense (no "from bmk X.Y.Z", "Before", "no longer", "as
  before"): the user's rule that a skill describes only the latest release; bmk upgrades itself
  on every `make`, so its readers run the latest.
- The 3 REACH-OK rows the skeptic marked ALREADY (pwshpy-overview, second-config-path,
  windows-two-interface-namespaces) get no edit, only the pointer archive. The namespace text
  survives the ipscout 1.7.0 resync (checked at `c90231c4`).
- bmk tracks no `.skillwriter` checklists, so its twin got none; lsdsk tracks them, so it did.

## Decided against, and why

- No bare `X.Y.Z` alternative in the history finder: it matches every version floor and example;
  the review step judges the candidates.
- The one history line in `coding-python-send-mail` stays until a btx_lib_mail push is approved:
  filed as [720].

## Still open, untouched

- [23] pass 2 (27 REACH-PARTIAL rows with a kept pointer, 2 REACH-FAILS); [720]; [710] a
  suspected false positive in block-write-after-sibling-cd (unverified); [28] and [96] wait for
  shadow data; [700] waits for the user; the FOUND items: `OPEN-WORK.md`.
- A memory consolidation (tree dream) is still due per the SessionStart nudge; run it AFTER the
  18-pointer archive, so it sees the store without them.

## Lessons for the next nap

- When a script applies several anchored edits, validate EVERY anchor in every file before
  writing any: a mid-list miss left a half-applied state twice in this session.
- When reflowing prose with textwrap, protect code spans first (swap their spaces for a
  sentinel): a wrap inside a span splits it.
- When telling a peer session a release is on PyPI, check PyPI in the same call first: a false
  "3.24.0 is on PyPI" went out and needed a correction.
- tooling: Workflow `args` must be the value itself; a file path passed there arrives as a
  string and the script's `Object.keys` iterates it.
- tooling: repo-gate judged a scratch-dir `git commit` probe as a commit in the session
  worktree and blocked it; give such probes a literal `cd /abs &&`.
- When a review fixes skill text, re-run the review on the fix DELTA: three rounds each found
  real defects in the previous round's fixes (the joined-text finder drifted from the line
  finder twice).
- Carried from earlier handovers (not yet napped):
  - When a shadow or classifier site cuts a window out of untrusted text for an API, redact the WHOLE
  text first and cut afterwards: a secret pattern needs its context (a key's BEGIN line), and a
  window cut first keeps the body without it.
  - When de-duplicating records re-scanned by a later pass over a sliding window, key on the source
  record's own id (transcript `uuid`), never on text plus occurrence index.
  - When a review fixes a shadow site, re-review the fix delta alone: the re-review found a defect the
  first review and all green gates missed.
  - tooling: gate.py refuses `--gate-cwd` written before its `--gate` (exit 2, nothing run).
  - tooling: block-write-after-sibling-cd refused a call that began with an absolute `cd <repo> &&`
  after a sibling cd'd into `<repo>-wt-30`; `git -C` passed. Filed as [710], unverified.
  - When the user asks mid-turn for a change to the backlog tooling's behaviour, the user's answer
  also settles the "for everyone or per file" question: ask only if they did not say.
  - When pricing a narrower guard variant, replay its own predicate: filtering another predicate's
    labelled firings undercounts (95 vs 211 for [500]). Queued against meta-claude-hooks.
  - When a negative test asserts a word is absent from a whole doc row, assert on the one cell.
  - tooling: the meta-claude-hooks freshness check reports STRUCTURAL without naming which events
    moved; filed as [690].
  - When a script filters a backlog's template row, match the template's exact line, not a
    substring such as `YYYY`; compare the count against the SessionStart count (recurred
    2026-10-23: a `YYYY` substring filter dropped [96] from a listing).
  - tooling: when replaying a transcript-reading PreToolUse hook, cut the transcript at the call
    first; the guard reads only the last 4 MB.
  - When counting classifier shadow rows for a verdict, deduplicate by (transcript, message text)
    first: a rescanned subagent transcript is logged again.
  - When dispatching blind judges or any review-shaped agent, pass `effort: medium` with
    `model: opus`.
  - tooling: ci_wait needs `--timeout 2400` or more here; this repo's CI ran about 35 minutes.
  - tooling: switching a classifier knob to a mode a newer plugin adds leaves older sessions on the
    old behaviour with no log; queued against meta-memory-settings.
  - When you are working IN the repo that owns a bitranox tool and find it broken, fix it in its
    own worktree; the queue-the-symptom rule covers only a tool met while working elsewhere.
  - When a backlog item waits on the user, re-measure its premise before asking.
  - When a GitHub head_sha-filtered run listing goes empty mid-wait, the runs still exist: read
    them by id.
  - tooling: the question-premises gate refuses the first AskUserQuestion each time; mark
    unmeasured premises "unverified" in the option text before the first send.
  - When reusing an earlier round's workflow script, re-check its model and effort pins first.
  - When a review subagent's "Skill gaps" names a count in a lead-in, check whether your own edit
    changed what it counts.
  - When `factedit check` is the validator, read its advisories, not its exit code.
  - When measuring a subagent's output by effort, use the notification's subagent_tokens minus the
    transcript input.
  - When a /goal's pre-registered threshold misses but the arms do not overlap, decide on what the
    plan rests on, and record the weaker reading and the miss.
  - When a user answers an AskUserQuestion without reading it and asks again, the superseding
    answer governs; log both.
  - tooling: `repo-gate.py --mirrors` counts a tool repo's linked worktrees as UNLISTED twins
    (seen again 2026-10-23: `apps/utils/bmk-wt-backlog`).
  - tooling: the auto-mode classifier refused a subagent's Bash edit of plugin.json; keep version
    bumps in the controller.
  - When a rule depends on what an OMITTED subagent field inherits, read `~/.claude/settings.json`
    first and probe the override.
  - When an OPEN-WORK line carries several dated segments, the latest segment's "next:" is current.
  - When a handover's next action names counts, recount them from the cited data first.
  - When a mirrored skill's text carries a package version floor, check every pin of that floor
    (`jev_shadow.py` JEV_JUDGE_FLOOR); run `repo-gate.py --ci` before pushing.
  - tooling: bmk's floor-pin reconcile drops a hand-written `exclude-newer-package` timestamp once
    the floor is older than the cooldown.
  - When a PreToolUse gate refuses a git command, stage or fetch in a separate earlier command.

## The exact next action

[23] is the top-ranked open item, and both of these finish its pass 1. Do them in order:

1. Marketplace: `git fetch origin`,
   check that `origin/master` is an ancestor of `master` (`488e08cd`), then
   `git push origin master`
   (its pre-push gate runs about 5 min). Watch CI with `ci_wait.py --ref HEAD --timeout 2700`
   from bitranox:compuse-toolbox, then tell the pwshpy session (see In flight) that master moved.
2. lsdsk, in `apps/utils/lsdsk-wt-fold23`: fetch, `git rebase origin/main`, add one CHANGELOG
   line under Unreleased, `make bump-patch` (expect 1.15.3), `make test`, commit the churn, push
   `HEAD:main`, watch CI, then `git worktree remove` it and delete the branch.
3. Ask the user to run `/plugin marketplace update bitranox-skills` and `/reload-plugins`.
   Only after that, archive the 18 pointers listed in `.plan/fold-23/batch4/fold/slugs18.txt`:
   re-point the 4 facts that cite three of them (`refmap18.json`), snapshot the store,
   `reconcile_memory_index.py --archive`, `--check-tree` TOTAL 0, and a manifest diff showing only
   those slugs. Then remove `.claude/worktrees/fold-23-batch4`.

## Files that matter

- `.plan/fold-23/batch4/merged.json`: the batch 4 check (reach, skeptic) per slug.
- `.plan/fold-23/batch4/fold/`: `g1..g6.json` (inputs), `journal-*.json` (RED, GREEN, reviews per
  round), `slugs18.txt`, `refmap18.json`, `final-r4.patch`.
- `plugins/bitranox/skills/*/.skillwriter/checklist-20261023-fold23-batch4.md`.
- `OPEN-WORK.md` lines [23], [720].

## How to verify

- marketplace pushed: `git -C <repo> log -1 origin/master` names the 10.0.3 commit; CI via
  `ci_wait.py --ref HEAD`.
- bmk: `git -C ../../apps/utils/bmk merge-base --is-ancestor a7fd330 origin/master`.
- lsdsk: `grep '"version"' .claude-plugin/plugin.json` on origin/main reads 1.15.3.
- archive: `reconcile_memory_index.py --check-tree <tree anchor>` reports TOTAL 0.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
