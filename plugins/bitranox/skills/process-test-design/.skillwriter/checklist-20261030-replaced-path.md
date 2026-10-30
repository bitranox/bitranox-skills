# skill-writer checklist - process-test-design (a test that replaces PATH)

- [x] Change: SKILL.md - a new paragraph after the PATH stand-in paragraph: a test that REPLACES
      `PATH` with the stub dir must still provide every other command the script calls, or the
      script dies with exit 127 before the branch under test and the RED is an artifact; prepend
      when only adding a stub; when a program must be absent, symlink the other commands in
      (resolved with `command -v` before PATH is replaced, `bash` for an env shebang, builtins
      need none) and leave the absent one out; read the RED's error line before believing it.
- [x] Receipt held (skill_receipt.py start meta-skill-writer); the edit was made by the agent
      that loaded the skill.
- [x] redcheck --corpus-cascade: one hit on ordinary words (date, stub, temp, valid); the named
      document does not state the lesson. RED run as a text check anyway.
- [x] RED (opus quote-back on the pre-edit file): the replaced-PATH case NONE; whether an exit-127
      RED counts PARTIAL (only the general "the failing line is the assertion" rules).
- [x] GREEN round 1 (opus and haiku, 2 cells): all three questions quoted. Gaps: how to find the
      real binaries, the shebang interpreter, builtins. Closed in the same paragraph.
- [x] Round 2 (haiku): all quoted. Gaps: how a program is made absent, which program the
      shebang needs, how to list the commands. Closed: leave it out of the dir, `bash` (env is
      called by absolute path), list them by reading the script.
- [x] Round 3 (haiku): all three quoted. Gap closed: assert the absent program really is absent
      (`command -v <absent program>` fails under the new PATH). Declined: `test`/`[` builtins
      (the `echo`/`printf` examples carry the rule); `command -v` returning an alias (a test
      runner's non-interactive shell loads none).
- [x] Round 4 (haiku) on the final text: quoted "Assert that `command -v <absent program>` fails
      under the new `PATH` before relying on it." No new undecided gap.
- [x] Declined: a bats equivalent of the pytest `-rs` check - outside this change, the checklist
      line it sits in predates it; detecting a forgotten command before any run - the exit 127
      is the stated signal, and a pre-run audit is a tool, not a rule.
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion point (the self-relaunching argv rule) does not refer back to it.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense; the latest-release finder found no history line.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
