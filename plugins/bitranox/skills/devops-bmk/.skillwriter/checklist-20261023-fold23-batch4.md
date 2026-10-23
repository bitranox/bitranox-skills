# skill-writer checklist - devops-bmk (fold of memory rules into the skill)

- [x] Change: 4. Output format: JSON by default (new paragraph after the Precedence line); plus
      reconciling edits in section 1 (Install, line 51) and the Troubleshooting row '`make` keeps
      using an old bmk right after a release'. Verified against ground truth: JSON auto-accepts,
      text+non-tty declines with stderr 'run 'bmk install' to update it' and returns, text+tty
      click.confirm default=False -> bmk src/bmk/adapters/cli/commands/install_cmd.py:93-109
      (auto_accept = read_tool_output_format() is not TEXT); _stdin_is_a_terminal =
      sys.stdin.isatty() -> install_cmd.py:61-63; check runs for every subcommand except install,
      and a decline/OSError never blocks the command -> src/bmk/adapters/cli/root.py:112-123; check
      reads only BMK_OUTPUT_FORMAT env -> src/bmk/adapters/stagerunner/output_format_env.py:18-27,
      while --human is only a subcommand option (testsuite_cmd.py:64,88;
      test_integration_cmd.py:51,73,93; testall_cmd.py:38) and make test-human runs `bm
- [x] Change: 3. Everyday commands - '`release` does not bump; `push` always commits.' bullet list
      (first bullet amended, new second bullet; the following 'When that version is committed...'
      sentence became its own bullet). Verified against ground truth: release prints '[release]
      Pushing branch {branch} to {remote}' then pushes the branch before creating/pushing the tag ->
      bmk src/bmk/adapters/stagerunner/helpers/_release.py:227-240; branch is the current checkout's
      `git rev-parse --abbrev-ref HEAD` -> _release.py:55-58; push is a plain `git push <remote>
      <branch>` -> _release.py:72-74, so it applies to any non-default checkout (not only a
      worktree) and an earlier fast-forward of the default branch does not change which branch is
      pushed. bmk source at 3.23.2.
- [x] Added after review: the Makefile check acts on any version difference (a newer Makefile is
      rewritten back; the remedy is the next `make`, not `bmk install`); the regeneration line is
      qualified for text mode without a terminal; a dangling antecedent is fixed; every
      version-history marker is rewritten in the present tense (no 'from bmk X.Y.Z', 'Before', 'no
      longer', 'as before').
- [x] Claims the source contradicts were dropped or corrected; machine-local figures, private names
      and incident history were not carried over.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against the pre-edit snapshot (partial for scenario 1;
      partial for scenario 2). Only a verbatim quote from the snapshot counts, so context inherited
      from this machine cannot satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files, in four rounds: after the edit,
      after the first review's fixes, after the delta review's fixes, and a final round on the
      questions the last fixes touched. Every scenario was answered with a quote from the new text
      on both tiers in every round; no NONE.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or recorded below.
- [x] Gaps closed or declined: closed - downgrade case and its remedy, the text-mode regeneration
      qualifier, the antecedent (re-tested by quote-back); declined - a command to find the hung bmk
      process (generic process inspection), which answer to give the prompt (either unblocks; JSON
      mode is the stated unattended route), a leaked branch at a different commit (it carries real
      work, left to the user), reaching a default-branch checkout while another checkout holds it
      (git-worktrees mechanics).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, repo file paths or reserved examples.
