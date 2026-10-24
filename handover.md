# Handover 2026-10-24: [23] batch 4 pass 2 shipped (29 rows, 5 repos); pointer cut next

## In flight

- Nothing of this session is running: every gate and CI wait ended, no subagent or workflow is live.
- The bmk session releases bmk 3.25.2 (tag, PyPI) on its own; it carries this session's 65a09cc.
  Nothing for this repo depends on that release.
- Worktree `.claude/worktrees/fold23-b4p2` (branch fold23-b4p2, equal to origin/master once this
  handover is pushed) is removed with its branch right after the push; the lsdsk worktree is
  already removed.

## Committed, or not

- Everything is committed and pushed: bitranox-skills 10.0.9 (25 rows) and 10.0.11 (devops-bmk),
  lsdsk 1.15.5, lib_layered_config plugin 7.3.2 (plus a filelock CVE dev floor), btx_lib_mail
  4.6.1, bmk 3.25.2 (pushed by the bmk session). No tag, no PyPI release of my own (user choice).
- Not mine, left alone: the main checkout's untracked `o`; the lsdsk main checkout sits one commit
  behind its origin (the lsdsk session's checkout).
- Gitignored and local: `EXECUTION-USER-REVIEW.md` (two new entries), `.plan/fold-23/batch4/pass2/`
  (group inputs, pre-edit snapshots, round results, review texts, dispositions).

## Decided, and why - do not reopen

- Owner choice per row (EXECUTION-USER-REVIEW.md, 2026-10-24): each row folds into its recorded
  owner only, never a reach lens's second site; the quoted-version REACH-FAILS row went to
  coding-bash-reference, where it fires.
- User: "All four (Recommended)" - push bmk, lib_layered_config, btx_lib_mail and lsdsk, no tag,
  no PyPI; and "Finish shipping first (Recommended)" before this handover.
- Version order was negotiated with peers: 10.0.8 bmk, 10.0.9 mine, 10.0.10 ipscout, 10.0.11 mine.
- btx_lib_mail is PUBLIC: the peer handover commit that rode on my push named three private repos;
  rewrote only that unpushed commit (7d573f9, same message and author, backup branch
  backup-handover-8a4ff7a in btx_lib_mail) before pushing (EXECUTION-USER-REVIEW.md).

## Decided against, and why

- coding-python-uv's description ("measured on 0.11.x") was not touched in the fold: frontmatter
  is router text; filed as [750].
- The warm-cache rescue from a uv fact was not carried: it did not reproduce on uv 0.13.0.

## Still open, untouched

- [23] next step (top rank), [730], [740] (mechanism now measured), [750]: `OPEN-WORK.md`.
- lib_layered_config `OPEN-WORK.md` [60] (a docstring defect found while folding), untracked there.
- A tree dream is due per the SessionStart nudge; [730] is its input.

## Lessons for the next nap

- When a mirror gate refuses a commit over a mirrored skill the commit does not stage, look for an
  UNSTAGED edit in that skill: it marks the skill touched; copy it aside, commit, restore it.
- When a peer's commit will ride on your push to a public repo, scan it for private names first
  and rewrite only the unpushed range (same message and author, keep a backup branch).
- When fix rounds touch prose, run a column and fence-closure check over the ADDED lines each round:
  three fix rounds each left new over-100 lines and one an unclosed fence (queued for
  meta-skill-writer in the contrib queue).
- When probing cmd.exe behaviour over ssh, ship a .cmd file: the nested quoting of an inline probe
  mangled it into a misleading error.
- When a script globs a skill's reference files, glob every .md in the skill dir: some skills keep
  them beside SKILL.md, not under references/.
- When several sessions bump one marketplace, take the next number from origin at push time and
  tell the peers which number you took; a local bump is a reservation nobody else can see.
- tooling: reformat_tables.py sits at skills/docs-md-table-formatting/ root, not under scripts/.
- tooling: the AskUserQuestion premise gate refused each first ask again; mark unmeasured premises
  "unverified" before the first send.
- Carried from earlier handovers (not yet napped):
  - When a user's "yes" answers one of several open questions, never read it as approving the
    others: a peer session applied two memory-fact rewrites on a "yes, release now" meant for a
    release.
  - When a pending item says a peer drafted an edit awaiting approval, check the target's working
    tree first: the edit may already be on disk, uncommitted.
  - When a dependency's fixed release needs a newer Python than the project's floor, declare the
    floor with a `python_version` marker: bmk lowers an unmarked floor to the newest release the
    oldest supported Python can install, silently.
  - When a mirrored skill changes on both sides, commit the tool repo while the marketplace twin
    sits uncommitted with matching text, commit the marketplace, then push the marketplace first:
    the tool repo's push gate needs the twin committed.
  - tooling: repo-gate's commit gate judges the INDEX, so a pathspec commit of unstaged edits
    reads as drift; stage in an earlier call (recurred, see feedback-repo-gate-pre-evaluates).
  - tooling: gate.py refuses `--gate-cwd` before `--gate` (recurred 2026-10-24).
  - tooling: a backgrounded `ci_wait ...; echo RC=$?` is refused by block-masked-gate-exit; wrap the
    wait in gate.py, whose report carries the gate's own exit code.
  - tooling: repo-gate blocked an OPEN-WORK-only commit over a twin drift it did not touch; filed
    as [740].
  - When a script applies several anchored edits, validate EVERY anchor in every file before
    writing any.
  - When reflowing prose with textwrap, protect code spans first.
  - When telling a peer session a release is on PyPI, check PyPI in the same call first.
  - tooling: Workflow `args` must be the value itself; a file path arrives as a string.
  - tooling: repo-gate judged a scratch-dir `git commit` probe as a commit in the session
    worktree; give such probes a literal `cd /abs &&`.
  - When a review fixes skill text, re-run the review on the fix DELTA.
  - When a shadow or classifier site cuts a window out of untrusted text for an API, redact the
    WHOLE text first and cut afterwards.
  - When de-duplicating records re-scanned by a later pass over a sliding window, key on the
    source record's own id (transcript `uuid`).
  - When a review fixes a shadow site, re-review the fix delta alone.
  - tooling: block-write-after-sibling-cd refused a call that began with an absolute `cd <repo> &&`
    after a sibling cd'd into `<repo>-wt-30`; `git -C` passed. Filed as [710], unverified.
  - When the user asks mid-turn for a change to the backlog tooling's behaviour, the answer also
    settles "for everyone or per file": ask only if they did not say.
  - When pricing a narrower guard variant, replay its own predicate (95 vs 211 for [500]).
  - When a negative test asserts a word is absent from a whole doc row, assert on the one cell.
  - tooling: the meta-claude-hooks freshness check reports STRUCTURAL without naming the events;
    filed as [690].
  - When a script filters a backlog's template row, match the template's exact line, not `YYYY`.
  - tooling: when replaying a transcript-reading PreToolUse hook, cut the transcript at the call
    first; the guard reads only the last 4 MB.
  - When counting classifier shadow rows for a verdict, deduplicate by (transcript, message text).
  - When dispatching blind judges or any review-shaped agent, pass `effort: medium` with
    `model: opus`.
  - tooling: ci_wait needs `--timeout 2400` or more here; this repo's CI ran about 35 minutes.
  - tooling: switching a classifier knob to a mode a newer plugin adds leaves older sessions on
    the old behaviour with no log; queued against meta-memory-settings.
  - When you are working IN the repo that owns a bitranox tool and find it broken, fix it in its
    own worktree.
  - When a backlog item waits on the user, re-measure its premise before asking.
  - When a GitHub head_sha-filtered run listing goes empty mid-wait, read the runs by id.
  - tooling: the question-premises gate refuses the first AskUserQuestion each time; mark
    unmeasured premises "unverified" in the option text before the first send.
  - When reusing an earlier round's workflow script, re-check its model and effort pins first.
  - When a review subagent's "Skill gaps" names a count in a lead-in, check whether your own edit
    changed what it counts.
  - When `factedit check` is the validator, read its advisories, not its exit code.
  - When measuring a subagent's output by effort, use the notification's subagent_tokens minus
    the transcript input.
  - When a /goal's pre-registered threshold misses but the arms do not overlap, decide on what the
    plan rests on, and record the weaker reading and the miss.
  - When a user answers an AskUserQuestion without reading it and asks again, the superseding
    answer governs; log both.
  - tooling: `repo-gate.py --mirrors` counts a tool repo's linked worktrees as UNLISTED twins.
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

[23] is the top-ranked open item. Ask the user to run `/plugin marketplace update bitranox-skills`
then `/reload-plugins` (installed must be >= 10.0.11), then quote-check the 29 pass-2 rows against
the installed text and cut each pointer as the [23] line's next field says.

## Files that matter

- `OPEN-WORK.md` lines [23], [730], [740], [750].
- `.plan/fold-23/batch4/pass2/p1.json` .. `p7.json` (rows, owners, live skill dirs),
  `r1/` `r2/` `r3/` (round results, reviews, dispositions), `qs-r2.json` (the GREEN questions).
- `plugins/bitranox/skills/*/.skillwriter/checklist-20261024-fold23-batch4-pass2.md` (evidence).

## How to verify

- Marketplace: `git fetch && git log -1 origin/master` contains this handover's commit; CI with
  `ci_wait.py --ref HEAD --timeout 3000` (bitranox:compuse-toolbox).
- Mirrors: `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` shows devops-bmk,
  coding-python-layered-config and coding-python-send-mail in sync.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
