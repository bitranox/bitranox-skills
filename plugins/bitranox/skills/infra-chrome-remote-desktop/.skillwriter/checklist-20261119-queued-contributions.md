# skill-writer checklist - infra-chrome-remote-desktop (slow first start after the bus fix)

- [x] Change: the fix's keyring-prompt cost and its two ways out; a subsection timing a real page
      load with an interleaved --password-store=basic control arm; rtkit and no-DISPLAY causes;
      net-log and dbus-monitor instruments; the 25 s symptom row points at the subsection.
- [x] Decisions: d-20261119-f16a4b7c
- [x] Mechanism executed: the shipped timing loop, extracted from the file and run against a local
      http page: default 25387 and 25230 ms, basic 467 and 243 ms; a data: URL 0.3 to 0.8 s in
      both arms; google-chrome wrapper read (no flags file); login.keyring header read.
- [x] GREEN gap closed: the control arm was not called one (now named in the sentence).
- [x] Declined gaps: a healthy busctl answer and a pass threshold (host-specific).
- [x] Step 0b: `skill_decisions.py show infra-chrome-remote-desktop --kind rejected,removed` read in this worktree at the
      origin default branch; no declined entry is re-proposed and no live rule's anchor touched.
- [x] RED as a text check: opus (effort medium) and haiku quote-backs against the pre-edit text
      answered NONE, or only a neighbouring line that does not answer, for Q11, Q12 and Q13.
- [x] GREEN quote-back on opus (effort medium) and haiku against the edited text: every quote for
      Q11, Q12 and Q13 was found verbatim in the edited text and none in the pre-edit text.
- [x] Width and fence check over the added lines printed nothing; tables canonical.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Present tense, no history lines, no private hosts, paths or personal data.
