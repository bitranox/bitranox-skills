# skill-writer checklist - git-worktrees (memory rules folded in)

- [x] Change: Step 1: Create Isolated Workspace > 1a. Native Worktree Tools (after the 'Native tools
      handle directory placement' paragraph); Red Flags > Never (amended #1 line) -
      git-worktrees/SKILL.md. RED on the pre-edit snapshot: partial. Verified: fresh default =
      origin/<default-branch>, head = local HEAD, applies to --worktree, EnterWorktree and agent
      isolation -> CLI binary ~/.local/share/claude/versions/2.1.310 settings schema:
      baseRef:B(["fresh","head"]).describe("Which ref new worktrees branch from. 'fresh' (default)
      branches from origin/<default-branch> ... 'head' branches from your current local HEAD so
      unpushed commits ... are present. Applies to --worktree, EnterWorktree, and agent isolation.")
      (this also settles the skeptic's UNVERIFIED subagent claim: CONFIRMED). Setting name/value ->
      binary message 'To start worktrees from your current HEAD instead, set worktree.baseRef to
      "head" in Claude Code settings.' EnterWorktree path restriction -> binary: 'In both cases the
      target must be a worktree under `.claude/worktrees/` of the same repository'
      (already-in-worktree and pinned-agent cases) plus a safetyCheck permission decision 'a
      model-supplied worktree outside .claude/worktrees/' (classifierApprovable false) -> hence
      'asks for permission or is refused'. Agent cwd mutually exclusive with isolation -> binary:
      'Absolute path to run the agent in ... Mutually exclusive with isolation: "worktree".'
- [x] Dropped as stale or unverified: Nothing contradicted. Not carried: the body's historical
      incident (project name, ADR date). Reworded the body's 'cherry-pick onto main' to 'onto your
      branch' and gave the why (its tests ran on a different base) rather than claiming a merge
      would lose local state, which git does not do. Reconciled the Red Flags #1 line with the new
      exception in the same edit.
- [x] Change: Step 5: Finishing - Reclaim the Per-Topic Build Cache (wtclean), before the wtclean.py
      commands; plus a Red Flags > Never line - git-worktrees/SKILL.md. RED on the pre-edit
      snapshot: partial. Verified: Probe in my own scratch dir (git 2.53.0): background subshell
      cd'd into a linked worktree, `git worktree remove` from the main repo SUCCEEDED while it ran,
      then `LC_ALL=C git status` printed 'fatal: Unable to read current working directory: No such
      file or directory', rc=128; `python3 -c 'import os; os.getcwd()'` raised FileNotFoundError,
      rc=1. wtclean.py has no process check (grep for proc/lsof/fuser/running: none); its own
      docstring lines ~478 and ~520 state Windows locks a process's current directory. The /proc
      check verified: a background `sleep` cd'd into a dir was found (1 line). lsof present at
      /usr/bin/lsof.
- [x] Dropped as stale or unverified: Nothing stale. Generalised the body's named toolbox jig to 'a
      background CI waiter'.
- [x] Review B S2-S5 fixed: baseRef is the nested {"worktree": {"baseRef": "head"}} key in the
      repository's .claude/settings.local.json (Claude Code settings docs), fresh's local-HEAD
      fallback named; Agent cwd only where the tool offers it, absolute, with a fallback; the
      CI-waiter claim scoped to waiters that resolve the repo per poll (ci_wait resolves once); the
      /proc cwd check run from outside the worktree with an anchored pattern; Step 1a's skip
      sentence points at the exception.
- [x] Declined: long lines in the Red Flags list match its one-line-per-item style.
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
