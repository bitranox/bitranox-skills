# Handover 2026-10-23: [28] C+D shipped (9.16.0); solved backlog lines deleted (10.0.0); [23] batch 4 awaits the user

## In flight

- Nothing running. The [23] batch 4 check (workflow wf_2307b67e-dbd, 10 agents, read-only) has
  finished, and its merged result is on disk in `.plan/fold-23/batch4/merged.json` (gitignored).
  It has NOT been put to the user yet: that is the next action.
- No worktree of this session is left; `feat/jev-sites-c-d` is merged and deleted.

## Committed, or not

- Pushed this session: 48931d97 (9.16.0, Jev shadow sites `backlog_ask` and `audit_candidate`, CI
  green) and 8efd0b24 (10.0.0, solved backlog lines deleted). Installed copies need
  `/plugin marketplace update bitranox-skills` + `/reload-plugins` for 10.0.0. Both knobs read `shadow` on this machine (`settings.py view`), and 9.16.0 is
  installed here; live `backlog_ask` rows are already in the shadow log.
- This commit (10.0.0): `backlog_close` / `open_work.close_item` DELETE a solved line and return
  `{rank, line, reason, deleted}`, the new-file header and meta-context-watcher say so (user:
  "always delete solved lines in open-work.md", then "also fix open_work.close_item ... including
  in the new backlog file's header template"); `OPEN-WORK.md` lost its 113 closed lines and its
  header rule changed; [23] batch 4 result and new [700] recorded. Git history keeps every deleted
  line. MAJOR because the tool now deletes a line it used to keep.
- Memory: new tree-top fact `feedback-delete-solved-open-work-lines-everywhere` (the same rule for
  every backlog); the older soundtouch-zonemaster-only fact it generalises can go in the next dream.
- Gitignored, clone-local: `EXECUTION-USER-REVIEW.md` (the user's "C and D" answer, the
  autonomous C/D shape decisions), `.plan/fold-23/batch4/` (inputs, roster, mirrors map,
  merged.json).

## Decided, and why - do not reopen

- [28] C and D are shadow only, no decide mode. C asks on EVERY typed prompt (the pattern both
  misses paraphrases and fires on bare replies, so only asking every prompt measures both). D sends
  a 3000-character excerpt REDACTED BEFORE IT IS CUT (a review found a key whose BEGIN line fell
  outside the window would leak), and the eval keys a candidate by its transcript record `uuid`
  (the audit window slides between a compaction and the session end). Detail in
  EXECUTION-USER-REVIEW.md.
- [23] batch 4 is the nine tool-repo levels that ship their own plugin skill (plan order: after the
  bitranox-skills/KI levels come the tool repos). The 34 pointers added there after phase 1 were
  classified first, then every fold candidate got the reach and skeptic lenses of batch 3.

- Solved OPEN-WORK lines are deleted, never kept as `- [x]` (user, 2026-10-23), and the plugin's
  close verb does the same for every user (10.0.0). A file whose own header keeps closed lines
  still governs itself and is closed by hand.

## Decided against, and why

- No deterministic noise filter for the audit candidates was built: the user chose the Jev shadow;
  whether a filter would do it cheaper is unverified and recorded in [28].
- The site tests' "nothing sent" checks keep a fixed 1 s wait, as the existing jig_repetition
  test does: absence cannot be awaited.

## Still open, untouched

- [23] the batch 4 decision (below); [710] a suspected false positive in
  block-write-after-sibling-cd (unverified); [28] waits for 100 rows per site from 3 sessions; [96] blocked
  on data; [700] two memory-fact rewrites wait for the user; the FOUND items: `OPEN-WORK.md`.
- A memory consolidation (tree dream) is due per the SessionStart nudge; it would also add a
  dream-placement run for [96].

## Lessons for the next nap

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
- Carried from earlier handovers (not yet napped):
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

[23] is the top-ranked open item. Put batch 4 to the user with one AskUserQuestion, built from
`.plan/fold-23/batch4/merged.json` (recount first; recorded: 47 candidates - reach OK 18, PARTIAL
27, FAILS 2; skeptic FOLD-AMENDED 34, AS-HINTED 7, ALREADY 6; 13 rows target mirrored skills, so
folding them means pushing those tool repos too, and 2 target lsdsk's own plugin). Batches 2 and 3
folded the REACH-OK rows first and the PARTIAL ones with a kept pointer later; offer that, and ask
separately whether the six tool repos may be pushed this round (pushes to tool repos need this
conversation's own approval). Read the 5 rows whose body has a CONTRADICTED claim before quoting
any of them.

## Files that matter

- `.plan/fold-23/batch4/merged.json` - per slug: `input`, `classify` (new rows), `reach`, `skeptic`.
- `.plan/fold-23/batch4/{o1,o2,n1,n2,roster,mirrors}.json` - the inputs the agents read.
- `~/.claude/plans/curried-mapping-dolphin.md` - the [23] plan (Phase 2 steps are the fold loop).
- `plugins/bitranox/hooks/recall-memory.py` (`_shadow_backlog_ask`),
  `plugins/bitranox/hooks/self-improve-audit.py` (`shadow_excerpt`, `_shadow`),
  `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` (`_audit_entries`).
- `OPEN-WORK.md` lines [23], [28], [96], [700].

## How to verify

- `git status --porcelain` in the repo: empty after this commit except gitignored files.
- 9.16.0 on origin: `git merge-base --is-ancestor 48931d97 origin/master`.
- CI for the commit carrying this file: `ci_wait.py --ref HEAD --timeout 2700`
  (bitranox:compuse-toolbox).
- Shadow sites live: `python3 plugins/bitranox/skills/meta-memory-settings/settings.py view`
  shows both new knobs at `shadow`; `classifier_eval.py report` shows `backlog_ask` rows.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
