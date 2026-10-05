# checklist-20261005-prev-copy-stale-commit-closing-rank

Changes under test, four rules in `SKILL.md`:

1. A free rank is free over EVERY line of `OPEN-WORK.md`, closed `[x]` lines included (the
   SessionStart listing shows open items only, so a closed item's number looks free).
2. The `[x]`-and-keep closing rule is a default: a backlog file's own header that states another
   rule governs that file, and before deleting a line the file's tracking is checked, because a
   deleted line in an untracked backlog is unrecoverable.
3. A new procedure step 3: copy the outgoing `handover.md` to `handover.prev.md` before the
   overwrite unless git already holds it exactly (tracked AND unmodified), keep the copy out of
   commits, and diff the new file against the earlier text afterwards. Later steps renumbered,
   and the one internal step reference moved with them.
4. The STALE marker a reader adds is a working-tree edit: never a standalone commit, carried by
   the next commit the user asks for where the file is tracked, and named in the reply.

Plus one sentence under "When it fires on its own": the Stop hook's overwrite warning asks git
whether `handover.md` is tracked rather than asserting it.

## PLAN

- [x] Skill type: discipline (filing and overwrite rules followed at the end of a long session).
- [x] Scope: `SKILL.md` only; the companion hook changes (Stop-hook wording, SessionStart
      shared-rank line) ship as code with their own tests.

## RED

- [x] Inherited-coverage check: `redcheck.py --corpus-cascade` on the repo answered INHERITED
      COVERAGE for the closing-rule and rank scenarios (the tree-top CLAUDE.local.md and memory
      store carry related text) and clean (NOT CAUGHT) for the copy-aside and STALE-commit ones.
      One route for all four: a TEXT CHECK of the artifact, with a behavioural arm for gaps.
- [x] Text-check RED: the pre-change file has no `handover.prev` (the only `prev` hit is the word
      "prevent"), no sentence on committing the STALE line, no "header" at all, and the only rank
      sentence near "closed" is the closing rule itself.

## GREEN

- [x] Text-check GREEN: each rule is present once (grep "free over EVERY line", "header governs
      that file", "handover.prev.md", "working-tree edit and stays one").
- [x] Behavioural arm on haiku with the edited sections pasted, five scenarios, every answer with
      a direct quote of the new text and none answered NONE: rank 50 (not 40) beside a closed
      `[40]`; a gitignored backlog whose header says DELETE - checked tracking, deleted, named the
      deletion; a gitignored handover - copied, overwrote, diffed; a tracked unmodified handover -
      no copy; a STALE mark in auto mode - no commit, the reply names the uncommitted line.
- [x] The arm was asked for a `Skill gaps` section; its list is worked below.

## REFACTOR - every gap closed or declined

- [x] GAP: what "ranked last" means numerically. DECLINED - the scenario's wording; "Rank in
      TENS" plus "free over EVERY line" already gave the right number.
- [x] GAP: what to do when the tracking check is ambiguous. DECLINED - `git ls-files
      --error-unmatch` has a binary exit code; the rule names it.
- [x] GAP: the format of "account for every item that vanished". DECLINED - step 2 already says
      where such items go (a line in `OPEN-WORK.md` or a `[x]` with a reason).
- [x] GAP: whether to fetch before the tracking check. DECLINED - the check is about the local
      file being overwritten, not about upstream.
- [x] GAP: the exact STALE text. DECLINED - step 5's expiry instruction gives it verbatim; the
      probe excerpt quoted it.
- [x] GREEN against the pre-change behaviour: reconcile-first, the wholesale overwrite, the
      `/clear` nudge and the ranking order are unchanged; the copy-aside is an added step before
      the overwrite, not a replacement for reconciling.

## Quality

- [x] Description unchanged, so the trigger map needs no rebuild.
- [x] Step renumbering checked: no hook, test or other skill cites a step number of this skill.
- [x] No narrative, no scratch paths, no addresses added; added lines wrapped at 100 columns.

## Deployment

- [x] No version bump or CHANGELOG entry in this branch: the integration owner bumps and writes
      the release notes for the whole batch.
