# skill-writer checklist - meta-skill-writer (ledger read from a stale checkout; Decisions line end)

- [x] Change: Step 0b says show reads the ledger of the checkout it runs in (fetch, run in a
      worktree at origin's default branch); the checklist bullet says the Decisions line ends at
      the last id or reason.
- [x] Decisions: d-20261119-e3fd4158
- [x] Mechanism executed: a main checkout 249 commits behind printed 0 ledger lines where the
      origin worktree printed 2; DECISIONS_LINE_RX tested with a trailing note and a trailing
      period (both refused) and the bare id list (accepted).
- [x] Step 0b: `skill_decisions.py show meta-skill-writer --kind rejected,removed` read in this worktree at the
      origin default branch; no declined entry is re-proposed and no live rule's anchor touched.
- [x] RED as a text check: opus (effort medium) and haiku quote-backs against the pre-edit text
      answered NONE, or only a neighbouring line that does not answer, for Q9 and Q10.
- [x] GREEN quote-back on opus (effort medium) and haiku against the edited text: every quote for
      Q9 and Q10 was found verbatim in the edited text and none in the pre-edit text.
- [x] Width and fence check over the added lines printed nothing; tables canonical.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Present tense, no history lines, no private hosts, paths or personal data.
