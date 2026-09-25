# skill-writer checklist - meta-audit-local-skills-and-hooks (false-clean paths closed)

Change: Step 2 names two new check ids (`settings-unparseable`, `unlistable`) and states `check`'s
exit codes, including the refusal (exit 2) of a `--root`, `--home` or `--shipped` that is not a
directory.

- [x] RED is a measurement: a truncated settings.json, a typo in `--root`, `--home` or
      `--shipped`, and a chmod 000 subtree each made `check` print "clean" and exit 0 before the
      fix; a `settings.json` holding `[]` and an undecodable SKILL.md each crashed with exit 1,
      the code that means "findings".
- [x] GREEN: each case is pinned by a test in `tests/test_audit_local.py` that runs the real
      `cmd_check` / `main()` and asserts the exit code and the check id the SKILL.md now names.
- [x] The controls stay green: the same settings file with its brace restored reports the
      `registration` finding, a well-formed file without hooks is clean, and an existing
      `--shipped` dir still drives the duplicate checks.
- [x] The documented invocation is unchanged; only its outcomes are stated more completely.
- [x] Present tense, no session narrative, no machine paths added.
- [x] Frontmatter untouched: no `name` or `description` change.
