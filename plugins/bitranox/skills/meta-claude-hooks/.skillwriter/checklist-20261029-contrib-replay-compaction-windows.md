# skill-writer checklist - meta-claude-hooks (contribution entries: variant pricing, compaction facts, Windows bash)

- [x] Change: SKILL.md, "Price the variant you are actually proposing" bullet - never derive a narrower
      variant's count by filtering another predicate's labelled firings; replay the variant's own predicate
      and diff firing sets by `id` (measured 95 vs 211). references/events.md - new subsection "What
      auto-compaction does around a hook (measured)" under Compaction: the ~33k reserve below
      `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, the same turn continuing after an auto compaction, SessionStart
      `compact` as the injection route, an `env` block reaching hook subprocesses, `rapid_refill_breaker`.
      references/authoring.md - a hook test must not launch the bash shim with a bare `bash` (WSL on a Windows
      runner); skip on Windows or resolve Git Bash's `bash.exe`.
- [x] Receipt held: `skill_receipt.py check meta-skill-writer` reported "fresh"; the editing agent loaded
      bitranox:meta-skill-writer through the Skill tool before its first edit.
- [x] RED as a text check of the pre-edit files (no subagent arm: the batch brief forbids dispatching
      subagents, so the file coverage check is the evidence): `grep -n -iE "label|another predicate" SKILL.md`
      hit only an unrelated line about a "label or an intent"; the Compaction section of events.md held only the
      PreCompact/PostCompact contract, no reserve, continuation, env or breaker fact; `grep -n -iE "wsl"
      references/authoring.md` printed nothing.
- [x] GREEN quote-back, each found with grep: SKILL.md "Never derive a narrower variant's count by filtering
      ANOTHER predicate's labelled firings"; events.md "It fires about 33k tokens BELOW
      `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, not at it." and "The same turn continues after an AUTO compaction.";
      authoring.md "A test that launches the hook through a bash shim must not name a bare `bash`."
- [x] Mechanism claims checked against their sources: the reserve, the 42k tool result and the env-block reach
      against hooks/context-watcher.py (`_HARNESS_RESERVE`, `_SAVE_MARGIN_MIN`, `_ENV_COMPACT_WINDOW` comments);
      continuation, SessionStart injection and the PreCompact/PostCompact limits against the
      hooks/compact-resume.py docstring; `rapid_refill_breaker` found as a `terminal_reason` in a recorded
      `claude -p` result and as a string in the CLI binary; the WSL failure against
      hooks/tests/test_non_ascii_introduced.py, whose shim smoke test is skipped on win32 for that reason.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only (no non-ASCII byte in the three files), `reformat_tables.py --check --strict` reports
      Unchanged for each, and the release-history finder over the diff's added lines printed nothing; version
      numbers appear only as the probed build ("CLI 2.1.310").
- [x] Not mirrored: `repo-gate.py --mirrors` lists no twin for meta-claude-hooks.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
