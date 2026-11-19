# skill-writer checklist - coding-data-architecture (blame --contents and duplicate scope)

- [x] Change: STEP A SCOPE uses `git blame --contents <file> <base>..HEAD -- <file>` and counts a
      new duplicate of a pre-base rule in scope with its old twin.
- [x] Decisions: d-20261119-c2f71e55
- [x] Mechanism executed: scratch repo, git 2.53.0: an uncommitted top insert shifts the plain
      blame's numbering; --contents numbers the working tree, new line `00000000`, base lines `^`.
- [x] Step 0b: `skill_decisions.py show coding-data-architecture --kind rejected,removed` read in this worktree at the
      origin default branch; no declined entry is re-proposed and no live rule's anchor touched.
- [x] RED as a text check: opus (effort medium) and haiku quote-backs against the pre-edit text
      answered NONE, or only a neighbouring line that does not answer, for Q7 and Q8.
- [x] GREEN quote-back on opus (effort medium) and haiku against the edited text: every quote for
      Q7 and Q8 was found verbatim in the edited text and none in the pre-edit text.
- [x] Width and fence check over the added lines printed nothing; tables canonical.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Present tense, no history lines, no private hosts, paths or personal data.
