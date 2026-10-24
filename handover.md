# Handover 2026-10-24: [700], [720] and [23] batch 4 pass 1 shipped; pass 2 next

## In flight

- Nothing running. No subagent, workflow or background shell of this session is live; every CI
  wait it started has finished green.
- Worktrees: the fold worktrees (`.claude/worktrees/fold-23-batch4`, `../bitranox-skills-wt-ow23`,
  `apps/utils/lsdsk-wt-fold23`) are removed with their branches.

## Committed, or not

- Everything of this session is committed AND pushed:
  - marketplace 10.0.5 (send-mail `inline_images` present tense; [700], [720] closed) and the
    [23] backlog line;
  - btx_lib_mail 4.5.2 (twin edit plus a filelock pin), lsdsk 1.15.3 (the batch 4 skill note);
  - memory store: the two [700] rewrites (`d4f4423`) and the 18-pointer archive plus 4 re-pointed
    facts (`1fdd0a5`).
- Not released to PyPI, by design: btx_lib_mail 4.5.1/4.5.2 and lsdsk 1.15.3 are skill-text and
  dev-pin changes only. The btx_lib_mail session has since pushed its own 4.6.0 work on top.
- Uncommitted: this file (it goes into the commit that carries it). Gitignored and local:
  `EXECUTION-USER-REVIEW.md`, `.plan/fold-23/batch4/` (merged.json, fold inputs, journals).

## Decided, and why - do not reopen

- [700]: the user chose "Keep and commit (Recommended)" for the two fact rewrites a bmk session
  had applied on an ambiguous "yes" (verbatim in USER-DECISIONS.jsonl).
- btx_lib_mail's filelock floor is `filelock>=4.2.1; python_version >= '3.11'`: 4.2.1 needs 3.11,
  and an unmarked floor makes bmk lower it to 4.1.0 to keep 3.10 installable (bmk and datamax-dpl
  use the same marker form). 3.10 keeps 4.1.x with the CVEs, no fix exists for it.
- `--check-tree` TOTAL 4 was accepted for the archive: all four are pre-existing sideways refs in
  other facts, filed as [730] for the tree dream.

## Decided against, and why

- No behavioural subagent arm for [720]'s one-line edit: it removes a version qualifier and adds
  no instruction; the latest-release finder (RED one hit per twin, GREEN zero) is the evidence,
  recorded in the skill's `.skillwriter/checklist-20261024-latest-release-inline-images.md`.

## Still open, untouched

- [23] pass 2 (top rank), [730], [740], and every other line: `OPEN-WORK.md`.
- A tree dream (memory consolidation) is due per the SessionStart nudge; [730] is its input.

## Lessons for the next nap

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
- Carried from earlier handovers (not yet napped):
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

[23] is the top-ranked open item. Start pass 2:

1. Recount from `.plan/fold-23/batch4/merged.json`: the REACH-PARTIAL rows (27 recorded) and the
   REACH-FAILS rows (2 recorded), with their owner skills, excluding the 18 slugs in
   `.plan/fold-23/batch4/fold/slugs18.txt` (archived).
2. Invoke `bitranox:meta-skill-writer` and run the pass 1 method on them: RED quote-back on the
   pre-edit skill, fold, GREEN quote-back on haiku and opus, fix-delta reviews; a REACH-PARTIAL
   row keeps a shortened pointer. Ask the user for each tool repo's push before pushing it.

## Files that matter

- `OPEN-WORK.md` lines [23], [730], [740].
- `.plan/fold-23/batch4/merged.json` (reach and skeptic verdict per slug), `.plan/fold-23/batch4/fold/`
  (g1..g6 inputs, journals, `slugs18.txt`, `refmap18.json`).
- `plugins/bitranox/skills/*/.skillwriter/checklist-20261023-fold23-batch4.md` (pass 1 evidence).

## How to verify

- marketplace: `git -C <repo> fetch && git -C <repo> log -1 origin/master` contains the handover
  commit; CI via `ci_wait.py --ref HEAD --timeout 2700` (bitranox:compuse-toolbox).
- memory store: `reconcile_memory_index.py --check-tree <tree anchor>` reports TOTAL 4,
  exactly the [730] refs.
- none of the 18 archived slugs has a pointer: `grep -rl -F -f .plan/fold-23/batch4/fold/slugs18.txt`
  over the tree's `CLAUDE.local.md` files (found with find, they are gitignored) prints nothing.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
