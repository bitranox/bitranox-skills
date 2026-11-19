# skill-writer checklist - compuse-bash (tail -F over several logs; grep -c in a chain)

- [x] Change: quick-reference row "Capturing a `grep -c` count" gains the && chain case; new row
      "`tail -F A B | grep PATTERN` (one watch over SEVERAL logs)" (headers reach grep; -q;
      pattern from the producer's exact line).
- [x] Decisions: d-20261119-65d85687, d-20261119-92836e60
- [x] Mechanism executed: tail -n 1 over two files piped to grep -c counted 2 header lines, 0 with
      -q; `grep -c zzz f && echo ran` printed 0, exit 1, no `ran`.
- [x] Step 0b: `skill_decisions.py show compuse-bash --kind rejected,removed` read in this worktree at the
      origin default branch; no declined entry is re-proposed and no live rule's anchor touched.
- [x] RED as a text check: opus (effort medium) and haiku quote-backs against the pre-edit text
      answered NONE, or only a neighbouring line that does not answer, for Q1 and Q2.
- [x] GREEN quote-back on opus (effort medium) and haiku against the edited text: every quote for
      Q1 and Q2 was found verbatim in the edited text and none in the pre-edit text.
- [x] Width and fence check over the added lines printed nothing; tables canonical.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Present tense, no history lines, no private hosts, paths or personal data.
