# skill-writer checklist - process-agents-dispatching-parallel (memory rules folded in)

- [x] Change: The Pattern > ### 4. Review and Integrate (after the 'Re-run the gate YOURSELF' block,
      before 'Structured output must be harvested') - process-agents-dispatching-parallel/SKILL.md.
      RED on the pre-edit snapshot: partial. Verified: `git cherry-pick -n` applies each named
      commit to index/worktree without committing -> `LC_ALL=C man git-cherry-pick` (-n,
      --no-commit: 'applies the changes necessary to cherry-pick each named commit to your working
      tree and the index, without making any commit'). Re-applied range stops on now-empty commit ->
      same man page: 'Commits which are made empty due to a previous commit will cause the
      cherry-pick to fail' (default --empty handling). git cherry vs squash/context ->
      git-worktrees/SKILL.md Step 4 (lines ~177-196: 'git cherry and git merge-base --is-ancestor
      answer it badly: work that landed SQUASHED, rebased, or copied ... reads as unlanded';
      landed.py checks patch-equivalence OR added lines present). --continue resuming a sequencer
      range, GIT_SEQUENCE_EDITOR scripted rebase, rebase --onto: standard documented git, not
      re-run. Existing 'Run full test suite' / 'Re-run the gate YOURSELF' bullets kept; new text
      complements them (no contradiction).
- [x] Dropped as stale or unverified: Dropped all project-specific measurements (project name, sweep
      number, shas 0d35acf/158ece1, version 1.11.0, the ext3/dotenv_path specifics) and generalised
      them; dropped the memory-slug cross-link to the adopted-commit prose fact. Trap 5 (git cherry
      patch-id) carried only as a one-line pointer because git-worktrees already owns it.
- [x] Change: The Pattern > ### 4. Review and Integrate (directly after the cherry-pick paragraph
      above) - process-agents-dispatching-parallel/SKILL.md. RED on the pre-edit snapshot: partial.
      Verified: isolation: worktree gives the agent its own git worktree -> CLI 2.1.310 binary
      ('`isolation: "worktree"` gives the agent its own git worktree (auto-cleaned if unchanged)'),
      so `git worktree list` finds the surviving ones. 'Resumed agent continues only after the
      reset' -> consistent with a rate limit; kept as stated by the body (skeptic: UNVERIFIED but
      consistent). Ticking checklist wording reconciled with the existing step-4 bullet 'Tick each
      dispatched name ... ONLY when its hand-back has been READ'. Commands are plain git.
- [x] Dropped as stale or unverified: Dropped the historical incident (project, version, four-of-six
      count, internal census test name) and the memory-slug link to the merge fact, replaced by
      'land it by cherry-pick as above' pointing at the folded paragraph in the same section. Did
      not carry a claim about where the worktree directory is named/located (not verified beyond
      'own git worktree').
- [x] Review B S6 fixed: the history-only backup is taken immediately before the squash or rebase; a
      separate `-f` pre-pick branch is the rollback point for the picks (delta reviews 2 and 3).
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      every scenario again after the first review's fixes, then the scenarios each later fix
      touched. Every answer was a quote from the new text on both tiers in every round; no NONE.
      Quotes were checked against the files (6-word windows; misses traced to line wraps,
      markup and line-number prefixes).
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps not listed
      here asked for detail the rule does not need (out of scope) or were answered elsewhere in
      the skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history finder clean on the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns except where the file keeps one line per paragraph or list item.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
