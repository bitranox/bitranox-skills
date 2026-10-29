# skill-writer checklist - meta-dream-tree (session-review answers by exit status)

- [x] Change: `dream_state.py session-review` exits 0 while it shows a transcript part, 1 once
      NOTHING NEW is left of that transcript (including the case where only the subagent, routing
      or skills blocks remain, which printed `(none - already consumed)` and exited 0), 2 on an
      error, including no transcript discovered (message on stderr). `references/dream-core.md`
      "A stretch over 2 MB" loops on that status and says why a marker search cannot work.
- [x] Code TDD: four new or changed tests failed on the pre-change script (exit 1 on nothing new,
      exit 1 with only routing evidence left, a three-part loop whose every line quotes the marker
      ending on the status after exactly three rounds, exit 2 on discovery failure), then passed.
      `meta-dream-tree/tests` plus `hooks/tests` with the CI dependency set: 7824 passed, 6
      skipped, 1 xfailed.
- [x] Corpus check: this machine's memory store holds a fact prescribing a `head -12` banner
      window for this loop, so a dispatched probe inherits it. Recorded, not escaped: the RED
      arms below show it, and the new text names that window as a failing form.
- [x] RED (pre-edit paragraph pasted, text-only probe agent, opus and haiku): haiku stopped on
      `grep -q 'NOTHING NEW'` over the whole review file; opus stopped on that marker inside
      `head -n 15`, the window that ends inside the transcript when the banner is shorter. Both
      treated any non-zero session-review status as an abort.
- [x] GREEN (edited paragraph pasted, same scenario, opus and haiku): both looped on the exit
      status, stopped on 1, aborted on 2, never searched the output, and quoted
      "rc 1: NOTHING NEW is left of this transcript - the done answer, not a failure" and
      "Decide by that status, never by searching the output for a marker." 2 tiers, 4 cells.
- [x] Skill gaps from GREEN, declined with reasons: the launch path of `dream_state.py` (covered in
      the same file, "Script homes", outside the pasted excerpt); bytes appended to the transcript
      while the loop runs (the next review shows them as a new stretch, by design); one file per
      part rather than one `review.txt` (the text says to read each part before repeating, so an
      overwrite loses nothing that was read); `session-reviewed` after exit 1 (the text says stop).
- [x] RED vs GREEN diffed both ways: no baseline result lost; both GREEN arms kept the per-part
      `session-reviewed` exit-2 check the RED arms had.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, every fence closes, prose wrapped to the file's width; the
      history-phrase finder found nothing in the added lines.
- [x] Security scan: no secrets, hostnames, private paths or PII.
