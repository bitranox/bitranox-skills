# skill-writer checklist - compuse-toolbox (2026-09-03, guard_replay per-tool payload)

Change: the `guard_replay` row says it replays "every real Bash command"; the tool now also reads
`--tool Write` and `--tool Edit`, and refuses a tool it cannot read. The row and its usage cell are
corrected to match. No frontmatter change.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Skill type: REFERENCE. The row is an index entry, so the test is whether it is TRUE of the
      shipped tool and whether it aids retrieval - not whether it changes a decision.
- [x] The old sentence was FALSE as of this change, which is why it is edited rather than extended:
      "every real Bash command" understates a tool that now reads three tool names, and a reader
      pricing a write-shaped guard would not learn it is possible.
- [x] Its new claims are checked against behaviour, not intent. An always-true control predicate
      over the same corpus: Bash 76649 firings, Write 3350, Edit 5521. Before the change the same
      control reported Write 0 and Edit 0 over the same 2332 files, so the control discriminates
      and the row's claim is measured rather than asserted.
- [x] The exit-code claim in the usage cell is executed, not read off the source: an unknown
      `--tool Glob` returns 2 and prints a line naming both the rejected tool and the known ones.
- [x] That refusal was a DEFECT IN THIS CHANGE first, caught by running the real invocation rather
      than the unit test: the library raise was correct while the CLI let it escape as a traceback,
      which is a worse answer than the wrong one it replaced. A test now pins exit 2 through
      `main()`, not only the library raise.
- [x] Scripts ship with tests that pass: `tests/test_guard_replay.py` goes 33 -> 40 cases, green.
      RED verified at 6 of 6 new failures before implementation (the seventh, the Bash-unchanged
      regression, passed throughout by design). `repo-gate.py --ci` green.
- [x] A control test pins the map to reality: every entry in `TOOL_PAYLOAD` must extract something
      from a fixture, so a tool listed as supported but unreadable fails the suite rather than
      documenting a capability that does not exist.
- [x] No frontmatter change; `build_skill_triggers.py --check` reports the map in sync.
- [x] Present tense, no session narrative, no machine-specific address or path added.
