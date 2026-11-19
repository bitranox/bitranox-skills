# skill-writer checklist - compuse-ssh (ConnectTimeout below the outer bound)

- [x] Change: the scripted-ssh row says ConnectTimeout goes below the outer bound when code tells
      a hung call from an unreachable host.
- [x] Decisions: d-20261119-237c6f68
- [x] Mechanism executed: an unroutable address under `timeout 4`: rc 124 without ConnectTimeout,
      rc 255 `Connection timed out` with ConnectTimeout=2.
- [x] Step 0b: `skill_decisions.py show compuse-ssh --kind rejected,removed` read in this worktree at the
      origin default branch; no declined entry is re-proposed and no live rule's anchor touched.
- [x] RED as a text check: opus (effort medium) and haiku quote-backs against the pre-edit text
      answered NONE, or only a neighbouring line that does not answer, for Q3.
- [x] GREEN quote-back on opus (effort medium) and haiku against the edited text: every quote for
      Q3 was found verbatim in the edited text and none in the pre-edit text.
- [x] Width and fence check over the added lines printed nothing; tables canonical.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Present tense, no history lines, no private hosts, paths or personal data.
