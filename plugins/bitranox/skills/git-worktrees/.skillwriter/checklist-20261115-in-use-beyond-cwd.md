# skill-writer checklist - git-worktrees (2026-11-15, an in-use check beyond the cwd test)

Step 5 now says a clean `/proc` cwd check does not mean nobody is working in a worktree: an agent
session edits by absolute path from its launch directory. Before removing a dirty worktree or
calling one stale, read its dirty files' mtimes and search the session transcripts for its path; a
recent dirty file with no transcript naming the session goes to the user; a behind count or
last-commit date says nothing about uncommitted files. The cwd grep takes the resolved path, and
its `none = clear` comment now reads `none = no process there`.

Decisions: d-20261115-bdcc7ef3

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing; the two live rules are about
      ignored work files and the ExitWorktree count, neither touched.
- [x] Mechanism measured on this repo: the skill's cwd check, run from the main checkout, returned
      0 hits for a worktree a live session was editing (that session's claude process had the main
      checkout as cwd). Positive control: a process with its cwd in the worktree returned 1 hit.
      Symlink: a process that entered a directory through a symlink matched the grep 0 times by the
      link path and 1 time by `realpath`.
- [x] RED. Context check: a tree-top memory fact already says a session's cwd is where it was
      launched, so a behavioural RED is contaminated. Route taken: a text check of the pre-edit
      skill (0 hits for transcript, mtime, `.claude/projects`; the one "absolute paths" hit is
      about briefing a subagent), plus quote-back probes on the pre-edit excerpt: opus and haiku
      both answered NONE to "how to detect a live session editing from another cwd" and to
      "does a behind count or commit date say anything about uncommitted files". Both reasoned
      their way to "do not discard" from inherited context, not from the text.
- [x] Every added command executed: the mtime command listed a dirty file and kept the caller's
      cwd (subshell); on a scratch repo with a modified, a deleted and an untracked file it printed
      two dated lines and a `cannot statx` error for the deleted file; the transcript search listed
      the live transcripts of the editing session.
- [x] GREEN, edited excerpt pasted, opus and haiku (one scenario, four questions): both quoted the
      new detection and behind-count lines verbatim and refused to discard a worktree with a
      40-minute-old dirty file.
- [x] Gaps closed after GREEN: the old `# Linux; none = clear` comment contradicted the new
      paragraph (now `none = no process there`); the cwd grep missed a symlinked path (resolved
      path stated); whether an empty transcript search clears a recent dirty file (it does not;
      ask the user); `2>/dev/null` made a failed `stat` read as "no dirty files" (removed, and the
      comment says a deleted file prints an error); "ask the user" was narrowed to a recent dirty
      file so an old worktree is not forced into a question.
- [x] Re-run on the final text, opus and haiku, five scenarios (symlinked path, clean cwd check
      alone, recent file with empty transcripts, over-trigger control with five-week-old files,
      the `statx` error line): 10 of 10 cells answered with the governing quote; the control went
      on to landed.py on both tiers without forcing a question. No new undecided gap.
- [x] Gaps declined: landed.py's path, arguments and exit codes, and how to "save what it names"
      (covered in Step 4: SKILL.md lines 261, 293, 297); "the last hours" as a number, how old a
      deleted file is, and asking a session to stop versus asking whether it still works
      (judgement calls left to the reader); how to reach a session once its transcript is found
      (outside this skill); searching both spellings of a symlinked path, and sessions under
      another config dir or HOME (covered by "An empty transcript search does not clear a recent
      dirty file"); other users' processes hidden from `/proc` without root (an agent session
      editing the user's worktree runs as that user); `grep -E` treating `.` as any character
      (false positives only, the safe direction); a macOS form of the mtime command (no macOS
      host to verify one on, and the error is no longer hidden, so a failure there is loud).
- [x] Width and fence check over the added lines printed nothing. ASCII only.
