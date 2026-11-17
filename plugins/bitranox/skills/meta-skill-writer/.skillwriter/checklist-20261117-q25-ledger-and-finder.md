# Review checklist: meta-skill-writer, old-base worktree fallback, add's anchor corpus, trailing version markers (2026-11-17)

Change covered:

- "Step 0b": a worktree whose base has no `plugins/bitranox/hooks/skill_decisions.py` runs the
  installed plugin's copy, with `--skill-dir <worktree>/plugins/bitranox/skills/<skill>` for `show`
  and `--skills-dir <worktree>/plugins/bitranox/skills` for `add`; a code block gives all three
  commands.
- The ledger step: an anchor is counted in the working-tree text of the tracked files of the skill
  directory whose ledger `add` writes (the marketplace copy, never a tool repo's twin), so a
  mirrored skill edited in its tool repo gets the same text in the marketplace copy before `add`.
- "Describe the latest release only": the finder pattern also lists a trailing version marker
  (`X.Y.Z and later`, `or later`, `and newer`, `onwards`), the history list names the
  "(X.Y.Z and later)" form, and the review sentence names a requirement on another tool
  ("needs Rust 1.80 or newer") as not history.
- New test `tests/test_release_history_finder.py`, reading the pattern out of SKILL.md.

- [x] Decisions: d-20261117-7c9e51dd, d-20261117-03681569, d-20261117-f5d6faf9

## Evidence

- [x] Step 0b ran: `show meta-skill-writer --kind rejected,removed --full` printed three rejected
      entries (narrative history file, probe hand-back from a subagent, gate refusing uncited
      declines); none is touched by this change.
- [x] Claims checked against the code (`hooks/skill_decisions.py`): `show` accepts `--skill-dir`
      and refuses a path that is not a directory; `add` accepts `--skills-dir` and skips the
      installed-copy refusal when it is given (`_skills_dir`); `_cmd_add` -> `prepare_entries` ->
      `corpus_from_dir` reads `(skill_dir / rel).read_bytes()` for each `git ls-files` path, so the
      corpus is working-tree text of tracked files in the ledger's own skill directory. An unstaged
      edited sentence counted 1 in `corpus_from_dir` for this skill.
- [x] Commands executed with the text's placeholders substituted literally (`<installed>` the
      installed 11.10.6 version directory, `<worktree>` this worktree): both `show` lines exit 0
      and list this worktree's ledger (3 and 21 lines); the `add` line wrote the three entries above
      into this worktree's ledger (rc 0); `skill_decisions.py check meta-skill-writer` reports 0
      findings. A missing script path exits 2 with "can't open file", as the text says.
- [x] Finder block executed over this skill dir with the new pattern: both passes run (10 hits
      each); over the whole skills tree the pattern adds 32 candidate lines to 539, among them a
      live history marker, "(pydantic 2.11 and later)" in coding-python-data-architecture.
- [x] Test RED/GREEN: against the old pattern 7 failed, 8 passed (every trailing form missed, the
      broken-across-a-line case missed, the grep cross-check disagreed); against the new pattern the
      skill's tests dir passes (71 passed).
- [x] RED (pre-edit Step 0b and ledger text, opus and haiku, text-only probe): both answered NONE
      for the missing-script case; opus would fast-forward the worktree, haiku guessed the installed
      copy; both called "which copy add counts anchors in" not stated and inferred it from the
      error.
- [x] GREEN (edited text, opus and haiku): both wrote the installed-copy `show` commands and the
      `--skills-dir` `add` command, and quoted "the marketplace copy, never in a tool repo's twin"
      with no staging needed for a tracked file.
- [x] Fix round after GREEN: both tiers flagged `--skill-dir` vs `--skills-dir` read as "the same
      way", haiku flagged which marketplace checkout `add` reads. The `add` command joined the code
      block with the plural flag called out, and the anchor paragraph names `--skills-dir` or the
      cwd's git top.
- [x] Final re-probe on the final text (opus and haiku, the two touched questions): both quote the
      new sentences and give the right `add` command and target directory; no new undecided gap.
- [x] Tiers: opus and haiku, three rounds (RED, GREEN, final), six cells.
- [x] Width and fence check over the added lines printed nothing; the paragraphs after each
      insertion ("Resuming a skill edit after a compaction", "Picking an anchor") bind to nothing
      new; no list count changed.
- [x] redcheck `--corpus-cascade` named topical documents (repo CLAUDE.md and memory facts on
      mirrored skills); none states the fallback or the anchor corpus (grep for `skill-dir`,
      `skills-dir`, `found 0` in each found only the edit guard's installed-copy fallback), so the
      behavioural RED stands.

## Gaps reported and declined

- The entries file schema: the field list under "Record every decision the edit makes" in this
  SKILL.md; excerpt-only.
- Re-applying the three mirror divergences when copying text into the marketplace copy: "Picking an
  anchor" in this SKILL.md says to keep anchors off those three, and the repo CLAUDE.md mirror
  section owns the regeneration procedure.
- Whether the installed copy supports `--skills-dir` and an older ledger: run above, rc 0 against
  this worktree's ledger.
- Whether `add` creates a missing ledger: `ledger_path` is documented as "it need not exist yet"
  (`skill_decisions.py` `ledger_path`); unchanged by this edit.
- Empty `show` output cannot tell a missing ledger from a wrong existing directory: pre-existing in
  both arms; a non-directory `--skill-dir` is refused (`_show_dir`), so only a wrong existing skill
  directory stays silent. Left as is.
