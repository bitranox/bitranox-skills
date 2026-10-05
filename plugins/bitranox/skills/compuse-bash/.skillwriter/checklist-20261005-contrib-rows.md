# skill-writer checklist - compuse-bash (2026-10-05, contrib rows C4/C18)

Two new quick-reference rows: a heredoc nested inside another heredoc reusing the same delimiter,
and arming a waiter on a log a previous run already wrote.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Test approach: retrieval - two questions, each answered
      with a direct quote or NONE.
- [x] RED (pre-change text, pasted): "What happens if an inner heredoc inside a running script
      reuses the outer heredoc's delimiter?" - NONE (the existing row only covers an UNQUOTED
      delimiter, a different failure mode). "Does polling a log for a terminal line prove THIS
      run finished?" - NONE (the existing "Waiting for an event" row sets a ceiling but says
      nothing about a log armed on a stale prior run).
- [x] Reproduced the heredoc claim directly: a script with `cat << 'OUTER' ... cat << 'OUTER' ...
      OUTER ... OUTER` closed the OUTER heredoc at the FIRST reused delimiter, printed the
      remaining line as output, then failed with `OUTER: command not found` when the shell tried
      to run the leftover delimiter as a command - matching the row's description exactly.
- [x] GREEN (new rows pasted): both questions now answer with a direct quote ("ends the OUTER
      heredoc early", "fires AT ONCE if that line is already sitting in the log").
- [x] GREEN diffed against RED in both directions: nothing removed, two gaps closed.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
