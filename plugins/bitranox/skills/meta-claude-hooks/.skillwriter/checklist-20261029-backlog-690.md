# skill-writer checklist - meta-claude-hooks (upstream hooks docs drift, backlog 690)

- [x] Change: references/io-contract.md - new section "Blocking when the hook fails (`onFailure`)": what counts
      as a failure, what a blocked failure does per event, the events and async hooks it does not affect, and
      the Windows-without-Git-Bash default; the Timeouts paragraph names the `onFailure` exception.
      references/configuration.md - `onFailure` rows in the command and HTTP handler field tables.
      references/events.md - `CLAUDE_CODE_DISABLE_FILE_MENTIONS=1` on the PreToolUse `@` note; the Elicitation
      decline rules (top-level `decision: "block"`, a decline from one of several hooks wins).
      references/authoring.md - Windows: running a `.ps1` with `&`, `CLAUDE_CODE_GIT_BASH_PATH`, a PowerShell
      guard needing both `onFailure` and `shell`; traps: a decision printed by a background process, the
      per-source limits on skill frontmatter hooks. SKILL.md - the Reference baseline line, rewritten by
      `hookdoc_stamp.py baseline --write`, and the I/O contract routing row now names `onFailure (block when
      a hook fails)` so a reader finds the new section from the hub (accuracy: `grep -c onFailure
      references/io-contract.md` is non-zero); references/upstream-stamp.json rewritten by `stamp --write`.
- [x] Receipt held: `skill_receipt.py check meta-skill-writer` reported "fresh"; the editing agent loaded
      bitranox:meta-skill-writer through the Skill tool before its first edit.
- [x] RED as a mechanical text check: `hookdoc_stamp.py check --force` against the live upstream pages returned
      STRUCTURAL for both sources, and `hookdoc_stamp.py stamp` (dry run) was refused with coverage
      `missing_required`: CLAUDE_CODE_DISABLE_FILE_MENTIONS, CLAUDE_CODE_GIT_BASH_PATH, check, failed,
      onFailure, ps1. `grep -n 'onFailure\|DISABLE_FILE_MENTIONS\|GIT_BASH_PATH' references/*.md` printed nothing.
      No subagent arm: the session brief forbids dispatching subagents, so the coverage gate is the evidence.
- [x] GREEN: `hookdoc_stamp.py coverage --json` reports complete true, missing_required [], missing_events [],
      phantom_events []. `stamp --write` wrote the stamp; a fresh `check --force` with an empty cache dir
      returns CURRENT for hooks-reference and hooks-guide; `baseline` exits 0 (in sync).
- [x] Quote-back of the governing text, each substring found with `grep -cF` (count 1): io-contract.md
      "`\"onFailure\": \"block\"` on a `command` or `http` hook (Claude Code 2.1.295+) turns a"; events.md "turn the insertion off with
      `CLAUDE_CODE_DISABLE_FILE_MENTIONS=1` in the shell, user or managed settings"; authoring.md "set
      `CLAUDE_CODE_GIT_BASH_PATH` to the `bash.exe` Claude Code did not find, then start a new session."
- [x] Each mechanism claim checked against the upstream hooks.md text it restates (sections "Block the action
      when a hook fails", "Failed hooks on Windows without Git Bash", "PreToolUse", "Other ways to decline an
      elicitation", "Hooks that start a background process", "Limits on skill hooks").
- [x] Upstream "removed" names `elicitation_id` and `action` are still documented upstream (Elicitation input and
      output sections); only their position in the fingerprinted examples moved, so events.md keeps them.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only (no non-ASCII byte in references/*.md or SKILL.md), tables canonical
      (`reformat_tables.py --check --strict` reports Unchanged for every file), no history phrasing in the
      added lines (the release-history finder over the diff's added lines printed nothing); version numbers
      appear only as floors ("Claude Code 2.1.295+").
- [x] Skill tests: `pytest plugins/bitranox/skills/meta-claude-hooks/tests` 99 passed.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
